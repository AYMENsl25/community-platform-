from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.clubs.membership_models import JoinRequest, Membership
from talaqi.clubs.models import Club
from talaqi.clubs.repository import ClubRepository
from talaqi.db.identifiers import generate_uuid7
from talaqi.identity.models import AuthPrincipal
from talaqi.outbox import TransactionalEventPublisher
from talaqi.platform import ApiError


def _membership(row: Mapping[str, object]) -> Membership:
    return Membership(
        id=cast(UUID, row["id"]),
        club_id=cast(UUID, row["club_id"]),
        user_id=cast(UUID, row["user_id"]),
        role=cast(str, row["role"]),  # type: ignore[arg-type]
        joined_at=cast(datetime, row["joined_at"]),
        display_name=cast(str | None, row.get("display_name")),
        email=cast(str | None, row.get("email")),
    )


def _join_request(row: Mapping[str, object]) -> JoinRequest:
    return JoinRequest(
        id=cast(UUID, row["id"]),
        club_id=cast(UUID, row["club_id"]),
        user_id=cast(UUID, row["user_id"]),
        status=cast(str, row["status"]),  # type: ignore[arg-type]
        message=cast(str | None, row["message"]),
        decided_by_user_id=cast(UUID | None, row["decided_by_user_id"]),
        decision_reason=cast(str | None, row["decision_reason"]),
        decided_at=cast(datetime | None, row["decided_at"]),
        created_at=cast(datetime, row["created_at"]),
        updated_at=cast(datetime, row["updated_at"]),
        display_name=cast(str | None, row.get("display_name")),
        email=cast(str | None, row.get("email")),
    )


class MembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._clubs = ClubRepository(session)

    async def lock_club(self, club_id: UUID) -> Club | None:
        return await self._clubs.get(club_id, for_update=True)

    async def transfer_candidate(self, user_id: UUID) -> AuthPrincipal | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT id, status::text AS status,
                               email_verified_at IS NOT NULL AS email_verified,
                               is_platform_admin
                        FROM talaqi.users
                        WHERE id = :user_id
                        FOR UPDATE
                        """
                    ),
                    {"user_id": user_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return AuthPrincipal(
            user_id=cast(UUID, row["id"]),
            session_id=generate_uuid7(),
            email_verified=cast(bool, row["email_verified"]),
            status=cast(str, row["status"]),  # type: ignore[arg-type]
            is_platform_admin=cast(bool, row["is_platform_admin"]),
        )

    async def get_membership(
        self,
        club_id: UUID,
        user_id: UUID,
        *,
        for_update: bool = False,
    ) -> Membership | None:
        suffix = " FOR UPDATE OF membership" if for_update else ""
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT membership.id, membership.club_id, membership.user_id,
                               membership.role::text AS role, membership.joined_at
                        FROM talaqi.club_memberships AS membership
                        WHERE membership.club_id = :club_id
                          AND membership.user_id = :user_id
                        """
                        + suffix
                    ),
                    {"club_id": club_id, "user_id": user_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else _membership(cast(Mapping[str, object], row))

    async def add_member(self, club_id: UUID, user_id: UUID) -> Membership:
        await self._session.execute(
            text(
                """
                INSERT INTO talaqi.club_memberships (id, club_id, user_id, role)
                VALUES (:id, :club_id, :user_id, 'member')
                ON CONFLICT (club_id, user_id) DO NOTHING
                """
            ),
            {"id": generate_uuid7(), "club_id": club_id, "user_id": user_id},
        )
        membership = await self.get_membership(club_id, user_id, for_update=True)
        if membership is None:
            raise RuntimeError("membership insertion did not persist")
        return membership

    async def create_or_get_pending_request(
        self,
        club_id: UUID,
        user_id: UUID,
        message: str | None,
    ) -> tuple[JoinRequest, bool]:
        existing = await self._session.execute(
            text(
                """
                SELECT id, club_id, user_id, status::text AS status, message,
                       decided_by_user_id, decision_reason, decided_at,
                       created_at, updated_at
                FROM talaqi.club_join_requests
                WHERE club_id = :club_id AND user_id = :user_id AND status = 'pending'
                FOR UPDATE
                """
            ),
            {"club_id": club_id, "user_id": user_id},
        )
        existing_row = existing.mappings().one_or_none()
        if existing_row is not None:
            return _join_request(cast(Mapping[str, object], existing_row)), False
        request_id = generate_uuid7()
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        INSERT INTO talaqi.club_join_requests (
                            id, club_id, user_id, status, message
                        ) VALUES (:id, :club_id, :user_id, 'pending', :message)
                        ON CONFLICT (club_id, user_id) WHERE status = 'pending'
                        DO UPDATE SET id = talaqi.club_join_requests.id
                        RETURNING id, club_id, user_id, status::text AS status, message,
                                  decided_by_user_id, decision_reason, decided_at,
                                  created_at, updated_at
                        """
                    ),
                    {
                        "id": request_id,
                        "club_id": club_id,
                        "user_id": user_id,
                        "message": message,
                    },
                )
            )
            .mappings()
            .one()
        )
        result = _join_request(cast(Mapping[str, object], row))
        organizers = (
            (
                await self._session.execute(
                    text(
                        "SELECT user_id FROM talaqi.club_memberships "
                        "WHERE club_id = :club_id AND role IN ('owner', 'admin')"
                    ),
                    {"club_id": club_id},
                )
            )
            .scalars()
            .all()
        )
        publisher = TransactionalEventPublisher(self._session)
        for organizer_id in organizers:
            await publisher.publish(
                aggregate_type="membership",
                aggregate_id=result.id,
                event_type="membership.requested",
                payload={
                    "recipient_user_id": str(organizer_id),
                    "club_id": str(club_id),
                    "membership_id": str(result.id),
                },
                deduplication_key=f"membership:{result.id}:requested:{organizer_id}",
                available_at=result.created_at,
            )
        return result, True

    async def cancel_pending_request(self, club_id: UUID, user_id: UUID) -> bool:
        cancelled = await self._session.scalar(
            text(
                """
                UPDATE talaqi.club_join_requests
                SET status = 'cancelled'
                WHERE club_id = :club_id AND user_id = :user_id AND status = 'pending'
                RETURNING id
                """
            ),
            {"club_id": club_id, "user_id": user_id},
        )
        return cancelled is not None

    async def remove_membership(self, membership_id: UUID) -> None:
        removed = (
            await self._session.execute(
                text(
                    "DELETE FROM talaqi.club_memberships WHERE id = :id RETURNING club_id, user_id"
                ),
                {"id": membership_id},
            )
        ).one_or_none()
        if removed is None:
            return
        club_id, user_id = removed
        await TransactionalEventPublisher(self._session).publish(
            aggregate_type="membership",
            aggregate_id=membership_id,
            event_type="membership.removed",
            payload={
                "recipient_user_id": str(user_id),
                "club_id": str(club_id),
                "membership_id": str(membership_id),
            },
            deduplication_key=f"membership:{membership_id}:removed",
            available_at=datetime.now().astimezone(),
        )

    async def list_members(self, club_id: UUID) -> list[Membership]:
        rows = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT membership.id, membership.club_id, membership.user_id,
                               membership.role::text AS role, membership.joined_at,
                               profile.display_name, user_account.email
                        FROM talaqi.club_memberships AS membership
                        JOIN talaqi.users AS user_account ON user_account.id = membership.user_id
                        LEFT JOIN talaqi.profiles AS profile
                          ON profile.user_id = membership.user_id
                        WHERE membership.club_id = :club_id
                        ORDER BY
                          CASE membership.role
                            WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 ELSE 2
                          END,
                          membership.joined_at,
                          membership.id
                        """
                    ),
                    {"club_id": club_id},
                )
            )
            .mappings()
            .all()
        )
        return [_membership(cast(Mapping[str, object], row)) for row in rows]

    async def list_pending_requests(self, club_id: UUID) -> list[JoinRequest]:
        rows = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT request.id, request.club_id, request.user_id,
                               request.status::text AS status, request.message,
                               request.decided_by_user_id, request.decision_reason,
                               request.decided_at, request.created_at, request.updated_at,
                               profile.display_name, user_account.email
                        FROM talaqi.club_join_requests AS request
                        JOIN talaqi.users AS user_account ON user_account.id = request.user_id
                        LEFT JOIN talaqi.profiles AS profile
                          ON profile.user_id = request.user_id
                        WHERE request.club_id = :club_id AND request.status = 'pending'
                        ORDER BY request.created_at, request.id
                        """
                    ),
                    {"club_id": club_id},
                )
            )
            .mappings()
            .all()
        )
        return [_join_request(cast(Mapping[str, object], row)) for row in rows]

    async def get_join_request(
        self,
        club_id: UUID,
        request_id: UUID,
        *,
        for_update: bool = False,
    ) -> JoinRequest | None:
        suffix = " FOR UPDATE OF request" if for_update else ""
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT request.id, request.club_id, request.user_id,
                               request.status::text AS status, request.message,
                               request.decided_by_user_id, request.decision_reason,
                               request.decided_at, request.created_at, request.updated_at
                        FROM talaqi.club_join_requests AS request
                        WHERE request.club_id = :club_id AND request.id = :request_id
                        """
                        + suffix
                    ),
                    {"club_id": club_id, "request_id": request_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else _join_request(cast(Mapping[str, object], row))

    async def decide_request(
        self,
        request_id: UUID,
        *,
        status: str,
        actor_user_id: UUID,
        reason: str,
        decided_at: datetime,
    ) -> JoinRequest:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        UPDATE talaqi.club_join_requests
                        SET status = CAST(:status AS talaqi.join_request_status),
                            decided_by_user_id = :actor_user_id,
                            decision_reason = :reason,
                            decided_at = :decided_at
                        WHERE id = :request_id AND status = 'pending'
                        RETURNING id, club_id, user_id, status::text AS status, message,
                                  decided_by_user_id, decision_reason, decided_at,
                                  created_at, updated_at
                        """
                    ),
                    {
                        "request_id": request_id,
                        "status": status,
                        "actor_user_id": actor_user_id,
                        "reason": reason,
                        "decided_at": decided_at,
                    },
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ApiError(code="conflict", message_key="errors.conflict", status_code=409)
        result = _join_request(cast(Mapping[str, object], row))
        await TransactionalEventPublisher(self._session).publish(
            aggregate_type="membership",
            aggregate_id=result.id,
            event_type=f"membership.{status}",
            payload={
                "recipient_user_id": str(result.user_id),
                "club_id": str(result.club_id),
                "membership_id": str(result.id),
            },
            deduplication_key=f"membership:{result.id}:{status}",
            available_at=decided_at,
        )
        return result

    async def set_role(self, membership_id: UUID, role: str) -> Membership:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        UPDATE talaqi.club_memberships
                        SET role = CAST(:role AS talaqi.club_role)
                        WHERE id = :membership_id AND role <> 'owner'
                        RETURNING id, club_id, user_id, role::text AS role, joined_at
                        """
                    ),
                    {"membership_id": membership_id, "role": role},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ApiError(code="conflict", message_key="errors.conflict", status_code=409)
        return _membership(cast(Mapping[str, object], row))

    async def transfer_ownership(
        self,
        club: Club,
        current_owner: Membership,
        target: Membership,
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE talaqi.club_memberships
                SET role = 'member'
                WHERE id = :current_owner_id AND role = 'owner'
                """
            ),
            {"current_owner_id": current_owner.id},
        )
        promoted = await self._session.scalar(
            text(
                """
                UPDATE talaqi.club_memberships
                SET role = 'owner'
                WHERE id = :target_id AND role <> 'owner'
                RETURNING id
                """
            ),
            {"target_id": target.id},
        )
        if promoted is None:
            raise ApiError(code="conflict", message_key="errors.conflict", status_code=409)
        await self._session.execute(
            text(
                """
                UPDATE talaqi.clubs
                SET owner_user_id = :target_user_id, revision = revision + 1
                WHERE id = :club_id AND owner_user_id = :current_owner_user_id
                """
            ),
            {
                "club_id": club.id,
                "target_user_id": target.user_id,
                "current_owner_user_id": current_owner.user_id,
            },
        )

    async def close_club(self, club_id: UUID, closed_at: datetime) -> None:
        closed = await self._session.scalar(
            text(
                """
                UPDATE talaqi.clubs
                SET status = 'closed', closed_at = :closed_at, revision = revision + 1
                WHERE id = :club_id AND status NOT IN ('closed', 'suspended')
                RETURNING id
                """
            ),
            {"club_id": club_id, "closed_at": closed_at},
        )
        if closed is None:
            raise ApiError(code="forbidden", message_key="errors.forbidden", status_code=403)
