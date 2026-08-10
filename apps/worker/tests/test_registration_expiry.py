from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.db.engine import build_session_factory
from talaqi.db.identifiers import generate_uuid7
from talaqi.registrations.expiry import CashExpiryJobRepository
from talaqi_worker.registration_expiry import CashExpiryWorker, build_cash_expiry_processor

from apps.api.tests.events.fixtures import (
    app_for,
    complete_event_body,
    create_user,
    event_settings,
)


async def _cash_event_with_waitlist(engine: AsyncEngine) -> tuple[UUID, UUID, datetime]:
    owner, first, second = await asyncio.gather(
        create_user(engine), create_user(engine), create_user(engine)
    )
    now = datetime.now(UTC).replace(microsecond=0)
    app = app_for(engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        event_response = await client.post(
            "/api/v1/events",
            json=complete_event_body(
                capacity=1,
                registration_method="cash_organizer_confirmed",
                cash_expiry_minutes=120,
            ),
            headers=owner.headers(idempotency_key=f"expiry-event-{generate_uuid7()}"),
        )
        assert event_response.status_code == 201, event_response.text
        event_id = UUID(event_response.json()["id"])
        responses: list[httpx.Response] = [
            await client.post(
                f"/api/v1/events/{event_id}/registrations",
                headers=member.headers(idempotency_key=f"expiry-register-{generate_uuid7()}"),
            )
            for member in (first, second)
        ]
        assert [response.json()["state"] for response in responses] == [
            "cash_pending",
            "waitlisted",
        ]
        registration_id = UUID(responses[0].json()["id"])

    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                UPDATE talaqi.registrations SET cash_expires_at = :now
                WHERE id = :registration_id
                """
            ),
            {"registration_id": registration_id, "now": now},
        )
        await connection.execute(
            text(
                """
                UPDATE talaqi.outbox_events SET available_at = :now
                WHERE deduplication_key = :deduplication_key
                """
            ),
            {
                "deduplication_key": f"registration.cash_expiry:{registration_id}",
                "now": now,
            },
        )
    return event_id, registration_id, now


def _worker(engine: AsyncEngine, worker_id: str) -> CashExpiryWorker:
    factory = build_session_factory(engine)
    settings = event_settings()
    return CashExpiryWorker(
        factory,
        lambda session: build_cash_expiry_processor(session, settings),
        worker_id=worker_id,
        lease_duration=timedelta(seconds=5),
        retry_base=timedelta(seconds=1),
    )


@pytest.mark.asyncio
async def test_competing_workers_expire_once_promote_fifo_and_replay_is_idle(
    worker_engine: AsyncEngine,
) -> None:
    event_id, registration_id, now = await _cash_event_with_waitlist(worker_engine)
    completed = await asyncio.gather(
        _worker(worker_engine, "expiry-a").run_once(now=now),
        _worker(worker_engine, "expiry-b").run_once(now=now),
    )
    assert sum(completed) == 1
    assert await _worker(worker_engine, "expiry-replay").run_once(now=now) == 0

    async with worker_engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT id, state::text AS state, seat_held
                        FROM talaqi.registrations WHERE event_id = :event_id
                        ORDER BY created_at, id
                        """
                    ),
                    {"event_id": event_id},
                )
            )
            .mappings()
            .all()
        )
        transition_count = await connection.scalar(
            text(
                """
                SELECT count(*) FROM talaqi.registration_transitions
                WHERE registration_id = :registration_id AND reason_code = 'cash_expired'
                """
            ),
            {"registration_id": registration_id},
        )
        job_status = await connection.scalar(
            text(
                """
                SELECT status::text FROM talaqi.outbox_events
                WHERE deduplication_key = :deduplication_key
                """
            ),
            {"deduplication_key": f"registration.cash_expiry:{registration_id}"},
        )
        promoted_expiry_jobs = await connection.scalar(
            text(
                """
                SELECT count(*) FROM talaqi.outbox_events AS job
                JOIN talaqi.registrations AS registration
                  ON registration.id = job.aggregate_id
                WHERE registration.event_id = :event_id
                  AND registration.state = 'cash_pending'
                  AND job.event_type = 'registration.cash_expiry_due'
                """
            ),
            {"event_id": event_id},
        )
    assert [(row["state"], row["seat_held"]) for row in rows] == [
        ("expired", False),
        ("cash_pending", True),
    ]
    assert transition_count == 1
    assert job_status == "delivered"
    assert promoted_expiry_jobs == 1


@pytest.mark.asyncio
async def test_crashed_claim_is_recovered_only_after_lease_boundary(
    worker_engine: AsyncEngine,
) -> None:
    _, registration_id, now = await _cash_event_with_waitlist(worker_engine)
    factory = build_session_factory(worker_engine)
    async with factory() as session, session.begin():
        claimed = await CashExpiryJobRepository(session).claim(
            worker_id="crashed-worker",
            now=now,
            lease_duration=timedelta(seconds=5),
            limit=1,
        )
    assert len(claimed) == 1

    recovery = _worker(worker_engine, "recovery-worker")
    assert await recovery.run_once(now=now + timedelta(seconds=4)) == 0
    assert await recovery.run_once(now=now + timedelta(seconds=5)) == 1

    async with worker_engine.connect() as connection:
        state = await connection.scalar(
            text("SELECT state::text FROM talaqi.registrations WHERE id = :id"),
            {"id": registration_id},
        )
        attempts = await connection.scalar(
            text(
                """
                SELECT attempt_count FROM talaqi.outbox_events
                WHERE deduplication_key = :deduplication_key
                """
            ),
            {"deduplication_key": f"registration.cash_expiry:{registration_id}"},
        )
    assert state == "expired"
    assert attempts == 2


@pytest.mark.asyncio
async def test_expiry_at_event_start_boundary_releases_seat_without_promotion(
    worker_engine: AsyncEngine,
) -> None:
    event_id, _, now = await _cash_event_with_waitlist(worker_engine)
    async with worker_engine.begin() as connection:
        await connection.execute(
            text("UPDATE talaqi.events SET start_at = :now WHERE id = :event_id"),
            {"event_id": event_id, "now": now},
        )

    assert await _worker(worker_engine, "boundary-worker").run_once(now=now) == 1
    async with worker_engine.connect() as connection:
        states = (
            (
                await connection.execute(
                    text(
                        """
                    SELECT state::text FROM talaqi.registrations
                    WHERE event_id = :event_id ORDER BY created_at, id
                    """
                    ),
                    {"event_id": event_id},
                )
            )
            .scalars()
            .all()
        )
    assert list(states) == ["expired", "waitlisted"]


class _AlwaysFails:
    async def process(self, job: object, *, now: datetime) -> bool:
        del job, now
        raise RuntimeError("poison expiry job")


@pytest.mark.asyncio
async def test_failures_back_off_then_become_visible_as_permanent(
    worker_engine: AsyncEngine,
) -> None:
    _, registration_id, now = await _cash_event_with_waitlist(worker_engine)
    worker = CashExpiryWorker(
        build_session_factory(worker_engine),
        lambda session: _AlwaysFails(),
        worker_id="failing-worker",
        max_attempts=2,
        retry_base=timedelta(seconds=1),
    )
    assert await worker.run_once(now=now) == 0
    assert await worker.run_once(now=now + timedelta(seconds=1)) == 0

    async with worker_engine.connect() as connection:
        row = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT status::text AS status, attempt_count, last_error_code,
                               locked_by, locked_until
                        FROM talaqi.outbox_events
                        WHERE deduplication_key = :deduplication_key
                        """
                    ),
                    {"deduplication_key": f"registration.cash_expiry:{registration_id}"},
                )
            )
            .mappings()
            .one()
        )
    assert row["status"] == "permanent_failed"
    assert row["attempt_count"] == 2
    assert row["last_error_code"] == "runtimeerror"
    assert row["locked_by"] is None
    assert row["locked_until"] is None
