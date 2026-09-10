from __future__ import annotations

import logging
import secrets
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from talaqi.outbox import OutboxEvent, OutboxRepository
from talaqi.telemetry import emit_metric

LOGGER = logging.getLogger("talaqi.worker.telemetry")


class OutboxHandler(Protocol):
    """At-least-once handler; delivery must be idempotent by deduplication_key."""

    async def deliver(self, event: OutboxEvent) -> None: ...


class PermanentDeliveryError(RuntimeError):
    """A delivery failure that must be sent directly to dead-letter review."""


Jitter = Callable[[float], float]
Clock = Callable[[], datetime]


def _random_jitter(ceiling: float) -> float:
    return secrets.SystemRandom().uniform(0.0, ceiling)


class TransactionalOutboxWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        handlers: Mapping[str, OutboxHandler],
        *,
        worker_id: str,
        lease_duration: timedelta = timedelta(seconds=30),
        max_attempts: int = 8,
        retry_base: timedelta = timedelta(seconds=5),
        retry_max: timedelta = timedelta(minutes=15),
        jitter: Jitter | None = None,
        clock: Clock | None = None,
    ) -> None:
        if not worker_id.strip() or len(worker_id) > 120:
            raise ValueError("worker_id must be between 1 and 120 characters")
        if not handlers:
            raise ValueError("at least one outbox handler is required")
        if lease_duration <= timedelta(0):
            raise ValueError("lease_duration must be positive")
        if not 1 <= max_attempts <= 20:
            raise ValueError("max_attempts must be between 1 and 20")
        if retry_base <= timedelta(0) or retry_max < retry_base:
            raise ValueError("retry bounds are invalid")
        self._session_factory = session_factory
        self._handlers = dict(handlers)
        self._event_types = tuple(sorted(handlers))
        self._worker_id = worker_id
        self._lease_duration = lease_duration
        self._max_attempts = max_attempts
        self._retry_base = retry_base
        self._retry_max = retry_max
        self._jitter: Jitter = jitter or _random_jitter
        self._clock: Clock = clock or (lambda: datetime.now(UTC))

    async def run_once(self, *, now: datetime | None = None, limit: int = 100) -> int:
        current = self._instant(now or datetime.now(UTC))
        if not 1 <= limit <= 1_000:
            raise ValueError("outbox claim limit must be between 1 and 1000")
        async with self._session_factory() as session, session.begin():
            events = await OutboxRepository(session).claim(
                worker_id=self._worker_id,
                event_types=self._event_types,
                now=current,
                lease_duration=self._lease_duration,
                limit=limit,
            )

        delivered = 0
        for event in events:
            try:
                claim_now = max(current, self._instant(self._clock()))
                async with self._session_factory() as session:
                    claimed = await OutboxRepository(session).get_claimed(
                        event.id, worker_id=self._worker_id, now=claim_now
                    )
                if claimed is None:
                    continue
                await self._handlers[claimed.event_type].deliver(claimed)
                finished_at = max(claim_now, self._instant(self._clock()))
                async with self._session_factory() as session, session.begin():
                    if await OutboxRepository(session).complete(
                        claimed.id,
                        worker_id=self._worker_id,
                        attempt_count=claimed.attempt_count,
                        locked_until=claimed.locked_until,
                        processed_at=finished_at,
                    ):
                        delivered += 1
            except Exception as error:
                await self._record_failure(
                    event,
                    error=error,
                    now=current,
                    failed_at=max(current, self._instant(self._clock())),
                )
        return delivered

    async def cleanup_delivered(self, *, before: datetime, limit: int = 1_000) -> int:
        cutoff = self._instant(before)
        if not 1 <= limit <= 10_000:
            raise ValueError("outbox cleanup limit must be between 1 and 10000")
        async with self._session_factory() as session, session.begin():
            return await OutboxRepository(session).cleanup_delivered(before=cutoff, limit=limit)

    async def _record_failure(
        self,
        event: OutboxEvent,
        *,
        error: Exception,
        now: datetime,
        failed_at: datetime,
    ) -> None:
        permanent = isinstance(error, PermanentDeliveryError) or (
            event.attempt_count >= self._max_attempts
        )
        exponent = min(max(event.attempt_count - 1, 0), 10)
        bounded_seconds = min(
            self._retry_base.total_seconds() * (2**exponent),
            self._retry_max.total_seconds(),
        )
        jitter_ceiling = min(
            self._retry_base.total_seconds(),
            max(self._retry_max.total_seconds() - bounded_seconds, 0.0),
        )
        jitter_seconds = min(max(self._jitter(jitter_ceiling), 0.0), jitter_ceiling)
        retry_at = now + timedelta(seconds=bounded_seconds + jitter_seconds)
        async with self._session_factory() as session, session.begin():
            recorded = await OutboxRepository(session).fail(
                event.id,
                worker_id=self._worker_id,
                attempt_count=event.attempt_count,
                locked_until=event.locked_until,
                error_code=type(error).__name__.lower(),
                retry_at=retry_at,
                failed_at=failed_at,
                permanent=permanent,
            )
        if recorded:
            emit_metric(
                LOGGER,
                "outbox_failures_total",
                1,
                {
                    "event_type": event.event_type,
                    "failure_class": "permanent" if permanent else "retryable",
                },
            )

    @staticmethod
    def _instant(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("worker clock must be timezone-aware")
        return value.astimezone(UTC)


__all__ = [
    "OutboxHandler",
    "PermanentDeliveryError",
    "TransactionalOutboxWorker",
]
