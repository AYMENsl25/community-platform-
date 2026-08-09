from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import httpx
import pytest
from events.fixtures import (
    AuthenticatedUser,
    app_for,
    complete_event_body,
    create_club,
    create_user,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.db.identifiers import generate_uuid7


async def _create_event(
    client: httpx.AsyncClient,
    owner: AuthenticatedUser,
    **changes: object,
) -> UUID:
    response = await client.post(
        "/api/v1/events",
        json=complete_event_body(**changes),
        headers=owner.headers(idempotency_key=f"registration-event-{generate_uuid7()}"),
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def _registration_headers(
    user: AuthenticatedUser,
    *,
    key: str,
    private_link: str | None = None,
) -> dict[str, str]:
    headers = user.headers(idempotency_key=key)
    if private_link is not None:
        headers["Authorization"] = f"PrivateLink {private_link}"
    return headers


async def _wait_until_blocked(engine: AsyncEngine, blocker_pid: int) -> None:
    deadline = asyncio.get_running_loop().time() + 5
    while asyncio.get_running_loop().time() < deadline:
        async with engine.connect() as connection:
            blocked = await connection.scalar(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM pg_stat_activity
                        WHERE :blocker_pid = ANY(pg_blocking_pids(pid))
                    )
                    """
                ),
                {"blocker_pid": blocker_pid},
            )
        if blocked:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("registration request did not wait on the authoritative row lock")


@pytest.mark.asyncio
async def test_fifty_clients_serialize_the_last_seat_and_allocate_fifo_waitlist(
    registration_engine: AsyncEngine,
) -> None:
    event_engine = registration_engine
    owner = await create_user(event_engine)
    members = await asyncio.gather(*(create_user(event_engine) for _ in range(50)))
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as setup_client:
        event_id = await _create_event(setup_client, owner, capacity=1)

    clients = [
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost")
        for _ in members
    ]
    try:
        responses = await asyncio.gather(
            *(
                client.post(
                    f"/api/v1/events/{event_id}/registrations",
                    headers=_registration_headers(
                        member,
                        key=f"last-seat-{generate_uuid7()}",
                    ),
                )
                for client, member in zip(clients, members, strict=True)
            )
        )
    finally:
        await asyncio.gather(*(client.aclose() for client in clients))

    assert [response.status_code for response in responses] == [201] * 50, responses[0].text
    states = [response.json()["state"] for response in responses]
    assert states.count("confirmed") == 1
    assert states.count("waitlisted") == 49
    assert sorted(
        response.json()["waitlist_sequence"]
        for response in responses
        if response.json()["state"] == "waitlisted"
    ) == list(range(1, 50))

    async with event_engine.connect() as connection:
        stored = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT count(*) FILTER (WHERE seat_held) AS seats,
                               count(*) FILTER (WHERE state = 'waitlisted') AS waiting,
                               count(DISTINCT waitlist_sequence)
                                   FILTER (WHERE state = 'waitlisted') AS sequences
                        FROM talaqi.registrations
                        WHERE event_id = :event_id
                        """
                    ),
                    {"event_id": event_id},
                )
            )
            .mappings()
            .one()
        )
        transitions = (
            await connection.execute(
                text(
                    """
                    SELECT count(*) FROM talaqi.registration_transitions AS transition
                    JOIN talaqi.registrations AS registration
                      ON registration.id = transition.registration_id
                    WHERE registration.event_id = :event_id
                      AND transition.previous_state IS NULL
                    """
                ),
                {"event_id": event_id},
            )
        ).scalar_one()
        outbox = (
            await connection.execute(
                text(
                    """
                    SELECT count(*) FROM talaqi.outbox_events
                    WHERE aggregate_type = 'registration'
                      AND payload->>'event_id' = :event_id
                    """
                ),
                {"event_id": str(event_id)},
            )
        ).scalar_one()

    assert stored == {"seats": 1, "waiting": 49, "sequences": 49}
    assert transitions == outbox == 50


@pytest.mark.asyncio
async def test_cash_registration_retries_safely_and_conflicting_key_reuse_is_rejected(
    registration_engine: AsyncEngine,
) -> None:
    event_engine = registration_engine
    owner = await create_user(event_engine)
    member = await create_user(event_engine)
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        first_event = await _create_event(
            client,
            owner,
            capacity=2,
            registration_method="cash_organizer_confirmed",
            cash_expiry_minutes=120,
        )
        second_event = await _create_event(client, owner, capacity=2)
        key = f"cash-registration-{generate_uuid7()}"
        first = await client.post(
            f"/api/v1/events/{first_event}/registrations",
            headers=_registration_headers(member, key=key),
        )
        replay = await client.post(
            f"/api/v1/events/{first_event}/registrations",
            headers=_registration_headers(member, key=key),
        )
        safe_retry_key = f"safe-retry-{generate_uuid7()}"
        fresh_key_retry = await client.post(
            f"/api/v1/events/{first_event}/registrations",
            headers=_registration_headers(member, key=safe_retry_key),
        )
        fresh_key_replay = await client.post(
            f"/api/v1/events/{first_event}/registrations",
            headers=_registration_headers(member, key=safe_retry_key),
        )
        conflict = await client.post(
            f"/api/v1/events/{second_event}/registrations",
            headers=_registration_headers(member, key=key),
        )

    assert first.status_code == replay.status_code == 201
    assert fresh_key_retry.status_code == fresh_key_replay.status_code == 200
    assert first.json() == replay.json() == fresh_key_retry.json() == fresh_key_replay.json()
    assert first.json()["state"] == "cash_pending"
    assert first.json()["seat_held"] is True
    assert first.json()["cash_expires_at"] is not None
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"

    async with event_engine.connect() as connection:
        counts = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT
                            (SELECT count(*) FROM talaqi.registrations
                             WHERE event_id = :event_id AND user_id = :user_id) AS registrations,
                            (SELECT count(*) FROM talaqi.outbox_events
                             WHERE aggregate_type = 'registration'
                               AND aggregate_id = CAST(:registration_id AS uuid)) AS outbox
                        """
                    ),
                    {
                        "event_id": first_event,
                        "user_id": member.user_id,
                        "registration_id": first.json()["id"],
                    },
                )
            )
            .mappings()
            .one()
        )
    assert counts == {"registrations": 1, "outbox": 1}


@pytest.mark.asyncio
async def test_registration_requires_current_member_and_event_eligibility(
    registration_engine: AsyncEngine,
) -> None:
    event_engine = registration_engine
    owner = await create_user(event_engine)
    eligible = await create_user(event_engine)
    unverified = await create_user(event_engine, verified=False)
    incomplete = await create_user(event_engine, profile_complete=False)
    suspended = await create_user(event_engine, status="suspended")
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        event_id = await _create_event(client, owner, capacity=5)
        denied = [
            await client.post(
                f"/api/v1/events/{event_id}/registrations",
                headers=_registration_headers(actor, key=f"ineligible-{generate_uuid7()}"),
            )
            for actor in (unverified, incomplete, suspended)
        ]
        async with event_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    UPDATE talaqi.events
                    SET status = 'suspended', suspended_at = clock_timestamp(),
                        suspension_reason = 'safety_review'
                    WHERE id = :event_id
                    """
                ),
                {"event_id": event_id},
            )
        suspended_event = await client.post(
            f"/api/v1/events/{event_id}/registrations",
            headers=_registration_headers(eligible, key=f"event-suspended-{generate_uuid7()}"),
        )

    assert [response.status_code for response in denied] == [403, 403, 401]
    assert [response.json()["error"]["code"] for response in denied] == [
        "registration_not_allowed",
        "registration_not_allowed",
        "invalid_credentials",
    ]
    assert suspended_event.status_code == 404
    assert suspended_event.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_concurrent_user_and_club_suspension_win_before_registration_commit(
    registration_engine: AsyncEngine,
) -> None:
    owner = await create_user(registration_engine)
    member = await create_user(registration_engine)
    second_member = await create_user(registration_engine)
    club_id = await create_club(registration_engine, owner)
    app = app_for(registration_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        public_event = await _create_event(client, owner, capacity=2)
        club_event = await _create_event(
            client,
            owner,
            ownership_type="club",
            club_id=str(club_id),
            capacity=2,
        )

        async with registration_engine.connect() as connection:
            transaction = await connection.begin()
            blocker_pid = await connection.scalar(text("SELECT pg_backend_pid()"))
            await connection.execute(
                text("SELECT id FROM talaqi.events WHERE id = :id FOR UPDATE"),
                {"id": public_event},
            )
            user_request = asyncio.create_task(
                client.post(
                    f"/api/v1/events/{public_event}/registrations",
                    headers=_registration_headers(
                        member, key=f"user-suspension-race-{generate_uuid7()}"
                    ),
                )
            )
            assert isinstance(blocker_pid, int)
            await _wait_until_blocked(registration_engine, blocker_pid)
            async with registration_engine.begin() as suspension_connection:
                await suspension_connection.execute(
                    text(
                        """
                        UPDATE talaqi.users
                        SET status = 'suspended', suspended_at = clock_timestamp(),
                            suspension_reason = 'safety_review'
                        WHERE id = :id
                        """
                    ),
                    {"id": member.user_id},
                )
            await transaction.commit()
            user_denied = await asyncio.wait_for(user_request, timeout=5)

        async with registration_engine.connect() as connection:
            transaction = await connection.begin()
            blocker_pid = await connection.scalar(text("SELECT pg_backend_pid()"))
            await connection.execute(
                text("SELECT id FROM talaqi.clubs WHERE id = :id FOR UPDATE"),
                {"id": club_id},
            )
            club_request = asyncio.create_task(
                client.post(
                    f"/api/v1/events/{club_event}/registrations",
                    headers=_registration_headers(
                        second_member, key=f"club-suspension-race-{generate_uuid7()}"
                    ),
                )
            )
            assert isinstance(blocker_pid, int)
            await _wait_until_blocked(registration_engine, blocker_pid)
            await connection.execute(
                text(
                    """
                    UPDATE talaqi.clubs
                    SET status = 'suspended', suspended_at = clock_timestamp(),
                        suspension_reason = 'safety_review'
                    WHERE id = :id
                    """
                ),
                {"id": club_id},
            )
            await transaction.commit()
            club_denied = await asyncio.wait_for(club_request, timeout=5)

    assert user_denied.status_code == 403
    assert user_denied.json()["error"]["code"] == "registration_not_allowed"
    assert club_denied.status_code == 404
    assert club_denied.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_registration_requires_authentication_and_matching_csrf(
    registration_engine: AsyncEngine,
) -> None:
    owner = await create_user(registration_engine)
    member = await create_user(registration_engine)
    app = app_for(registration_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        event_id = await _create_event(client, owner, capacity=2)
        unauthenticated = await client.post(
            f"/api/v1/events/{event_id}/registrations",
            headers={"Idempotency-Key": f"unauthenticated-{generate_uuid7()}"},
        )
        missing_csrf = await client.post(
            f"/api/v1/events/{event_id}/registrations",
            headers={
                "cookie": member.cookie,
                "Idempotency-Key": f"missing-csrf-{generate_uuid7()}",
            },
        )
        mismatched_headers = member.headers(idempotency_key=f"mismatched-csrf-{generate_uuid7()}")
        mismatched_headers["X-CSRF-Token"] = "not-the-session-token"
        mismatched_csrf = await client.post(
            f"/api/v1/events/{event_id}/registrations",
            headers=mismatched_headers,
        )

    assert unauthenticated.status_code == 401
    assert missing_csrf.status_code == 403
    assert mismatched_csrf.status_code == 403
    assert unauthenticated.json()["error"]["code"] == "authentication_required"
    assert missing_csrf.json()["error"]["code"] == "csrf_failed"
    assert mismatched_csrf.json()["error"]["code"] == "csrf_failed"


@pytest.mark.asyncio
async def test_outbox_failure_rolls_back_registration_history_and_idempotency(
    registration_engine: AsyncEngine,
) -> None:
    owner = await create_user(registration_engine)
    member = await create_user(registration_engine)
    app = app_for(registration_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        event_id = await _create_event(client, owner, capacity=2)
        key = f"rollback-registration-{generate_uuid7()}"
        async with registration_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    ALTER TABLE talaqi.outbox_events
                    ADD CONSTRAINT ck_test_reject_registration_outbox
                    CHECK (event_type NOT LIKE 'registration.%') NOT VALID
                    """
                )
            )
        try:
            failed = await client.post(
                f"/api/v1/events/{event_id}/registrations",
                headers=_registration_headers(member, key=key),
            )
            async with registration_engine.connect() as connection:
                counts = (
                    (
                        await connection.execute(
                            text(
                                """
                                SELECT
                                    (SELECT count(*) FROM talaqi.registrations
                                     WHERE event_id = :event_id
                                       AND user_id = :user_id) AS registrations,
                                    (SELECT count(*) FROM talaqi.registration_transitions AS t
                                     JOIN talaqi.registrations AS r ON r.id = t.registration_id
                                     WHERE r.event_id = :event_id
                                       AND r.user_id = :user_id) AS history,
                                    (SELECT count(*) FROM talaqi.idempotency_keys
                                     WHERE user_id = :user_id AND key = :key) AS idempotency
                                """
                            ),
                            {"event_id": event_id, "user_id": member.user_id, "key": key},
                        )
                    )
                    .mappings()
                    .one()
                )
        finally:
            async with registration_engine.begin() as connection:
                await connection.execute(
                    text(
                        "ALTER TABLE talaqi.outbox_events "
                        "DROP CONSTRAINT IF EXISTS ck_test_reject_registration_outbox"
                    )
                )

    assert failed.status_code == 500
    assert counts == {"registrations": 0, "history": 0, "idempotency": 0}


@pytest.mark.asyncio
async def test_private_registration_requires_live_link_and_start_time_is_hard_deadline(
    registration_engine: AsyncEngine,
) -> None:
    event_engine = registration_engine
    owner = await create_user(event_engine)
    member = await create_user(event_engine)
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        event_id = await _create_event(
            client,
            owner,
            capacity=3,
            visibility="private_link",
        )
        issued = await client.post(
            f"/api/v1/events/{event_id}/private-link",
            json={"expires_in_days": 7},
            headers=owner.headers(),
        )
        assert issued.status_code == 201
        private_link = issued.json()["copy_value"]
        missing = await client.post(
            f"/api/v1/events/{event_id}/registrations",
            headers=_registration_headers(member, key=f"missing-link-{generate_uuid7()}"),
        )
        invalid = await client.post(
            f"/api/v1/events/{event_id}/registrations",
            headers=_registration_headers(
                member,
                key=f"invalid-link-{generate_uuid7()}",
                private_link="x" * 43,
            ),
        )
        private_key = f"valid-link-{generate_uuid7()}"
        registered = await client.post(
            f"/api/v1/events/{event_id}/registrations",
            json={"private_link": private_link},
            headers=_registration_headers(member, key=private_key),
        )
        private_replay = await client.post(
            f"/api/v1/events/{event_id}/registrations",
            headers=_registration_headers(member, key=private_key, private_link=private_link),
        )
        private_conflict = await client.post(
            f"/api/v1/events/{event_id}/registrations",
            json={"private_link": "y" * 43},
            headers=_registration_headers(member, key=private_key),
        )
        async with event_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    UPDATE talaqi.events
                    SET start_at = :start_at, end_at = :end_at
                    WHERE id = :event_id
                    """
                ),
                {
                    "event_id": event_id,
                    "start_at": datetime.now(UTC) - timedelta(minutes=1),
                    "end_at": datetime.now(UTC) + timedelta(hours=1),
                },
            )
        late_member = await create_user(event_engine)
        closed = await client.post(
            f"/api/v1/events/{event_id}/registrations",
            json={"private_link": private_link},
            headers=_registration_headers(
                late_member, key=f"closed-registration-{generate_uuid7()}"
            ),
        )

    assert missing.status_code == invalid.status_code == 404
    assert missing.json()["error"]["code"] == invalid.json()["error"]["code"] == "not_found"
    assert registered.status_code == 201
    assert private_replay.status_code == 201
    assert private_replay.json() == registered.json()
    assert private_conflict.status_code == 409
    assert private_conflict.json()["error"]["code"] == "idempotency_conflict"
    assert registered.json()["state"] == "confirmed"
    assert closed.status_code == 409
    assert closed.json()["error"]["code"] == "registration_closed"


@pytest.mark.asyncio
async def test_free_cancellation_promotes_fifo_and_replays_with_history_audit_and_outbox(
    registration_engine: AsyncEngine,
) -> None:
    owner = await create_user(registration_engine)
    members = [await create_user(registration_engine) for _ in range(3)]
    app = app_for(registration_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        event_id = await _create_event(client, owner, capacity=1)
        created = [
            await client.post(
                f"/api/v1/events/{event_id}/registrations",
                headers=_registration_headers(member, key=f"free-promotion-{generate_uuid7()}"),
            )
            for member in members
        ]
        key = f"cancel-free-{generate_uuid7()}"
        cancelled = await client.delete(
            f"/api/v1/events/{event_id}/registrations/me",
            headers=_registration_headers(members[0], key=key),
        )
        replay = await client.delete(
            f"/api/v1/events/{event_id}/registrations/me",
            headers=_registration_headers(members[0], key=key),
        )

    assert [response.status_code for response in created] == [201, 201, 201]
    assert [response.json()["state"] for response in created] == [
        "confirmed",
        "waitlisted",
        "waitlisted",
    ]
    assert cancelled.status_code == replay.status_code == 200
    assert cancelled.json() == replay.json()
    assert cancelled.json()["state"] == "cancelled"

    async with registration_engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT user_id, state::text AS state, seat_held,
                               waitlist_sequence
                        FROM talaqi.registrations
                        WHERE event_id = :event_id
                        ORDER BY created_at, id
                        """
                    ),
                    {"event_id": event_id},
                )
            )
            .mappings()
            .all()
        )
        evidence = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT
                            (SELECT count(*) FROM talaqi.registration_transitions
                             WHERE registration_id IN (
                                 SELECT id FROM talaqi.registrations
                                 WHERE event_id = :event_id
                             ) AND reason_code IN ('member_cancelled', 'waitlist_promoted'))
                                AS transitions,
                            (SELECT count(*) FROM talaqi.audit_events
                             WHERE target_type = 'registration'
                               AND action IN ('registration.cancel', 'registration.promote')
                               AND target_id IN (
                                   SELECT id FROM talaqi.registrations
                                   WHERE event_id = :event_id
                               )) AS audits,
                            (SELECT count(*) FROM talaqi.outbox_events
                             WHERE aggregate_type = 'registration'
                               AND aggregate_id IN (
                                   SELECT id FROM talaqi.registrations
                                   WHERE event_id = :event_id
                               )
                               AND deduplication_key LIKE 'registration.transition:%')
                                AS outbox
                        """
                    ),
                    {"event_id": event_id},
                )
            )
            .mappings()
            .one()
        )

    assert [row["user_id"] for row in rows] == [member.user_id for member in members]
    assert [row["state"] for row in rows] == ["cancelled", "confirmed", "waitlisted"]
    assert [row["waitlist_sequence"] for row in rows] == [None, None, 2]
    assert evidence == {"transitions": 2, "audits": 2, "outbox": 2}


@pytest.mark.asyncio
async def test_promotion_skips_ineligible_fifo_member_and_promotes_next(
    registration_engine: AsyncEngine,
) -> None:
    owner = await create_user(registration_engine)
    holder = await create_user(registration_engine)
    ineligible = await create_user(registration_engine)
    eligible = await create_user(registration_engine)
    app = app_for(registration_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        event_id = await _create_event(client, owner, capacity=1)
        for member in (holder, ineligible, eligible):
            response = await client.post(
                f"/api/v1/events/{event_id}/registrations",
                headers=_registration_headers(
                    member, key=f"ineligible-promotion-{generate_uuid7()}"
                ),
            )
            assert response.status_code == 201
        async with registration_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    UPDATE talaqi.users
                    SET status = 'suspended', suspended_at = clock_timestamp(),
                        suspension_reason = 'safety_review'
                    WHERE id = :user_id
                    """
                ),
                {"user_id": ineligible.user_id},
            )
        cancelled = await client.delete(
            f"/api/v1/events/{event_id}/registrations/me",
            headers=_registration_headers(holder, key=f"skip-ineligible-{generate_uuid7()}"),
        )

    assert cancelled.status_code == 200
    async with registration_engine.connect() as connection:
        state_rows = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT user_id, state::text AS state
                        FROM talaqi.registrations
                        WHERE event_id = :event_id
                        """
                    ),
                    {"event_id": event_id},
                )
            )
            .mappings()
            .all()
        )
        states = {cast(UUID, row["user_id"]): cast(str, row["state"]) for row in state_rows}
        reasons = set(
            (
                await connection.execute(
                    text(
                        """
                        SELECT reason_code
                        FROM talaqi.registration_transitions
                        WHERE registration_id IN (
                            SELECT id FROM talaqi.registrations WHERE event_id = :event_id
                        )
                        """
                    ),
                    {"event_id": event_id},
                )
            ).scalars()
        )
    assert states[holder.user_id] == "cancelled"
    assert states[ineligible.user_id] == "cancelled"
    assert states[eligible.user_id] == "confirmed"
    assert "promotion_ineligible" in reasons
    assert "waitlist_promoted" in reasons


@pytest.mark.asyncio
async def test_simultaneous_cancellations_promote_one_each_without_overcapacity(
    registration_engine: AsyncEngine,
) -> None:
    owner = await create_user(registration_engine)
    members = [await create_user(registration_engine) for _ in range(4)]
    app = app_for(registration_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        event_id = await _create_event(client, owner, capacity=2)
        for member in members:
            response = await client.post(
                f"/api/v1/events/{event_id}/registrations",
                headers=_registration_headers(
                    member, key=f"concurrent-cancel-setup-{generate_uuid7()}"
                ),
            )
            assert response.status_code == 201
        responses = await asyncio.gather(
            *(
                client.delete(
                    f"/api/v1/events/{event_id}/registrations/me",
                    headers=_registration_headers(
                        member, key=f"concurrent-cancel-{generate_uuid7()}"
                    ),
                )
                for member in members[:2]
            )
        )

    assert [response.status_code for response in responses] == [200, 200]
    async with registration_engine.connect() as connection:
        invariant = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT count(*) FILTER (WHERE seat_held) AS held,
                               count(*) FILTER (WHERE state = 'confirmed') AS confirmed,
                               count(*) FILTER (WHERE state = 'waitlisted') AS waitlisted,
                               count(*) FILTER (WHERE state = 'cancelled') AS cancelled
                        FROM talaqi.registrations
                        WHERE event_id = :event_id
                        """
                    ),
                    {"event_id": event_id},
                )
            )
            .mappings()
            .one()
        )
    assert invariant == {"held": 2, "confirmed": 2, "waitlisted": 0, "cancelled": 2}


@pytest.mark.asyncio
async def test_cash_promotion_gets_new_bounded_expiry_and_cutoff_fails_closed(
    registration_engine: AsyncEngine,
) -> None:
    owner = await create_user(registration_engine)
    holder = await create_user(registration_engine)
    waiting = await create_user(registration_engine)
    app = app_for(registration_engine)
    start_at = datetime.now(UTC) + timedelta(hours=3)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        event_id = await _create_event(
            client,
            owner,
            capacity=1,
            registration_method="cash_organizer_confirmed",
            cash_expiry_minutes=240,
            cancellation_cutoff_minutes=0,
            start_at=start_at.isoformat(),
            end_at=(start_at + timedelta(hours=2)).isoformat(),
        )
        for member in (holder, waiting):
            response = await client.post(
                f"/api/v1/events/{event_id}/registrations",
                headers=_registration_headers(member, key=f"cash-promotion-{generate_uuid7()}"),
            )
            assert response.status_code == 201
        cancelled = await client.delete(
            f"/api/v1/events/{event_id}/registrations/me",
            headers=_registration_headers(holder, key=f"cash-cancel-{generate_uuid7()}"),
        )

        closed_start = datetime.now(UTC) + timedelta(hours=1)
        closed_event = await _create_event(
            client,
            owner,
            capacity=1,
            cancellation_cutoff_minutes=120,
            start_at=closed_start.isoformat(),
            end_at=(closed_start + timedelta(hours=2)).isoformat(),
        )
        registered = await client.post(
            f"/api/v1/events/{closed_event}/registrations",
            headers=_registration_headers(holder, key=f"closed-cancel-register-{generate_uuid7()}"),
        )
        closed = await client.delete(
            f"/api/v1/events/{closed_event}/registrations/me",
            headers=_registration_headers(holder, key=f"closed-cancel-{generate_uuid7()}"),
        )

    assert cancelled.status_code == 200
    assert registered.status_code == 201
    assert closed.status_code == 409
    assert closed.json()["error"]["code"] == "cancellation_closed"
    async with registration_engine.connect() as connection:
        promoted = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT state::text AS state, cash_expires_at
                        FROM talaqi.registrations
                        WHERE event_id = :event_id AND user_id = :user_id
                        """
                    ),
                    {"event_id": event_id, "user_id": waiting.user_id},
                )
            )
            .mappings()
            .one()
        )
    assert promoted["state"] == "cash_pending"
    assert promoted["cash_expires_at"] == start_at


@pytest.mark.asyncio
async def test_manager_confirms_cash_and_lists_privacy_safe_attendees_with_export_audit(
    registration_engine: AsyncEngine,
) -> None:
    owner = await create_user(registration_engine)
    unrelated = await create_user(registration_engine)
    members = [await create_user(registration_engine) for _ in range(2)]
    app = app_for(registration_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        event_id = await _create_event(
            client,
            owner,
            capacity=2,
            registration_method="cash_organizer_confirmed",
            cash_expiry_minutes=120,
        )
        other_event_id = await _create_event(client, unrelated, capacity=2)
        created = [
            await client.post(
                f"/api/v1/events/{event_id}/registrations",
                headers=_registration_headers(member, key=f"attendee-register-{generate_uuid7()}"),
            )
            for member in members
        ]
        registration_id = UUID(created[0].json()["id"])
        key = f"cash-confirm-{generate_uuid7()}"
        confirmed = await client.post(
            f"/api/v1/events/{event_id}/registrations/{registration_id}/confirm-cash",
            headers=owner.headers(idempotency_key=key),
        )
        replay = await client.post(
            f"/api/v1/events/{event_id}/registrations/{registration_id}/confirm-cash",
            headers=owner.headers(idempotency_key=key),
        )
        denied = await client.post(
            f"/api/v1/events/{event_id}/registrations/{registration_id}/confirm-cash",
            headers=unrelated.headers(idempotency_key=f"denied-{generate_uuid7()}"),
        )
        cross_event = await client.post(
            f"/api/v1/events/{other_event_id}/registrations/{registration_id}/confirm-cash",
            headers=unrelated.headers(idempotency_key=f"cross-{generate_uuid7()}"),
        )
        async with registration_engine.connect() as connection:
            member_username = await connection.scalar(
                text("SELECT username FROM talaqi.profiles WHERE user_id = :user_id"),
                {"user_id": members[0].user_id},
            )
        assert isinstance(member_username, str)
        first_page = await client.get(
            f"/api/v1/events/{event_id}/attendees",
            params={"limit": 1},
            headers=owner.headers(),
        )
        assert first_page.status_code == 200, first_page.text
        searched = await client.get(
            f"/api/v1/events/{event_id}/attendees",
            params={"search": member_username.upper()},
            headers=owner.headers(),
        )
        confirmed_only = await client.get(
            f"/api/v1/events/{event_id}/attendees",
            params={"state": "confirmed"},
            headers=owner.headers(),
        )
        second_page = await client.get(
            f"/api/v1/events/{event_id}/attendees",
            params={"limit": 1, "cursor": first_page.json()["next_cursor"]},
            headers=owner.headers(),
        )
        cursor_mismatch = await client.get(
            f"/api/v1/events/{event_id}/attendees",
            params={
                "limit": 1,
                "state": "confirmed",
                "cursor": first_page.json()["next_cursor"],
            },
            headers=owner.headers(),
        )
        attendee_denied = await client.get(
            f"/api/v1/events/{event_id}/attendees", headers=unrelated.headers()
        )
        export_key = f"attendee-export-{generate_uuid7()}"
        export = await client.post(
            f"/api/v1/events/{event_id}/attendees/export",
            json={"state": "confirmed"},
            headers=owner.headers(idempotency_key=export_key),
        )
        export_replay = await client.post(
            f"/api/v1/events/{event_id}/attendees/export",
            json={"state": "confirmed"},
            headers=owner.headers(idempotency_key=export_key),
        )

    assert [response.status_code for response in created] == [201, 201]
    assert confirmed.status_code == replay.status_code == 200
    assert confirmed.json() == replay.json()
    assert confirmed.json()["state"] == "confirmed"
    assert denied.status_code == 403
    assert cross_event.status_code == 404
    assert attendee_denied.status_code == 403
    assert first_page.status_code == second_page.status_code == 200
    assert [item["user_id"] for item in searched.json()["items"]] == [str(members[0].user_id)]
    assert [item["state"] for item in confirmed_only.json()["items"]] == ["confirmed"]
    assert cursor_mismatch.status_code == 400
    items = first_page.json()["items"] + second_page.json()["items"]
    assert {item["user_id"] for item in items} == {str(member.user_id) for member in members}
    assert set(items[0]) == {
        "registration_id",
        "user_id",
        "username",
        "display_name",
        "method",
        "state",
        "waitlist_sequence",
        "cash_expires_at",
        "confirmed_at",
        "created_at",
    }
    assert "email" not in first_page.text
    assert export.status_code == export_replay.status_code == 202
    assert export.json() == export_replay.json()
    async with registration_engine.connect() as connection:
        evidence = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT
                            (SELECT count(*) FROM talaqi.audit_events
                             WHERE action = 'attendees.export_request'
                               AND target_id = :event_id) AS audits,
                            (SELECT count(*) FROM talaqi.outbox_events
                             WHERE event_type = 'attendees.export_requested'
                               AND aggregate_id = :event_id) AS outbox
                        """
                    ),
                    {"event_id": event_id},
                )
            )
            .mappings()
            .one()
        )
    assert evidence == {"audits": 1, "outbox": 1}


@pytest.mark.asyncio
async def test_cash_confirmation_rejects_expired_boundary_without_transition(
    registration_engine: AsyncEngine,
) -> None:
    owner = await create_user(registration_engine)
    member = await create_user(registration_engine)
    app = app_for(registration_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        event_id = await _create_event(
            client,
            owner,
            registration_method="cash_organizer_confirmed",
            cash_expiry_minutes=120,
        )
        created = await client.post(
            f"/api/v1/events/{event_id}/registrations",
            headers=_registration_headers(member, key=f"expiry-register-{generate_uuid7()}"),
        )
        registration_id = UUID(created.json()["id"])
        async with registration_engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE talaqi.registrations SET cash_expires_at = clock_timestamp() "
                    "WHERE id = :registration_id"
                ),
                {"registration_id": registration_id},
            )
        expired = await client.post(
            f"/api/v1/events/{event_id}/registrations/{registration_id}/confirm-cash",
            headers=owner.headers(idempotency_key=f"expired-confirm-{generate_uuid7()}"),
        )

    assert expired.status_code == 409
    assert expired.json()["error"]["code"] == "cash_confirmation_expired"
