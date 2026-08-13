from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.db.engine import build_session_factory
from talaqi.db.identifiers import generate_uuid7
from talaqi_worker.notifications import build_notification_worker

from apps.api.tests.events.fixtures import (
    add_club_member,
    app_for,
    complete_event_body,
    create_club,
    create_user,
)


@pytest.mark.asyncio
async def test_announcement_and_event_update_authorization_audiences_dedupe_and_projection(
    worker_engine: AsyncEngine,
) -> None:
    owner = await create_user(worker_engine)
    member = await create_user(worker_engine)
    confirmed = await create_user(worker_engine)
    waitlisted = await create_user(worker_engine)
    outsider = await create_user(worker_engine)
    club_id = await create_club(worker_engine, owner)
    await add_club_member(worker_engine, club_id, member, role="member")
    app = app_for(worker_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        created_event = await client.post(
            "/api/v1/events",
            json=complete_event_body(),
            headers=owner.headers(idempotency_key=f"event-{generate_uuid7()}"),
        )
        assert created_event.status_code == 201, created_event.text
        event_id = UUID(created_event.json()["id"])
        event_revision = created_event.json()["revision"]
        async with worker_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    INSERT INTO talaqi.registrations (
                        id, event_id, user_id, method, state, seat_held,
                        confirmed_at, waitlist_sequence
                    ) VALUES (
                        :confirmed_id, :event_id, :confirmed_user,
                        'free', 'confirmed', true, clock_timestamp(), NULL
                    ), (
                        :waitlisted_id, :event_id, :waitlisted_user,
                        'free', 'waitlisted', false, NULL, 1
                    )
                    """
                ),
                {
                    "confirmed_id": generate_uuid7(),
                    "waitlisted_id": generate_uuid7(),
                    "event_id": event_id,
                    "confirmed_user": confirmed.user_id,
                    "waitlisted_user": waitlisted.user_id,
                },
            )

        announcement_key = f"announcement-{generate_uuid7()}"
        announcement = await client.post(
            f"/api/v1/clubs/{club_id}/announcements",
            json={"title": "Managers", "body": "Manager-only update", "audience": "admins"},
            headers=owner.headers(idempotency_key=announcement_key),
        )
        replay = await client.post(
            f"/api/v1/clubs/{club_id}/announcements",
            json={"title": "Managers", "body": "Manager-only update", "audience": "admins"},
            headers=owner.headers(idempotency_key=announcement_key),
        )
        conflict = await client.post(
            f"/api/v1/clubs/{club_id}/announcements",
            json={"title": "Changed", "body": "Different", "audience": "admins"},
            headers=owner.headers(idempotency_key=announcement_key),
        )
        denied = await client.post(
            f"/api/v1/clubs/{club_id}/announcements",
            json={"title": "No", "body": "No access", "audience": "all_members"},
            headers=outsider.headers(idempotency_key=f"denied-{generate_uuid7()}"),
        )
        missing_csrf = await client.post(
            f"/api/v1/clubs/{club_id}/announcements",
            json={"title": "No", "body": "No csrf", "audience": "all_members"},
            headers={"cookie": owner.cookie, "Idempotency-Key": f"csrf-{generate_uuid7()}"},
        )
        whitespace = await client.post(
            f"/api/v1/clubs/{club_id}/announcements",
            json={"title": "   ", "body": "message", "audience": "all_members"},
            headers=owner.headers(idempotency_key=f"blank-{generate_uuid7()}"),
        )
        owner_history = await client.get(
            f"/api/v1/clubs/{club_id}/announcements", headers=owner.headers()
        )
        member_history = await client.get(
            f"/api/v1/clubs/{club_id}/announcements", headers=member.headers()
        )

        update_key = f"event-update-{generate_uuid7()}"
        event_update = await client.post(
            f"/api/v1/events/{event_id}/updates",
            json={
                "title": "Confirmed only",
                "body": "Schedule note",
                "audience": "confirmed",
                "revision": event_revision,
            },
            headers=owner.headers(idempotency_key=update_key),
        )
        async with worker_engine.begin() as connection:
            await connection.execute(
                text("UPDATE talaqi.events SET revision = revision + 1 WHERE id = :event_id"),
                {"event_id": event_id},
            )
        replay_after_revision = await client.post(
            f"/api/v1/events/{event_id}/updates",
            json={
                "title": "Confirmed only",
                "body": "Schedule note",
                "audience": "confirmed",
                "revision": event_revision,
            },
            headers=owner.headers(idempotency_key=update_key),
        )
        stale_update = await client.post(
            f"/api/v1/events/{event_id}/updates",
            json={
                "title": "Stale",
                "body": "Old composer",
                "audience": "all_active",
                "revision": event_revision,
            },
            headers=owner.headers(idempotency_key=f"stale-{generate_uuid7()}"),
        )
        confirmed_history = await client.get(
            f"/api/v1/events/{event_id}/updates", headers=confirmed.headers()
        )
        async with worker_engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE talaqi.registrations SET state = 'confirmed', seat_held = true, "
                    "confirmed_at = clock_timestamp(), waitlist_sequence = NULL "
                    "WHERE event_id = :event_id AND user_id = :user_id"
                ),
                {"event_id": event_id, "user_id": waitlisted.user_id},
            )
        waitlisted_history = await client.get(
            f"/api/v1/events/{event_id}/updates", headers=waitlisted.headers()
        )
        outsider_history = await client.get(
            f"/api/v1/events/{event_id}/updates", headers=outsider.headers()
        )

    assert announcement.status_code == replay.status_code == 201
    assert announcement.json() == replay.json()
    assert conflict.status_code == 409
    assert denied.status_code == missing_csrf.status_code == 403
    assert whitespace.status_code == 422
    assert len(owner_history.json()["items"]) == 1
    assert member_history.json()["items"] == []
    assert event_update.status_code == 201, event_update.text
    assert replay_after_revision.status_code == 201
    assert replay_after_revision.json() == event_update.json()
    assert stale_update.status_code == 409
    assert len(confirmed_history.json()["items"]) == 1
    assert waitlisted_history.json()["items"] == []
    assert outsider_history.status_code == 404

    worker = build_notification_worker(
        build_session_factory(worker_engine), worker_id="content-notifications"
    )
    assert await worker.run_once(now=datetime.now(UTC)) == 2
    async with worker_engine.connect() as connection:
        projected = (
            (
                await connection.execute(
                    text(
                        """
                    SELECT type_key, recipient_user_id
                    FROM talaqi.notifications
                    WHERE type_key IN (
                        'club.announcement_published', 'event.update_published'
                    )
                    ORDER BY type_key, recipient_user_id
                    """
                    )
                )
            )
            .tuples()
            .all()
        )
    assert projected == [
        ("club.announcement_published", owner.user_id),
        ("event.update_published", confirmed.user_id),
    ]
