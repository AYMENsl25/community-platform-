from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from talaqi.audit import AuditService
from talaqi.clubs.membership_models import JoinRequest, JoinResult, Membership
from talaqi.clubs.membership_repository import MembershipRepository
from talaqi.clubs.models import Club
from talaqi.db.identifiers import validate_uuid7
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.profiles.schemas import Capabilities
from talaqi.security import can_manage_members


def _forbidden() -> ApiError:
    return ApiError(code="forbidden", message_key="errors.forbidden", status_code=403)


def _not_found() -> ApiError:
    return ApiError(code="not_found", message_key="errors.not_found", status_code=404)


def _conflict(code: str = "conflict") -> ApiError:
    return ApiError(code=code, message_key="errors.conflict", status_code=409)


def _reason(value: str) -> str:
    normalized = value.strip()
    if not 3 <= len(normalized) <= 500:
        raise ApiError(code="invalid_reason", message_key="errors.validation", status_code=422)
    return normalized


class TransferEligibility(Protocol):
    async def evaluate(self, principal: AuthPrincipal) -> Capabilities: ...


class MembershipService:
    def __init__(
        self,
        repository: MembershipRepository,
        audit: AuditService,
        eligibility: TransferEligibility,
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._eligibility = eligibility

    async def join(
        self,
        principal: AuthPrincipal,
        club_id: UUID,
        *,
        message: str | None,
        request_id: UUID,
    ) -> JoinResult:
        self._require_active_verified(principal)
        club = await self._club(club_id)
        if club.status != "published":
            raise _forbidden()
        existing = await self._repository.get_membership(
            club.id, principal.user_id, for_update=True
        )
        if existing is not None:
            return JoinResult(state="member", membership=existing)
        normalized_message = None
        if message is not None:
            normalized_message = message.strip() or None
        if club.membership_policy == "open":
            membership = await self._repository.add_member(club.id, principal.user_id)
            await self._audit.record(
                actor_user_id=principal.user_id,
                actor_kind="member",
                action="club.member.join",
                target_type="club",
                target_id=club.id,
                safe_after={"role": "member"},
                request_id=request_id,
            )
            return JoinResult(state="member", membership=membership)
        join_request, created = await self._repository.create_or_get_pending_request(
            club.id, principal.user_id, normalized_message
        )
        if created:
            await self._audit.record(
                actor_user_id=principal.user_id,
                actor_kind="member",
                action="club.join_request.create",
                target_type="club",
                target_id=club.id,
                safe_after={"request_id": str(join_request.id), "status": "pending"},
                request_id=request_id,
            )
        return JoinResult(state="pending", join_request=join_request)

    async def leave(
        self,
        principal: AuthPrincipal,
        club_id: UUID,
        *,
        request_id: UUID,
    ) -> None:
        self._require_active(principal)
        club = await self._club(club_id)
        if club.status in ("suspended", "closed"):
            raise _forbidden()
        membership = await self._repository.get_membership(
            club.id, principal.user_id, for_update=True
        )
        if membership is None:
            cancelled = await self._repository.cancel_pending_request(club.id, principal.user_id)
            if not cancelled:
                raise _not_found()
            action = "club.join_request.cancel"
            before = {"status": "pending"}
        else:
            if membership.role == "owner" or club.owner_user_id == principal.user_id:
                raise _conflict("sole_owner_exit")
            await self._repository.remove_membership(membership.id)
            action = "club.member.leave"
            before = {"role": membership.role}
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="member",
            action=action,
            target_type="club",
            target_id=club.id,
            safe_before=before,
            request_id=request_id,
        )

    async def list_members(self, principal: AuthPrincipal, club_id: UUID) -> list[Membership]:
        club, actor_membership = await self._managed_club(principal, club_id)
        can_manage_members(principal, club, actor_membership)
        return await self._repository.list_members(club.id)

    async def list_requests(self, principal: AuthPrincipal, club_id: UUID) -> list[JoinRequest]:
        club, actor_membership = await self._managed_club(principal, club_id)
        can_manage_members(principal, club, actor_membership)
        return await self._repository.list_pending_requests(club.id)

    async def approve(
        self,
        principal: AuthPrincipal,
        club_id: UUID,
        join_request_id: UUID,
        *,
        reason: str,
        request_id: UUID,
        now: datetime | None = None,
    ) -> None:
        normalized_reason = _reason(reason)
        club, actor_membership = await self._managed_club(principal, club_id)
        can_manage_members(principal, club, actor_membership)
        join_request = await self._request(club.id, join_request_id)
        existing = await self._repository.get_membership(
            club.id, join_request.user_id, for_update=True
        )
        if join_request.status == "approved" and existing is not None:
            return
        if join_request.status != "pending":
            raise _conflict()
        await self._repository.add_member(club.id, join_request.user_id)
        decided = await self._repository.decide_request(
            join_request.id,
            status="approved",
            actor_user_id=principal.user_id,
            reason=normalized_reason,
            decided_at=now or datetime.now(UTC),
        )
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="organizer",
            action="club.join_request.approve",
            target_type="club_join_request",
            target_id=decided.id,
            reason=normalized_reason,
            safe_before={"status": "pending"},
            safe_after={"status": "approved", "club_id": str(club.id)},
            request_id=request_id,
        )

    async def reject(
        self,
        principal: AuthPrincipal,
        club_id: UUID,
        join_request_id: UUID,
        *,
        reason: str,
        request_id: UUID,
        now: datetime | None = None,
    ) -> None:
        normalized_reason = _reason(reason)
        club, actor_membership = await self._managed_club(principal, club_id)
        can_manage_members(principal, club, actor_membership)
        join_request = await self._request(club.id, join_request_id)
        if join_request.status == "rejected":
            return
        if join_request.status != "pending":
            raise _conflict()
        decided = await self._repository.decide_request(
            join_request.id,
            status="rejected",
            actor_user_id=principal.user_id,
            reason=normalized_reason,
            decided_at=now or datetime.now(UTC),
        )
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="organizer",
            action="club.join_request.reject",
            target_type="club_join_request",
            target_id=decided.id,
            reason=normalized_reason,
            safe_before={"status": "pending"},
            safe_after={"status": "rejected", "club_id": str(club.id)},
            request_id=request_id,
        )

    async def change_role(
        self,
        principal: AuthPrincipal,
        club_id: UUID,
        target_user_id: UUID,
        *,
        role: str,
        reason: str,
        request_id: UUID,
    ) -> None:
        normalized_reason = _reason(reason)
        club = await self._club(club_id)
        self._require_owner(principal, club)
        target = await self._repository.get_membership(club.id, target_user_id, for_update=True)
        if target is None:
            raise _not_found()
        if target.role == "owner":
            raise _conflict()
        if target.role == role:
            return
        changed = await self._repository.set_role(target.id, role)
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="organizer",
            action="club.member.role_change",
            target_type="club_membership",
            target_id=changed.id,
            reason=normalized_reason,
            safe_before={"role": target.role, "club_id": str(club.id)},
            safe_after={"role": changed.role, "club_id": str(club.id)},
            request_id=request_id,
        )

    async def transfer(
        self,
        principal: AuthPrincipal,
        club_id: UUID,
        target_user_id: UUID,
        *,
        reason: str,
        request_id: UUID,
    ) -> None:
        normalized_reason = _reason(reason)
        club = await self._club(club_id)
        self._require_owner(principal, club)
        current_owner = await self._repository.get_membership(
            club.id, principal.user_id, for_update=True
        )
        target = await self._repository.get_membership(club.id, target_user_id, for_update=True)
        if current_owner is None or current_owner.role != "owner" or target is None:
            raise _not_found()
        if target.user_id == principal.user_id:
            raise _conflict()
        candidate = await self._repository.transfer_candidate(target.user_id)
        if candidate is None or not (await self._eligibility.evaluate(candidate)).create_club:
            raise ApiError(
                code="ownership_transfer_ineligible",
                message_key="errors.forbidden",
                status_code=403,
            )
        await self._repository.transfer_ownership(club, current_owner, target)
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="organizer",
            action="club.ownership.transfer",
            target_type="club",
            target_id=club.id,
            reason=normalized_reason,
            safe_before={"owner_user_id": str(principal.user_id)},
            safe_after={"owner_user_id": str(target.user_id)},
            request_id=request_id,
        )

    async def close(
        self,
        principal: AuthPrincipal,
        club_id: UUID,
        *,
        reason: str,
        request_id: UUID,
        now: datetime | None = None,
    ) -> None:
        normalized_reason = _reason(reason)
        club = await self._club(club_id)
        self._require_owner(principal, club)
        await self._repository.close_club(club.id, now or datetime.now(UTC))
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="organizer",
            action="club.close",
            target_type="club",
            target_id=club.id,
            reason=normalized_reason,
            safe_before={"status": club.status, "revision": club.revision},
            safe_after={"status": "closed", "revision": club.revision + 1},
            request_id=request_id,
        )

    async def _club(self, club_id: UUID) -> Club:
        try:
            identifier = validate_uuid7(club_id)
        except ValueError:
            raise _not_found() from None
        club = await self._repository.lock_club(identifier)
        if club is None:
            raise _not_found()
        return club

    async def _managed_club(
        self, principal: AuthPrincipal, club_id: UUID
    ) -> tuple[Club, Membership | None]:
        club = await self._club(club_id)
        membership = await self._repository.get_membership(
            club.id, principal.user_id, for_update=True
        )
        return club, membership

    async def _request(self, club_id: UUID, request_id: UUID) -> JoinRequest:
        try:
            identifier = validate_uuid7(request_id)
        except ValueError:
            raise _not_found() from None
        join_request = await self._repository.get_join_request(club_id, identifier, for_update=True)
        if join_request is None:
            raise _not_found()
        return join_request

    @staticmethod
    def _require_active(principal: AuthPrincipal) -> None:
        if principal.status != "active":
            raise _forbidden()

    @classmethod
    def _require_active_verified(cls, principal: AuthPrincipal) -> None:
        cls._require_active(principal)
        if not principal.email_verified:
            raise ApiError(
                code="email_verification_required",
                message_key="blockers.email_verification_required",
                status_code=403,
            )

    @classmethod
    def _require_owner(cls, principal: AuthPrincipal, club: Club) -> None:
        cls._require_active(principal)
        if club.status in ("suspended", "closed") or club.owner_user_id != principal.user_id:
            raise _forbidden()
