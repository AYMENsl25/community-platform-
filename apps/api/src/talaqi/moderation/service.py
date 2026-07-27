from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from talaqi.audit import AuditEvent, AuditService
from talaqi.db.identifiers import validate_uuid7
from talaqi.identity.models import AuthPrincipal
from talaqi.moderation.models import (
    ModerationAction,
    ModerationCase,
    ModerationCaseEvent,
    ModerationTarget,
    TargetType,
)
from talaqi.moderation.repository import ModerationRepositoryProtocol
from talaqi.platform import ApiError
from talaqi.security import can_access_admin, can_moderate


def _not_found() -> ApiError:
    return ApiError(code="not_found", message_key="errors.not_found", status_code=404)


def _conflict() -> ApiError:
    return ApiError(
        code="invalid_moderation_transition", message_key="errors.conflict", status_code=409
    )


def _reason(value: str) -> str:
    normalized = value.strip()
    if not 3 <= len(normalized) <= 2_000:
        raise ApiError(code="invalid_reason", message_key="errors.validation", status_code=422)
    return normalized


def emergency_notice(case: ModerationCase) -> bool:
    return case.category == "safety" or case.priority == "emergency"


def capabilities(target: ModerationTarget) -> tuple[ModerationAction, ...]:
    values: dict[tuple[TargetType, str], tuple[ModerationAction, ...]] = {
        ("user", "active"): ("suspend",),
        ("user", "suspended"): ("restore",),
        ("club", "published"): ("suspend", "unpublish"),
        ("club", "suspended"): ("restore",),
        ("club", "unpublished"): ("restore",),
        ("event", "published"): ("suspend",),
        ("event", "suspended"): ("restore",),
    }
    return values.get((target.type, target.status), ())


class ModerationService:
    def __init__(
        self,
        repository: ModerationRepositoryProtocol,
        audit: AuditService,
    ) -> None:
        self._repository = repository
        self._audit = audit

    async def list_cases(
        self,
        principal: AuthPrincipal,
        *,
        status: str | None,
        priority: str | None,
        target_type: str | None,
        limit: int,
        after_priority: str | None = None,
        after_created_at: datetime | None = None,
        after_id: UUID | None = None,
    ) -> list[tuple[ModerationCase, ModerationTarget, tuple[ModerationAction, ...]]]:
        can_access_admin(principal)
        cases = await self._repository.list_cases(
            status=status,
            priority=priority,
            target_type=target_type,
            limit=limit,
            after_priority=after_priority,
            after_created_at=after_created_at,
            after_id=after_id,
        )
        views: list[tuple[ModerationCase, ModerationTarget, tuple[ModerationAction, ...]]] = []
        for case in cases:
            target = await self._repository.get_target(case.target_type, case.target_id)
            if target is not None:
                views.append((case, target, capabilities(target)))
        return views

    async def list_audit_events(
        self,
        principal: AuthPrincipal,
        *,
        target_type: str | None,
        target_id: UUID | None,
        actor_user_id: UUID | None,
        action: str | None,
        limit: int,
        after_created_at: datetime | None = None,
        after_id: UUID | None = None,
    ) -> list[AuditEvent]:
        can_access_admin(principal)
        return await self._audit.list_events(
            target_type=target_type,
            target_id=target_id,
            actor_user_id=actor_user_id,
            action=action,
            limit=limit,
            after_created_at=after_created_at,
            after_id=after_id,
        )

    async def get_detail(
        self, principal: AuthPrincipal, case_id: UUID
    ) -> tuple[
        ModerationCase,
        ModerationTarget,
        list[ModerationCaseEvent],
        tuple[ModerationAction, ...],
    ]:
        can_access_admin(principal)
        case = await self._case(case_id)
        target = await self._repository.get_target(case.target_type, case.target_id)
        if target is None:
            raise _not_found()
        events = await self._repository.list_case_events(case.id)
        return case, target, events, capabilities(target)

    async def search_targets(
        self,
        principal: AuthPrincipal,
        target_type: TargetType,
        query: str,
        *,
        limit: int,
    ) -> list[ModerationTarget]:
        can_access_admin(principal)
        normalized = query.strip()
        if not 2 <= len(normalized) <= 120:
            raise ApiError(
                code="invalid_search",
                message_key="errors.validation",
                status_code=422,
            )
        return await self._repository.search_targets(target_type, normalized, limit=limit)

    async def act(
        self,
        principal: AuthPrincipal,
        case_id: UUID,
        action: ModerationAction,
        *,
        reason: str,
        request_id: UUID,
        now: datetime | None = None,
    ) -> tuple[ModerationCase, ModerationTarget, list[ModerationCaseEvent]]:
        can_access_admin(principal)
        has_active_mfa = await self._repository.has_active_mfa(principal.user_id)
        can_moderate(principal, has_active_mfa=has_active_mfa)
        normalized_reason = _reason(reason)
        case = await self._case(case_id, for_update=True)
        target = await self._repository.get_target(
            case.target_type, case.target_id, for_update=True
        )
        if target is None:
            raise _not_found()
        if action not in capabilities(target):
            raise _conflict()
        current = now or datetime.now(UTC)
        changed = await self._repository.apply_target_action(
            target, action, reason=normalized_reason, now=current
        )
        if changed is None:
            raise _conflict()
        updated_case = await self._repository.record_case_action(
            case,
            actor_user_id=principal.user_id,
            action=action,
            reason=normalized_reason,
            previous_target_status=target.status,
            target_status=changed.status,
            now=current,
        )
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="admin",
            action=f"moderation.target.{action}",
            target_type=target.type,
            target_id=target.id,
            reason=normalized_reason,
            safe_before={"status": target.status},
            safe_after={"status": changed.status, "case_id": str(case.id)},
            request_id=request_id,
        )
        return updated_case, changed, await self._repository.list_case_events(case.id)

    async def _case(self, case_id: UUID, *, for_update: bool = False) -> ModerationCase:
        try:
            identifier = validate_uuid7(case_id)
        except ValueError:
            raise _not_found() from None
        case = await self._repository.get_case(identifier, for_update=for_update)
        if case is None:
            raise _not_found()
        return case


__all__ = ["ModerationService", "capabilities", "emergency_notice"]
