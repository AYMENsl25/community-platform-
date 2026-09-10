from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import String

from talaqi.outbox.models import DeadLetter, OperationalOutboxEvent, OutboxEvent


class OutboxDeduplicationConflictError(RuntimeError):
    pass


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_active_mfa(self, user_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                text(
                    """SELECT EXISTS (
                        SELECT 1 FROM talaqi.user_mfa_factors
                        WHERE user_id = :user_id AND verified_at IS NOT NULL AND disabled_at IS NULL
                    )"""
                ),
                {"user_id": user_id},
            )
        )

    async def enqueue(
        self,
        *,
        aggregate_type: str,
        aggregate_id: UUID,
        event_type: str,
        payload: Mapping[str, object],
        deduplication_key: str,
        available_at: datetime,
    ) -> bool:
        statement = text(
            """
                INSERT INTO talaqi.outbox_events (
                    aggregate_type, aggregate_id, event_type, payload,
                    deduplication_key, available_at
                ) VALUES (
                    :aggregate_type, :aggregate_id, :event_type,
                    CAST(:payload AS jsonb), :deduplication_key, :available_at
                )
                ON CONFLICT (deduplication_key) DO NOTHING
                RETURNING id
                """
        ).bindparams(bindparam("payload", type_=JSONB))
        event_id = await self._session.scalar(
            statement,
            {
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "event_type": event_type,
                "payload": dict(payload),
                "deduplication_key": deduplication_key,
                "available_at": available_at,
            },
        )
        if event_id is not None:
            return True
        existing = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT aggregate_type, aggregate_id, event_type, payload, available_at
                        FROM talaqi.outbox_events
                        WHERE deduplication_key = :deduplication_key
                        """
                    ),
                    {"deduplication_key": deduplication_key},
                )
            )
            .mappings()
            .one()
        )
        intended = (aggregate_type, aggregate_id, event_type, dict(payload), available_at)
        actual = (
            existing["aggregate_type"],
            existing["aggregate_id"],
            existing["event_type"],
            existing["payload"],
            existing["available_at"],
        )
        if actual != intended:
            raise OutboxDeduplicationConflictError("outbox_deduplication_conflict")
        return False

    async def claim(
        self,
        *,
        worker_id: str,
        event_types: Sequence[str],
        now: datetime,
        lease_duration: timedelta,
        limit: int,
    ) -> tuple[OutboxEvent, ...]:
        if not event_types:
            return ()
        statement = text(
            """
            WITH due AS (
                SELECT event.id
                FROM talaqi.outbox_events AS event
                WHERE event.event_type = ANY(:event_types)
                  AND event.available_at <= :now
                  AND event.status IN ('pending', 'retryable_failed', 'processing')
                  AND (event.locked_until IS NULL OR event.locked_until <= :now)
                  AND NOT EXISTS (
                      SELECT 1
                      FROM talaqi.outbox_events AS earlier
                      WHERE earlier.aggregate_type = event.aggregate_type
                        AND earlier.aggregate_id = event.aggregate_id
                        AND earlier.available_at <= :now
                        AND earlier.status <> 'delivered'
                        AND (earlier.created_at, earlier.id)
                            < (event.created_at, event.id)
                  )
                ORDER BY event.available_at, event.created_at, event.id
                FOR UPDATE SKIP LOCKED
                LIMIT :limit
            )
            UPDATE talaqi.outbox_events AS event
            SET status = 'processing',
                attempt_count = event.attempt_count + 1,
                locked_by = :worker_id,
                locked_until = :locked_until
            FROM due
            WHERE event.id = due.id
            RETURNING event.id, event.aggregate_type, event.aggregate_id,
                      event.event_type, event.payload, event.deduplication_key,
                      event.attempt_count, event.created_at, event.locked_until
            """
        ).bindparams(bindparam("event_types", type_=ARRAY(String())))
        rows = (
            (
                await self._session.execute(
                    statement,
                    {
                        "event_types": list(event_types),
                        "now": now,
                        "worker_id": worker_id,
                        "locked_until": now + lease_duration,
                        "limit": limit,
                    },
                )
            )
            .mappings()
            .all()
        )
        return tuple(self._event(cast(Mapping[str, object], row)) for row in rows)

    async def get_claimed(
        self, event_id: UUID, *, worker_id: str, now: datetime
    ) -> OutboxEvent | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT id, aggregate_type, aggregate_id, event_type, payload,
                               deduplication_key, attempt_count, created_at, locked_until
                        FROM talaqi.outbox_events
                        WHERE id = :event_id AND status = 'processing'
                          AND locked_by = :worker_id AND locked_until > :now
                        """
                    ),
                    {"event_id": event_id, "worker_id": worker_id, "now": now},
                )
            )
            .mappings()
            .one_or_none()
        )
        return self._event(cast(Mapping[str, object], row)) if row is not None else None

    async def complete(
        self,
        event_id: UUID,
        *,
        worker_id: str,
        attempt_count: int,
        locked_until: datetime,
        processed_at: datetime,
    ) -> bool:
        completed_id = await self._session.scalar(
            text(
                """
                UPDATE talaqi.outbox_events
                SET status = 'delivered', processed_at = :processed_at,
                    locked_by = NULL, locked_until = NULL, last_error_code = NULL
                WHERE id = :event_id AND status = 'processing' AND locked_by = :worker_id
                  AND attempt_count = :attempt_count
                  AND locked_until = :locked_until
                  AND locked_until > :processed_at
                RETURNING id
                """
            ),
            {
                "event_id": event_id,
                "worker_id": worker_id,
                "attempt_count": attempt_count,
                "locked_until": locked_until,
                "processed_at": processed_at,
            },
        )
        return completed_id is not None

    async def fail(
        self,
        event_id: UUID,
        *,
        worker_id: str,
        attempt_count: int,
        locked_until: datetime,
        error_code: str,
        retry_at: datetime,
        failed_at: datetime,
        permanent: bool,
    ) -> bool:
        failed_id = await self._session.scalar(
            text(
                """
                UPDATE talaqi.outbox_events
                SET status = CAST(:status AS talaqi.delivery_status),
                    available_at = :retry_at, locked_by = NULL, locked_until = NULL,
                    last_error_code = :error_code
                WHERE id = :event_id AND status = 'processing' AND locked_by = :worker_id
                  AND attempt_count = :attempt_count
                  AND locked_until = :locked_until
                  AND locked_until > :failed_at
                RETURNING id
                """
            ),
            {
                "event_id": event_id,
                "worker_id": worker_id,
                "attempt_count": attempt_count,
                "locked_until": locked_until,
                "status": "permanent_failed" if permanent else "retryable_failed",
                "retry_at": retry_at,
                "failed_at": failed_at,
                "error_code": error_code[:120],
            },
        )
        return failed_id is not None

    async def list_dead_letters(self, *, limit: int = 100) -> tuple[DeadLetter, ...]:
        rows = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT id, aggregate_type, aggregate_id, event_type,
                               deduplication_key, attempt_count, last_error_code, created_at
                        FROM talaqi.outbox_events
                        WHERE status = 'permanent_failed'
                        ORDER BY created_at, id
                        LIMIT :limit
                        """
                    ),
                    {"limit": limit},
                )
            )
            .mappings()
            .all()
        )
        return tuple(
            DeadLetter(
                id=cast(UUID, row["id"]),
                aggregate_type=cast(str, row["aggregate_type"]),
                aggregate_id=cast(UUID, row["aggregate_id"]),
                event_type=cast(str, row["event_type"]),
                deduplication_key=cast(str, row["deduplication_key"]),
                attempt_count=cast(int, row["attempt_count"]),
                last_error_code=cast(str | None, row["last_error_code"]),
                created_at=cast(datetime, row["created_at"]),
            )
            for row in rows
        )

    async def list_operational(
        self, *, status: str | None = None, event_type: str | None = None, limit: int = 50
    ) -> tuple[OperationalOutboxEvent, ...]:
        rows = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT id, aggregate_type, event_type, status::text AS status,
                               attempt_count, last_error_code, available_at, created_at,
                               processed_at, locked_until
                        FROM talaqi.outbox_events
                        WHERE (CAST(:status AS text) IS NULL OR status::text = :status)
                          AND (CAST(:event_type AS text) IS NULL OR event_type = :event_type)
                        ORDER BY created_at DESC, id DESC
                        LIMIT :limit
                        """
                    ),
                    {"status": status, "event_type": event_type, "limit": limit},
                )
            )
            .mappings()
            .all()
        )
        return tuple(self._operational(cast(Mapping[str, object], row)) for row in rows)

    async def get_operational(self, event_id: UUID) -> OperationalOutboxEvent | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT id, aggregate_type, event_type, status::text AS status,
                               attempt_count, last_error_code, available_at, created_at,
                               processed_at, locked_until
                        FROM talaqi.outbox_events WHERE id = :event_id
                        """
                    ),
                    {"event_id": event_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        return self._operational(cast(Mapping[str, object], row)) if row is not None else None

    async def retry_permanent_failure(
        self, event_id: UUID, *, now: datetime
    ) -> OperationalOutboxEvent | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        UPDATE talaqi.outbox_events
                        SET status = 'pending', available_at = :now, processed_at = NULL,
                            locked_by = NULL, locked_until = NULL, last_error_code = NULL
                        WHERE id = :event_id AND status = 'permanent_failed'
                          AND (locked_until IS NULL OR locked_until <= :now)
                        RETURNING id, aggregate_type, event_type, status::text AS status,
                                  attempt_count, last_error_code, available_at, created_at,
                                  processed_at, locked_until
                        """
                    ),
                    {"event_id": event_id, "now": now},
                )
            )
            .mappings()
            .one_or_none()
        )
        return self._operational(cast(Mapping[str, object], row)) if row is not None else None

    async def cleanup_delivered(self, *, before: datetime, limit: int = 1_000) -> int:
        deleted = (
            (
                await self._session.execute(
                    text(
                        """
                    DELETE FROM talaqi.outbox_events
                    WHERE id IN (
                        SELECT id FROM talaqi.outbox_events
                        WHERE status = 'delivered' AND processed_at < :before
                        ORDER BY processed_at, id
                        LIMIT :limit
                        FOR UPDATE SKIP LOCKED
                    )
                    RETURNING id
                    """
                    ),
                    {"before": before, "limit": limit},
                )
            )
            .scalars()
            .all()
        )
        return len(deleted)

    @staticmethod
    def _event(row: Mapping[str, object]) -> OutboxEvent:
        return OutboxEvent(
            id=cast(UUID, row["id"]),
            aggregate_type=cast(str, row["aggregate_type"]),
            aggregate_id=cast(UUID, row["aggregate_id"]),
            event_type=cast(str, row["event_type"]),
            payload=cast(dict[str, object], row["payload"]),
            deduplication_key=cast(str, row["deduplication_key"]),
            attempt_count=cast(int, row["attempt_count"]),
            created_at=cast(datetime, row["created_at"]),
            locked_until=cast(datetime, row["locked_until"]),
        )

    @staticmethod
    def _operational(row: Mapping[str, object]) -> OperationalOutboxEvent:
        return OperationalOutboxEvent(
            id=cast(UUID, row["id"]),
            aggregate_type=cast(str, row["aggregate_type"]),
            event_type=cast(str, row["event_type"]),
            status=cast(str, row["status"]),
            attempt_count=cast(int, row["attempt_count"]),
            last_error_code=cast(str | None, row["last_error_code"]),
            available_at=cast(datetime, row["available_at"]),
            created_at=cast(datetime, row["created_at"]),
            processed_at=cast(datetime | None, row["processed_at"]),
            locked_until=cast(datetime | None, row["locked_until"]),
        )


__all__ = ["OutboxDeduplicationConflictError", "OutboxRepository"]
