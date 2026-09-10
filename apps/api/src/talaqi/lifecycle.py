from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.platform import ApiError

DELETION_RECOVERY_WINDOW = timedelta(days=30)
REVOKED_SESSION_RETENTION = timedelta(days=90)


@dataclass(frozen=True, slots=True)
class DeletionState:
    requested_at: datetime
    anonymize_after: datetime


class DataLifecycleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def request_deletion(self, user_id: UUID, *, now: datetime) -> datetime | None:
        requested = (
            await self._session.execute(
                text(
                    """
                    UPDATE talaqi.users
                    SET deletion_requested_at = coalesce(deletion_requested_at, :now)
                    WHERE id = :user_id AND status = 'active' AND anonymized_at IS NULL
                    RETURNING deletion_requested_at
                    """
                ),
                {"user_id": user_id, "now": now},
            )
        ).scalar_one_or_none()
        if requested is None:
            return None
        await self._session.execute(
            text(
                """
                UPDATE talaqi.sessions
                SET revoked_at = coalesce(revoked_at, :now),
                    revoke_reason = coalesce(revoke_reason, 'account_deletion_requested')
                WHERE user_id = :user_id AND revoked_at IS NULL
                """
            ),
            {"user_id": user_id, "now": now},
        )
        return cast(datetime, requested)

    async def cancel_deletion(self, user_id: UUID, *, now: datetime) -> bool:
        result = await self._session.execute(
            text(
                """
                UPDATE talaqi.users
                SET deletion_requested_at = NULL
                WHERE id = :user_id AND status = 'active' AND anonymized_at IS NULL
                  AND deletion_requested_at IS NOT NULL
                  AND deletion_requested_at > CAST(:now AS timestamptz) - interval '30 days'
                RETURNING id
                """
            ),
            {"user_id": user_id, "now": now},
        )
        return result.scalar_one_or_none() is not None

    async def anonymize_due(self, *, now: datetime, limit: int) -> tuple[UUID, ...]:
        rows = (
            (
                await self._session.execute(
                    text(
                        """
                        WITH due AS (
                            SELECT id FROM talaqi.users
                            WHERE status = 'active' AND anonymized_at IS NULL
                              AND deletion_requested_at <=
                                  CAST(:now AS timestamptz) - interval '30 days'
                            ORDER BY deletion_requested_at, id
                            FOR UPDATE SKIP LOCKED LIMIT :limit
                        ), anonymized AS (
                            UPDATE talaqi.users AS account
                            SET email = 'deleted+' || replace(account.id::text, '-', '')
                                || '@invalid.talaqi',
                                password_hash = '$argon2id$deleted', status = 'deleted',
                                email_verified_at = NULL, failed_login_count = 0,
                                locked_until = NULL, suspended_at = NULL, suspension_reason = NULL,
                                anonymized_at = :now
                            FROM due WHERE account.id = due.id RETURNING account.id
                        )
                        SELECT id FROM anonymized ORDER BY id
                        """
                    ),
                    {"now": now, "limit": limit},
                )
            )
            .scalars()
            .all()
        )
        user_ids = tuple(cast(UUID, value) for value in rows)
        if not user_ids:
            return ()
        await self._session.execute(
            text(
                """
                UPDATE talaqi.profiles
                SET username = 'deleted_' || left(replace(user_id::text, '-', ''), 22),
                    display_name = 'Deleted member', avatar_media_id = NULL,
                    notify_event_email = false, notify_community_email = false,
                    profile_completed_at = NULL
                WHERE user_id = ANY(:user_ids)
                """
            ),
            {"user_ids": list(user_ids)},
        )
        await self._session.execute(
            text("DELETE FROM talaqi.auth_tokens WHERE user_id = ANY(:user_ids)"),
            {"user_ids": list(user_ids)},
        )
        await self._session.execute(
            text("DELETE FROM talaqi.user_mfa_factors WHERE user_id = ANY(:user_ids)"),
            {"user_ids": list(user_ids)},
        )
        return user_ids

    async def cleanup_expired_credentials(self, *, now: datetime) -> None:
        await self._session.execute(
            text("DELETE FROM talaqi.auth_tokens WHERE expires_at < :now"), {"now": now}
        )
        await self._session.execute(
            text(
                """
                DELETE FROM talaqi.sessions
                WHERE revoked_at < :before AND expires_at < :now
                """
            ),
            {"before": now - REVOKED_SESSION_RETENTION, "now": now},
        )


class DataLifecycleService:
    def __init__(self, repository: DataLifecycleRepository) -> None:
        self._repository = repository

    async def request_deletion(
        self, user_id: UUID, *, now: datetime | None = None
    ) -> DeletionState:
        current = _utc(now or datetime.now(UTC))
        requested = await self._repository.request_deletion(user_id, now=current)
        if requested is None:
            raise ApiError(
                code="account_deletion_unavailable",
                message_key="errors.conflict",
                status_code=409,
            )
        requested = _utc(requested)
        return DeletionState(requested, requested + DELETION_RECOVERY_WINDOW)

    async def cancel_deletion(self, user_id: UUID, *, now: datetime | None = None) -> None:
        if not await self._repository.cancel_deletion(user_id, now=_utc(now or datetime.now(UTC))):
            raise ApiError(
                code="account_deletion_recovery_expired",
                message_key="errors.conflict",
                status_code=409,
            )

    async def run_cleanup(
        self, *, now: datetime | None = None, limit: int = 100
    ) -> tuple[UUID, ...]:
        if not 1 <= limit <= 1_000:
            raise ValueError("lifecycle cleanup limit must be between 1 and 1000")
        current = _utc(now or datetime.now(UTC))
        anonymized = await self._repository.anonymize_due(now=current, limit=limit)
        await self._repository.cleanup_expired_credentials(now=current)
        return anonymized


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("lifecycle time must be timezone-aware")
    return value.astimezone(UTC)


__all__ = [
    "DELETION_RECOVERY_WINDOW",
    "DataLifecycleRepository",
    "DataLifecycleService",
    "DeletionState",
]
