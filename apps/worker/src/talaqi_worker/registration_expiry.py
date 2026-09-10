from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from talaqi.audit import AuditRepository, AuditService
from talaqi.clubs.event_access import ClubEventAccessService
from talaqi.clubs.repository import ClubRepository
from talaqi.config import Settings
from talaqi.events.access_repository import EventAccessRepository
from talaqi.events.access_service import EventAccessService
from talaqi.events.access_tokens import PrivateLinkTokenCodec
from talaqi.events.repository import EventRepository
from talaqi.profiles.runtime import build_registration_eligibility_service
from talaqi.registrations.expiry import (
    CashExpiryJob,
    CashExpiryJobRepository,
    CashExpiryProcessor,
)
from talaqi.registrations.repository import RegistrationRepository
from talaqi.registrations.service import PromotionService, RegistrationTransitionService
from talaqi.telemetry import emit_metric

LOGGER = logging.getLogger("talaqi.worker.telemetry")


class ExpiryProcessorProtocol(Protocol):
    async def process(self, job: CashExpiryJob, *, now: datetime) -> bool: ...


ProcessorFactory = Callable[[AsyncSession], ExpiryProcessorProtocol | CashExpiryProcessor]


def build_cash_expiry_processor(session: AsyncSession, settings: Settings) -> CashExpiryProcessor:
    registrations = RegistrationRepository(session)
    audit = AuditService(AuditRepository(session))
    events = EventAccessService(
        EventAccessRepository(session),
        EventRepository(session),
        ClubEventAccessService(ClubRepository(session)),
        audit,
        PrivateLinkTokenCodec(settings.session_secret.get_secret_value().encode("utf-8")),
    )
    transitions = RegistrationTransitionService(registrations)
    promotion = PromotionService(
        registrations,
        events,
        build_registration_eligibility_service(session, settings),
        transitions,
        audit,
    )
    return CashExpiryProcessor(registrations, transitions, promotion, audit)


class CashExpiryWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        processor_factory: ProcessorFactory,
        *,
        worker_id: str,
        lease_duration: timedelta = timedelta(seconds=30),
        max_attempts: int = 5,
        retry_base: timedelta = timedelta(seconds=5),
    ) -> None:
        if not worker_id.strip() or len(worker_id) > 120:
            raise ValueError("worker_id must be between 1 and 120 characters")
        if lease_duration <= timedelta(0):
            raise ValueError("lease_duration must be positive")
        if not 1 <= max_attempts <= 20:
            raise ValueError("max_attempts must be between 1 and 20")
        if retry_base <= timedelta(0):
            raise ValueError("retry_base must be positive")
        self._session_factory = session_factory
        self._processor_factory = processor_factory
        self._worker_id = worker_id
        self._lease_duration = lease_duration
        self._max_attempts = max_attempts
        self._retry_base = retry_base

    async def run_once(self, *, now: datetime | None = None, limit: int = 100) -> int:
        current = self._instant(now or datetime.now(UTC))
        if not 1 <= limit <= 1_000:
            raise ValueError("expiry claim limit must be between 1 and 1000")
        async with self._session_factory() as session, session.begin():
            jobs = await CashExpiryJobRepository(session).claim(
                worker_id=self._worker_id,
                now=current,
                lease_duration=self._lease_duration,
                limit=limit,
            )

        completed = 0
        for job in jobs:
            try:
                async with self._session_factory() as session, session.begin():
                    repository = CashExpiryJobRepository(session)
                    claimed = await repository.lock_claimed(
                        job.id, worker_id=self._worker_id, now=current
                    )
                    if claimed is None:
                        continue
                    await self._processor_factory(session).process(claimed, now=current)
                    await repository.complete(claimed.id, processed_at=current)
                    completed += 1
                    emit_metric(
                        LOGGER,
                        "registration_expiry_total",
                        1,
                        {"result": "completed"},
                    )
            except Exception as error:
                await self._record_failure(job, error=error, now=current)
        return completed

    async def _record_failure(self, job: CashExpiryJob, *, error: Exception, now: datetime) -> None:
        permanent = job.attempt_count >= self._max_attempts
        exponent = min(max(job.attempt_count - 1, 0), 10)
        retry_at = now + self._retry_base * (2**exponent)
        async with self._session_factory() as session, session.begin():
            await CashExpiryJobRepository(session).fail(
                job.id,
                worker_id=self._worker_id,
                error_code=type(error).__name__.lower(),
                retry_at=retry_at,
                permanent=permanent,
            )
        emit_metric(
            LOGGER,
            "registration_expiry_total",
            1,
            {"result": "permanent_failed" if permanent else "retryable_failed"},
        )

    @staticmethod
    def _instant(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("worker clock must be timezone-aware")
        return value.astimezone(UTC)


__all__ = [
    "CashExpiryWorker",
    "ExpiryProcessorProtocol",
    "ProcessorFactory",
    "build_cash_expiry_processor",
]
