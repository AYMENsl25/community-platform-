from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.db.identifiers import generate_uuid7
from talaqi.moderation.models import (
    ModerationAction,
    ModerationCase,
    ModerationCaseEvent,
    ModerationTarget,
    TargetType,
)
from talaqi.outbox import TransactionalEventPublisher

_PRIORITY_RANK_SQL = "CASE priority WHEN 'emergency' THEN 3 WHEN 'high' THEN 2 ELSE 1 END"


def _case(row: Mapping[str, object]) -> ModerationCase:
    target_type = cast(TargetType, row["target_type"])
    target_column = {
        "user": "target_user_id",
        "club": "target_club_id",
        "event": "target_event_id",
    }[target_type]
    return ModerationCase(
        id=cast(UUID, row["id"]),
        reporter_user_id=cast(UUID | None, row["reporter_user_id"]),
        target_type=target_type,
        target_id=cast(UUID, row[target_column]),
        category=cast(str, row["category"]),
        description=cast(str, row["description"]),
        status=cast(str, row["status"]),  # type: ignore[arg-type]
        priority=cast(str, row["priority"]),  # type: ignore[arg-type]
        assigned_admin_user_id=cast(UUID | None, row["assigned_admin_user_id"]),
        resolution_reason=cast(str | None, row["resolution_reason"]),
        acknowledged_at=cast(datetime | None, row["acknowledged_at"]),
        resolved_at=cast(datetime | None, row["resolved_at"]),
        created_at=cast(datetime, row["created_at"]),
        updated_at=cast(datetime, row["updated_at"]),
    )


def _target(row: Mapping[str, object], target_type: TargetType) -> ModerationTarget:
    return ModerationTarget(
        type=target_type,
        id=cast(UUID, row["id"]),
        label=cast(str, row["label"]),
        secondary_label=cast(str | None, row["secondary_label"]),
        status=cast(str, row["status"]),
    )


class ModerationRepositoryProtocol(Protocol):
    async def has_active_mfa(self, user_id: UUID) -> bool: ...

    async def list_cases(
        self,
        *,
        status: str | None,
        priority: str | None,
        target_type: str | None,
        limit: int,
        after_priority: str | None = None,
        after_created_at: datetime | None = None,
        after_id: UUID | None = None,
    ) -> list[ModerationCase]: ...

    async def get_case(
        self, case_id: UUID, *, for_update: bool = False
    ) -> ModerationCase | None: ...

    async def list_case_events(self, case_id: UUID) -> list[ModerationCaseEvent]: ...

    async def get_target(
        self, target_type: TargetType, target_id: UUID, *, for_update: bool = False
    ) -> ModerationTarget | None: ...

    async def search_targets(
        self, target_type: TargetType, query: str, *, limit: int
    ) -> list[ModerationTarget]: ...

    async def apply_target_action(
        self,
        target: ModerationTarget,
        action: ModerationAction,
        *,
        reason: str,
        now: datetime,
    ) -> ModerationTarget | None: ...

    async def record_case_action(
        self,
        case: ModerationCase,
        *,
        actor_user_id: UUID,
        action: ModerationAction,
        reason: str,
        previous_target_status: str,
        target_status: str,
        now: datetime,
    ) -> ModerationCase: ...


class ModerationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_active_mfa(self, user_id: UUID) -> bool:
        return bool(
            (
                await self._session.execute(
                    text(
                        """
                        SELECT EXISTS (
                            SELECT 1 FROM talaqi.user_mfa_factors
                            WHERE user_id = :user_id
                              AND verified_at IS NOT NULL
                              AND disabled_at IS NULL
                        )
                        """
                    ),
                    {"user_id": user_id},
                )
            ).scalar_one()
        )

    async def list_cases(
        self,
        *,
        status: str | None,
        priority: str | None,
        target_type: str | None,
        limit: int,
        after_priority: str | None = None,
        after_created_at: datetime | None = None,
        after_id: UUID | None = None,
    ) -> list[ModerationCase]:
        conditions: list[str] = []
        params: dict[str, object] = {"limit": limit}
        if status is not None:
            conditions.append("status = CAST(:status AS talaqi.moderation_case_status)")
            params["status"] = status
        if priority is not None:
            conditions.append("priority = CAST(:priority AS talaqi.moderation_priority)")
            params["priority"] = priority
        if target_type is not None:
            conditions.append("target_type = CAST(:target_type AS talaqi.moderation_target_type)")
            params["target_type"] = target_type
        if after_priority is not None and after_created_at is not None and after_id is not None:
            priority_rank = {"standard": 1, "high": 2, "emergency": 3}[after_priority]
            conditions.append(
                f"({_PRIORITY_RANK_SQL} < :after_priority_rank OR "
                f"({_PRIORITY_RANK_SQL} = :after_priority_rank AND "
                "(created_at < :after_created_at OR "
                "(created_at = :after_created_at AND id < :after_id))))"
            )
            params.update(
                after_priority_rank=priority_rank,
                after_created_at=after_created_at,
                after_id=after_id,
            )
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = (
            (
                await self._session.execute(
                    text(
                        f"""
                        SELECT * FROM talaqi.moderation_cases
                        {where}
                        ORDER BY {_PRIORITY_RANK_SQL} DESC, created_at DESC, id DESC
                        LIMIT :limit
                        """  # noqa: S608 -- fixed clauses; values are bound
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )
        return [_case(cast(Mapping[str, object], row)) for row in rows]

    async def get_case(self, case_id: UUID, *, for_update: bool = False) -> ModerationCase | None:
        locking = " FOR UPDATE" if for_update else ""
        row = (
            (
                await self._session.execute(
                    text(f"SELECT * FROM talaqi.moderation_cases WHERE id = :id{locking}"),  # noqa: S608 -- fixed lock suffix
                    {"id": case_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        return _case(cast(Mapping[str, object], row)) if row is not None else None

    async def list_case_events(self, case_id: UUID) -> list[ModerationCaseEvent]:
        rows = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT id, moderation_case_id, actor_user_id, action::text AS action,
                               from_status::text AS from_status, to_status::text AS to_status,
                               reason, created_at
                        FROM talaqi.moderation_case_events
                        WHERE moderation_case_id = :case_id
                        ORDER BY created_at ASC, id ASC
                        """
                    ),
                    {"case_id": case_id},
                )
            )
            .mappings()
            .all()
        )
        return [
            ModerationCaseEvent(
                id=cast(UUID, row["id"]),
                moderation_case_id=cast(UUID, row["moderation_case_id"]),
                actor_user_id=cast(UUID | None, row["actor_user_id"]),
                action=cast(str | None, row["action"]),
                from_status=cast(str | None, row["from_status"]),
                to_status=cast(str, row["to_status"]),
                reason=cast(str, row["reason"]),
                created_at=cast(datetime, row["created_at"]),
            )
            for row in rows
        ]

    async def get_target(
        self, target_type: TargetType, target_id: UUID, *, for_update: bool = False
    ) -> ModerationTarget | None:
        locking = (
            {
                "user": " FOR UPDATE OF users",
                "club": " FOR UPDATE OF club",
                "event": " FOR UPDATE OF event",
            }[target_type]
            if for_update
            else ""
        )
        queries = {
            "user": """
                SELECT users.id,
                       coalesce(profile.display_name, profile.username, 'Member') AS label,
                       profile.username AS secondary_label, users.status::text AS status
                FROM talaqi.users AS users
                LEFT JOIN talaqi.profiles AS profile ON profile.user_id = users.id
                WHERE users.id = :id
            """,
            "club": """
                SELECT club.id, club.name AS label, club.slug AS secondary_label,
                       club.status::text AS status
                FROM talaqi.clubs AS club WHERE club.id = :id
            """,
            "event": """
                SELECT event.id, event.title AS label, NULL::text AS secondary_label,
                       event.status::text AS status
                FROM talaqi.events AS event WHERE event.id = :id
            """,
        }
        row = (
            (await self._session.execute(text(queries[target_type] + locking), {"id": target_id}))
            .mappings()
            .one_or_none()
        )
        return _target(cast(Mapping[str, object], row), target_type) if row is not None else None

    async def search_targets(
        self, target_type: TargetType, query: str, *, limit: int
    ) -> list[ModerationTarget]:
        queries = {
            "user": """
                SELECT users.id,
                       coalesce(profile.display_name, profile.username, 'Member') AS label,
                       profile.username AS secondary_label, users.status::text AS status
                FROM talaqi.users AS users
                LEFT JOIN talaqi.profiles AS profile ON profile.user_id = users.id
                WHERE lower(users.email) LIKE :query
                   OR lower(coalesce(profile.username, '')) LIKE :query
                   OR lower(coalesce(profile.display_name, '')) LIKE :query
                ORDER BY lower(coalesce(profile.display_name, profile.username, users.email)),
                         users.id
                LIMIT :limit
            """,
            "club": """
                SELECT id, name AS label, slug AS secondary_label, status::text AS status
                FROM talaqi.clubs
                WHERE lower(name) LIKE :query OR lower(slug) LIKE :query
                ORDER BY lower(name), id LIMIT :limit
            """,
            "event": """
                SELECT id, title AS label, NULL::text AS secondary_label, status::text AS status
                FROM talaqi.events
                WHERE lower(title) LIKE :query
                ORDER BY lower(title), id LIMIT :limit
            """,
        }
        rows = (
            (
                await self._session.execute(
                    text(queries[target_type]),
                    {"query": f"%{query.lower()}%", "limit": limit},
                )
            )
            .mappings()
            .all()
        )
        return [_target(cast(Mapping[str, object], row), target_type) for row in rows]

    async def apply_target_action(
        self,
        target: ModerationTarget,
        action: ModerationAction,
        *,
        reason: str,
        now: datetime,
    ) -> ModerationTarget | None:
        statements: dict[tuple[TargetType, ModerationAction], str] = {
            ("user", "suspend"): """
                UPDATE talaqi.users SET status = 'suspended', suspended_at = :now,
                    suspension_reason = :reason
                WHERE id = :id AND status = 'active'
                RETURNING status::text
            """,
            ("user", "restore"): """
                UPDATE talaqi.users SET status = 'active', suspended_at = NULL,
                    suspension_reason = NULL
                WHERE id = :id AND status = 'suspended'
                RETURNING status::text
            """,
            ("club", "suspend"): """
                WITH changed AS (
                    UPDATE talaqi.clubs
                    SET status = 'suspended', suspended_at = :now,
                        suspension_reason = :reason
                    WHERE id = :id AND status = 'published'
                    RETURNING id, status::text
                ), revoked AS (
                    UPDATE talaqi.event_invite_tokens AS invite
                    SET revoked_at = :now
                    FROM talaqi.events AS event, changed
                    WHERE event.club_id = changed.id
                      AND invite.event_id = event.id
                      AND invite.revoked_at IS NULL
                    RETURNING invite.id
                )
                SELECT status FROM changed
            """,
            ("club", "unpublish"): """
                WITH changed AS (
                    UPDATE talaqi.clubs SET status = 'unpublished'
                    WHERE id = :id AND status = 'published'
                    RETURNING id, status::text
                ), revoked AS (
                    UPDATE talaqi.event_invite_tokens AS invite
                    SET revoked_at = :now
                    FROM talaqi.events AS event, changed
                    WHERE event.club_id = changed.id
                      AND invite.event_id = event.id
                      AND invite.revoked_at IS NULL
                    RETURNING invite.id
                )
                SELECT status FROM changed
            """,
            ("club", "restore"): """
                UPDATE talaqi.clubs SET status = 'published', suspended_at = NULL,
                    suspension_reason = NULL, published_at = coalesce(published_at, :now)
                WHERE id = :id AND status IN ('suspended', 'unpublished')
                RETURNING status::text
            """,
            ("event", "suspend"): """
                WITH changed AS (
                    UPDATE talaqi.events
                    SET status = 'suspended', suspended_at = :now,
                        suspension_reason = :reason
                    WHERE id = :id AND status = 'published'
                    RETURNING id, status::text
                ), revoked AS (
                    UPDATE talaqi.event_invite_tokens AS invite
                    SET revoked_at = :now
                    FROM changed
                    WHERE invite.event_id = changed.id
                      AND invite.revoked_at IS NULL
                    RETURNING invite.id
                )
                SELECT status FROM changed
            """,
            ("event", "restore"): """
                UPDATE talaqi.events SET status = 'published', suspended_at = NULL,
                    suspension_reason = NULL, published_at = coalesce(published_at, :now)
                WHERE id = :id AND status = 'suspended'
                RETURNING status::text
            """,
        }
        statement = statements.get((target.type, action))
        if statement is None:
            return None
        status = (
            await self._session.execute(
                text(statement), {"id": target.id, "reason": reason, "now": now}
            )
        ).scalar_one_or_none()
        if status is None:
            return None
        return ModerationTarget(
            type=target.type,
            id=target.id,
            label=target.label,
            secondary_label=target.secondary_label,
            status=cast(str, status),
        )

    async def record_case_action(
        self,
        case: ModerationCase,
        *,
        actor_user_id: UUID,
        action: ModerationAction,
        reason: str,
        previous_target_status: str,
        target_status: str,
        now: datetime,
    ) -> ModerationCase:
        await self._session.execute(
            text(
                """
                INSERT INTO talaqi.moderation_case_events (
                    id, moderation_case_id, actor_user_id, action,
                    from_status, to_status, reason, safe_metadata
                ) VALUES (
                    :id, :case_id, :actor_user_id,
                    CAST(:action AS talaqi.moderation_action),
                    CAST(:from_status AS talaqi.moderation_case_status),
                    'actioned', :reason, CAST(:safe_metadata AS jsonb)
                )
                """
            ),
            {
                "id": generate_uuid7(),
                "case_id": case.id,
                "actor_user_id": actor_user_id,
                "action": action,
                "from_status": case.status,
                "reason": reason,
                "safe_metadata": json.dumps(
                    {
                        "previous_target_status": previous_target_status,
                        "target_status": target_status,
                    }
                ),
            },
        )
        await self._session.execute(
            text(
                """
                UPDATE talaqi.moderation_cases
                SET status = 'actioned', assigned_admin_user_id = :actor_user_id,
                    resolution_reason = :reason,
                    acknowledged_at = coalesce(acknowledged_at, :now),
                    resolved_at = :now
                WHERE id = :case_id
                """
            ),
            {
                "case_id": case.id,
                "actor_user_id": actor_user_id,
                "reason": reason,
                "now": now,
            },
        )
        updated = await self.get_case(case.id)
        if updated is None:
            raise RuntimeError("moderation case disappeared during action")
        if case.target_type == "user":
            await TransactionalEventPublisher(self._session).publish(
                aggregate_type="moderation_case",
                aggregate_id=case.id,
                event_type="moderation.action_taken",
                payload={
                    "recipient_user_id": str(case.target_id),
                    "case_id": str(case.id),
                },
                deduplication_key=f"moderation:{case.id}:action:{action}",
                available_at=now,
            )
        return updated


__all__ = ["ModerationRepository", "ModerationRepositoryProtocol"]
