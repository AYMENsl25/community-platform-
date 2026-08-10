from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.audit import AuditService
from talaqi.registrations.models import RegistrationState, TransitionCommand
from talaqi.registrations.repository import RegistrationRepository
from talaqi.registrations.service import PromotionService, RegistrationTransitionService


@dataclass(frozen=True, slots=True)
class CashExpiryJob:
    id: UUID
    registration_id: UUID
    event_id: UUID
    attempt_count: int
    locked_until: datetime


class ExpiryPromotionProtocol(Protocol):
    async def promote_next(
        self, event_id: UUID, *, now: datetime, request_id: UUID | None
    ) -> object | None: ...


class CashExpiryJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_duration: timedelta,
        limit: int,
    ) -> tuple[CashExpiryJob, ...]:
        rows = (
            (
                await self._session.execute(
                    text(
                        """
                        WITH due AS (
                            SELECT id
                            FROM talaqi.outbox_events
                            WHERE event_type = 'registration.cash_expiry_due'
                              AND available_at <= :now
                              AND status IN ('pending', 'retryable_failed', 'processing')
                              AND (locked_until IS NULL OR locked_until <= :now)
                            ORDER BY available_at, id
                            FOR UPDATE SKIP LOCKED
                            LIMIT :limit
                        )
                        UPDATE talaqi.outbox_events AS job
                        SET status = 'processing',
                            attempt_count = job.attempt_count + 1,
                            locked_by = :worker_id,
                            locked_until = :locked_until
                        FROM due
                        WHERE job.id = due.id
                        RETURNING job.id,
                                  CAST(job.payload ->> 'registration_id' AS uuid)
                                      AS registration_id,
                                  CAST(job.payload ->> 'event_id' AS uuid) AS event_id,
                                  job.attempt_count, job.locked_until
                        """
                    ),
                    {
                        "worker_id": worker_id,
                        "now": now,
                        "locked_until": now + lease_duration,
                        "limit": limit,
                    },
                )
            )
            .mappings()
            .all()
        )
        return tuple(self._job(cast(Mapping[str, object], row)) for row in rows)

    async def lock_claimed(
        self, job_id: UUID, *, worker_id: str, now: datetime
    ) -> CashExpiryJob | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT id,
                               CAST(payload ->> 'registration_id' AS uuid) AS registration_id,
                               CAST(payload ->> 'event_id' AS uuid) AS event_id,
                               attempt_count, locked_until
                        FROM talaqi.outbox_events
                        WHERE id = :job_id AND status = 'processing'
                          AND locked_by = :worker_id AND locked_until > :now
                        FOR UPDATE
                        """
                    ),
                    {"job_id": job_id, "worker_id": worker_id, "now": now},
                )
            )
            .mappings()
            .one_or_none()
        )
        return self._job(cast(Mapping[str, object], row)) if row is not None else None

    async def complete(self, job_id: UUID, *, processed_at: datetime) -> None:
        await self._session.execute(
            text(
                """
                UPDATE talaqi.outbox_events
                SET status = 'delivered', processed_at = :processed_at,
                    locked_by = NULL, locked_until = NULL, last_error_code = NULL
                WHERE id = :job_id AND status = 'processing'
                """
            ),
            {"job_id": job_id, "processed_at": processed_at},
        )

    async def fail(
        self,
        job_id: UUID,
        *,
        worker_id: str,
        error_code: str,
        retry_at: datetime,
        permanent: bool,
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE talaqi.outbox_events
                SET status = CAST(:status AS talaqi.delivery_status),
                    available_at = :retry_at, locked_by = NULL, locked_until = NULL,
                    last_error_code = :error_code
                WHERE id = :job_id AND status = 'processing' AND locked_by = :worker_id
                """
            ),
            {
                "job_id": job_id,
                "worker_id": worker_id,
                "status": "permanent_failed" if permanent else "retryable_failed",
                "retry_at": retry_at,
                "error_code": error_code[:120],
            },
        )

    @staticmethod
    def _job(row: Mapping[str, object]) -> CashExpiryJob:
        return CashExpiryJob(
            id=cast(UUID, row["id"]),
            registration_id=cast(UUID, row["registration_id"]),
            event_id=cast(UUID, row["event_id"]),
            attempt_count=cast(int, row["attempt_count"]),
            locked_until=cast(datetime, row["locked_until"]),
        )


class CashExpiryProcessor:
    def __init__(
        self,
        registrations: RegistrationRepository,
        transitions: RegistrationTransitionService,
        promotion: ExpiryPromotionProtocol | PromotionService,
        audit: AuditService,
    ) -> None:
        self._registrations = registrations
        self._transitions = transitions
        self._promotion = promotion
        self._audit = audit

    async def process(self, job: CashExpiryJob, *, now: datetime) -> bool:
        context = await self._registrations.get_context(job.registration_id, for_update=True)
        if context is None or context.registration.event_id != job.event_id:
            return False
        registration = context.registration
        if registration.state != "cash_pending":
            return False
        if registration.cash_expires_at is None or registration.cash_expires_at > now:
            raise RuntimeError("cash_expiry_job_not_due")

        result = await self._transitions.transition(
            TransitionCommand(
                command_id=job.id,
                registration_id=registration.id,
                target_state=cast(RegistrationState, "expired"),
                actor_user_id=None,
                actor_kind="system",
                reason_code="cash_expired",
                occurred_at=now,
            )
        )
        await self._audit.record(
            actor_user_id=None,
            actor_kind="system",
            action="registration.expire",
            target_type="registration",
            target_id=registration.id,
            reason="cash_expired",
            safe_before={"state": registration.state},
            safe_after={"state": result.registration.state},
            request_id=None,
        )
        await self._promotion.promote_next(job.event_id, now=now, request_id=None)
        return True


__all__ = ["CashExpiryJob", "CashExpiryJobRepository", "CashExpiryProcessor"]
