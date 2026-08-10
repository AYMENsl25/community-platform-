from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.db.engine import build_session_factory
from talaqi.db.identifiers import generate_uuid7
from talaqi.outbox import OutboxDeduplicationConflictError, OutboxEvent, OutboxRepository
from talaqi_worker.outbox import PermanentDeliveryError, TransactionalOutboxWorker

EVENT_TYPE = "test.message_requested"


class RecordingHandler:
    def __init__(self) -> None:
        self.events: list[OutboxEvent] = []

    async def deliver(self, event: OutboxEvent) -> None:
        self.events.append(event)


class PoisonHandler:
    def __init__(self, *, permanent: bool = False) -> None:
        self.permanent = permanent

    async def deliver(self, event: OutboxEvent) -> None:
        del event
        if self.permanent:
            raise PermanentDeliveryError("invalid destination")
        raise RuntimeError("provider unavailable")


class LeaseExpiryAfterDeliveryHandler:
    def __init__(self, engine: AsyncEngine, *, expired_at: datetime) -> None:
        self.engine = engine
        self.expired_at = expired_at
        self.calls = 0
        self.side_effect_keys: set[str] = set()

    async def deliver(self, event: OutboxEvent) -> None:
        self.calls += 1
        self.side_effect_keys.add(event.deduplication_key)
        if self.calls == 1:
            async with self.engine.begin() as connection:
                await connection.execute(
                    text(
                        "UPDATE talaqi.outbox_events SET locked_until = :expired_at "
                        "WHERE id = :event_id"
                    ),
                    {"expired_at": self.expired_at, "event_id": event.id},
                )


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


class AdvanceClockHandler:
    def __init__(self, clock: MutableClock) -> None:
        self.clock = clock
        self.calls = 0
        self.side_effect_keys: set[str] = set()

    async def deliver(self, event: OutboxEvent) -> None:
        self.calls += 1
        self.side_effect_keys.add(event.deduplication_key)
        if self.calls == 1:
            self.clock.value += timedelta(seconds=6)


async def enqueue(
    engine: AsyncEngine,
    *,
    aggregate_id: UUID,
    key: str,
    now: datetime,
    payload: dict[str, object] | None = None,
    event_type: str = EVENT_TYPE,
) -> bool:
    factory = build_session_factory(engine)
    async with factory() as session, session.begin():
        return await OutboxRepository(session).enqueue(
            aggregate_type="test_aggregate",
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload or {"safe_id": str(aggregate_id)},
            deduplication_key=key,
            available_at=now,
        )


async def enqueue_then_rollback(engine: AsyncEngine, *, aggregate_id: UUID, now: datetime) -> None:
    factory = build_session_factory(engine)
    async with factory() as session, session.begin():
        await OutboxRepository(session).enqueue(
            aggregate_type="test_aggregate",
            aggregate_id=aggregate_id,
            event_type=EVENT_TYPE,
            payload={"safe_id": str(aggregate_id)},
            deduplication_key="atomic:rolled-back",
            available_at=now,
        )
        raise RuntimeError("rollback")


def worker(
    engine: AsyncEngine,
    handler: RecordingHandler | PoisonHandler,
    worker_id: str,
    **kwargs: object,
) -> TransactionalOutboxWorker:
    return TransactionalOutboxWorker(
        build_session_factory(engine),
        {EVENT_TYPE: handler},
        worker_id=worker_id,
        lease_duration=timedelta(seconds=5),
        retry_base=timedelta(seconds=2),
        retry_max=timedelta(seconds=30),
        jitter=lambda ceiling: ceiling,
        **kwargs,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_atomic_enqueue_deduplicates_and_rolls_back_with_business_write(
    worker_engine: AsyncEngine,
) -> None:
    aggregate_id = generate_uuid7()
    now = datetime.now(UTC)
    assert await enqueue(worker_engine, aggregate_id=aggregate_id, key="atomic:one", now=now)
    assert not await enqueue(worker_engine, aggregate_id=aggregate_id, key="atomic:one", now=now)
    with pytest.raises(OutboxDeduplicationConflictError, match="outbox_deduplication_conflict"):
        await enqueue(
            worker_engine,
            aggregate_id=aggregate_id,
            key="atomic:one",
            now=now,
            payload={"different": True},
        )

    with pytest.raises(RuntimeError, match="rollback"):
        await enqueue_then_rollback(worker_engine, aggregate_id=aggregate_id, now=now)

    async with worker_engine.connect() as connection:
        count = await connection.scalar(
            text(
                "SELECT count(*) FROM talaqi.outbox_events WHERE deduplication_key LIKE 'atomic:%'"
            )
        )
    assert count == 1


@pytest.mark.asyncio
async def test_competing_workers_and_aggregate_ordering_deliver_once_in_order(
    worker_engine: AsyncEngine,
) -> None:
    aggregate_id = generate_uuid7()
    now = datetime.now(UTC)
    await enqueue(worker_engine, aggregate_id=aggregate_id, key="ordered:1", now=now)
    await enqueue(worker_engine, aggregate_id=aggregate_id, key="ordered:2", now=now)
    handler = RecordingHandler()

    first = await asyncio.gather(
        worker(worker_engine, handler, "outbox-a").run_once(now=now),
        worker(worker_engine, handler, "outbox-b").run_once(now=now),
    )
    assert sum(first) == 2
    assert await worker(worker_engine, handler, "outbox-c").run_once(now=now) == 0
    assert [event.deduplication_key for event in handler.events] == ["ordered:1", "ordered:2"]


@pytest.mark.asyncio
async def test_crashed_claim_is_recovered_at_lease_boundary(
    worker_engine: AsyncEngine,
) -> None:
    aggregate_id = generate_uuid7()
    now = datetime.now(UTC)
    await enqueue(worker_engine, aggregate_id=aggregate_id, key="lease:one", now=now)
    factory = build_session_factory(worker_engine)
    async with factory() as session, session.begin():
        claimed = await OutboxRepository(session).claim(
            worker_id="crashed",
            event_types=[EVENT_TYPE],
            now=now,
            lease_duration=timedelta(seconds=5),
            limit=1,
        )
    assert len(claimed) == 1

    handler = RecordingHandler()
    recovery = worker(worker_engine, handler, "recovery")
    assert await recovery.run_once(now=now + timedelta(seconds=4)) == 0
    assert await recovery.run_once(now=now + timedelta(seconds=5)) == 1
    assert handler.events[0].attempt_count == 2


@pytest.mark.asyncio
async def test_global_due_ordering_across_worker_handler_sets_and_future_jobs(
    worker_engine: AsyncEngine,
) -> None:
    aggregate_id = generate_uuid7()
    now = datetime.now(UTC)
    future_type = "test.future_job"
    second_type = "test.second_message"
    await enqueue(
        worker_engine,
        aggregate_id=aggregate_id,
        key="future:first",
        now=now + timedelta(hours=1),
        event_type=future_type,
    )
    await enqueue(
        worker_engine,
        aggregate_id=aggregate_id,
        key="due:second",
        now=now,
        event_type=second_type,
    )
    due_handler = RecordingHandler()
    due_worker = TransactionalOutboxWorker(
        build_session_factory(worker_engine),
        {second_type: due_handler},
        worker_id="due-worker",
    )
    assert await due_worker.run_once(now=now) == 1
    assert [event.deduplication_key for event in due_handler.events] == ["due:second"]

    first_type = "test.first_message"
    ordered_id = generate_uuid7()
    await enqueue(
        worker_engine,
        aggregate_id=ordered_id,
        key="cross:first",
        now=now,
        event_type=first_type,
    )
    await enqueue(
        worker_engine,
        aggregate_id=ordered_id,
        key="cross:second",
        now=now,
        event_type=second_type,
    )
    second_handler = RecordingHandler()
    second_worker = TransactionalOutboxWorker(
        build_session_factory(worker_engine),
        {second_type: second_handler},
        worker_id="second-worker",
    )
    assert await second_worker.run_once(now=now) == 0


@pytest.mark.asyncio
async def test_expired_lease_fences_completion_and_idempotent_replay(
    worker_engine: AsyncEngine,
) -> None:
    aggregate_id = generate_uuid7()
    now = datetime.now(UTC)
    await enqueue(worker_engine, aggregate_id=aggregate_id, key="fenced:one", now=now)
    handler = LeaseExpiryAfterDeliveryHandler(worker_engine, expired_at=now)
    first = TransactionalOutboxWorker(
        build_session_factory(worker_engine),
        {EVENT_TYPE: handler},
        worker_id="lease-expiry",
        lease_duration=timedelta(seconds=5),
    )
    assert await first.run_once(now=now) == 0

    replay = TransactionalOutboxWorker(
        build_session_factory(worker_engine),
        {EVENT_TYPE: handler},
        worker_id="lease-replay",
        lease_duration=timedelta(seconds=5),
    )
    assert await replay.run_once(now=now) == 1
    assert handler.calls == 2
    assert handler.side_effect_keys == {"fenced:one"}


@pytest.mark.asyncio
async def test_same_worker_reclaim_cannot_be_completed_by_stale_claim(
    worker_engine: AsyncEngine,
) -> None:
    now = datetime.now(UTC)
    await enqueue(
        worker_engine,
        aggregate_id=generate_uuid7(),
        key="aba:one",
        now=now,
    )
    factory = build_session_factory(worker_engine)
    async with factory() as session, session.begin():
        first = (
            await OutboxRepository(session).claim(
                worker_id="stable-worker",
                event_types=[EVENT_TYPE],
                now=now,
                lease_duration=timedelta(seconds=5),
                limit=1,
            )
        )[0]
    async with factory() as session, session.begin():
        second = (
            await OutboxRepository(session).claim(
                worker_id="stable-worker",
                event_types=[EVENT_TYPE],
                now=now + timedelta(seconds=5),
                lease_duration=timedelta(seconds=5),
                limit=1,
            )
        )[0]
    async with factory() as session, session.begin():
        assert not await OutboxRepository(session).complete(
            first.id,
            worker_id="stable-worker",
            attempt_count=first.attempt_count,
            locked_until=first.locked_until,
            processed_at=now + timedelta(seconds=6),
        )
        assert await OutboxRepository(session).complete(
            second.id,
            worker_id="stable-worker",
            attempt_count=second.attempt_count,
            locked_until=second.locked_until,
            processed_at=now + timedelta(seconds=6),
        )


@pytest.mark.asyncio
async def test_fresh_clock_skips_later_batch_items_after_lease_expiry(
    worker_engine: AsyncEngine,
) -> None:
    now = datetime.now(UTC)
    await enqueue(worker_engine, aggregate_id=generate_uuid7(), key="batch:one", now=now)
    await enqueue(worker_engine, aggregate_id=generate_uuid7(), key="batch:two", now=now)
    clock = MutableClock(now)
    handler = AdvanceClockHandler(clock)
    first = TransactionalOutboxWorker(
        build_session_factory(worker_engine),
        {EVENT_TYPE: handler},
        worker_id="batch-worker",
        lease_duration=timedelta(seconds=5),
        clock=clock,
    )
    assert await first.run_once(now=now) == 0
    assert handler.calls == 1

    recovery = TransactionalOutboxWorker(
        build_session_factory(worker_engine),
        {EVENT_TYPE: handler},
        worker_id="batch-recovery",
        lease_duration=timedelta(seconds=5),
        clock=clock,
    )
    assert await recovery.run_once(now=clock.value) == 2
    assert handler.calls == 3
    assert handler.side_effect_keys == {"batch:one", "batch:two"}


@pytest.mark.asyncio
async def test_poison_event_retries_with_bounded_jitter_then_enters_dead_letter_review(
    worker_engine: AsyncEngine,
) -> None:
    aggregate_id = generate_uuid7()
    now = datetime.now(UTC)
    await enqueue(worker_engine, aggregate_id=aggregate_id, key="poison:retry", now=now)
    failing = worker(worker_engine, PoisonHandler(), "poison", max_attempts=2)

    assert await failing.run_once(now=now) == 0
    async with worker_engine.connect() as connection:
        retry_at = await connection.scalar(
            text(
                "SELECT available_at FROM talaqi.outbox_events "
                "WHERE deduplication_key = 'poison:retry'"
            )
        )
    assert retry_at == now + timedelta(seconds=4)
    assert await failing.run_once(now=retry_at) == 0

    factory = build_session_factory(worker_engine)
    async with factory() as session:
        dead_letters = await OutboxRepository(session).list_dead_letters()
    assert len(dead_letters) == 1
    assert dead_letters[0].deduplication_key == "poison:retry"
    assert dead_letters[0].last_error_code == "runtimeerror"

    await enqueue(worker_engine, aggregate_id=generate_uuid7(), key="poison:permanent", now=now)
    permanent = worker(worker_engine, PoisonHandler(permanent=True), "permanent")
    assert await permanent.run_once(now=now) == 0
    async with factory() as session:
        letters = await OutboxRepository(session).list_dead_letters()
    assert {letter.deduplication_key for letter in letters} == {
        "poison:retry",
        "poison:permanent",
    }


@pytest.mark.asyncio
async def test_retention_cleanup_removes_only_old_delivered_events(
    worker_engine: AsyncEngine,
) -> None:
    now = datetime.now(UTC)
    old_id, fresh_id = generate_uuid7(), generate_uuid7()
    await enqueue(worker_engine, aggregate_id=old_id, key="cleanup:old", now=now)
    await enqueue(worker_engine, aggregate_id=fresh_id, key="cleanup:fresh", now=now)
    handler = RecordingHandler()
    delivery = worker(worker_engine, handler, "cleanup")
    assert await delivery.run_once(now=now) == 2

    async with worker_engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE talaqi.outbox_events SET processed_at = :old "
                "WHERE deduplication_key = 'cleanup:old'"
            ),
            {"old": now - timedelta(days=31)},
        )
    assert await delivery.cleanup_delivered(before=now - timedelta(days=30)) == 1
    async with worker_engine.connect() as connection:
        keys = (
            (
                await connection.execute(
                    text(
                        "SELECT deduplication_key FROM talaqi.outbox_events "
                        "WHERE deduplication_key LIKE 'cleanup:%'"
                    )
                )
            )
            .scalars()
            .all()
        )
    assert list(keys) == ["cleanup:fresh"]
