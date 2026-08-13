from __future__ import annotations

from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.db.identifiers import generate_uuid7

from apps.api.tests.events.fixtures import (
    add_club_member,
    app_for,
    complete_event_body,
    create_club,
    create_user,
)


@pytest.mark.asyncio
async def test_member_and_organizer_dashboards_are_permission_scoped(
    worker_engine: AsyncEngine,
) -> None:
    owner = await create_user(worker_engine)
    member = await create_user(worker_engine, profile_complete=False)
    outsider = await create_user(worker_engine)
    club_id = await create_club(worker_engine, owner)
    await add_club_member(worker_engine, club_id, member, role="member")
    app = app_for(worker_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        created = await client.post(
            "/api/v1/events",
            json=complete_event_body(),
            headers=owner.headers(idempotency_key=f"dashboard-{generate_uuid7()}"),
        )
        assert created.status_code == 201, created.text
        event_id = UUID(created.json()["id"])
        private_created = await client.post(
            "/api/v1/events",
            json=complete_event_body(title="Private saved event", visibility="private_link"),
            headers=owner.headers(idempotency_key=f"private-{generate_uuid7()}"),
        )
        assert private_created.status_code == 201, private_created.text
        private_event_id = UUID(private_created.json()["id"])
        async with worker_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    INSERT INTO talaqi.registrations (
                        event_id, user_id, method, state, seat_held, confirmed_at
                    ) VALUES (
                        :event_id, :member_id, 'free', 'confirmed', true, clock_timestamp()
                    )
                    """
                ),
                {
                    "event_id": event_id,
                    "member_id": member.user_id,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO talaqi.saved_events (event_id, user_id) "
                    "VALUES (:event_id, :member_id)"
                ),
                {"event_id": event_id, "member_id": member.user_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO talaqi.saved_events (event_id, user_id) "
                    "VALUES (:event_id, :member_id)"
                ),
                {"event_id": private_event_id, "member_id": member.user_id},
            )
            await connection.execute(
                text(
                    """INSERT INTO talaqi.notifications (
                           recipient_user_id, type_key, title_key, body_key, action_path
                       ) VALUES (
                           :member_id, 'event.updated', 'notifications.event.title',
                           'notifications.event.updated.body', :action_path
                       )"""
                ),
                {
                    "member_id": member.user_id,
                    "action_path": f"/events/{event_id}",
                },
            )
        member_response = await client.get("/api/v1/me/dashboard", headers=member.headers())
        outsider_response = await client.get("/api/v1/me/dashboard", headers=outsider.headers())
        organizer_response = await client.get(
            "/api/v1/organizer/dashboard", headers=owner.headers()
        )
        denied_organizer = await client.get(
            "/api/v1/organizer/dashboard", headers=outsider.headers()
        )
        async with worker_engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE talaqi.registrations SET method = 'cash_organizer_confirmed', "
                    "state = 'cash_pending', confirmed_at = NULL, "
                    "cash_expires_at = clock_timestamp() + interval '1 hour' "
                    "WHERE event_id = :event_id AND user_id = :user_id"
                ),
                {"event_id": event_id, "user_id": member.user_id},
            )
        cash_dashboard = await client.get("/api/v1/me/dashboard", headers=member.headers())
        async with worker_engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE talaqi.registrations SET method = 'free', state = 'waitlisted', "
                    "seat_held = false, cash_expires_at = NULL, waitlist_sequence = 1 "
                    "WHERE event_id = :event_id AND user_id = :user_id"
                ),
                {"event_id": event_id, "user_id": member.user_id},
            )
        waitlist_dashboard = await client.get("/api/v1/me/dashboard", headers=member.headers())
        async with worker_engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE talaqi.events SET status = 'cancelled', "
                    "cancelled_at = clock_timestamp() WHERE id = :event_id"
                ),
                {"event_id": event_id},
            )
        cancelled_dashboard = await client.get("/api/v1/me/dashboard", headers=member.headers())
        async with worker_engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE talaqi.events SET status = 'published', cancelled_at = NULL, "
                    "suspended_at = clock_timestamp(), suspension_reason = 'safety_review' "
                    "WHERE id = :event_id"
                ),
                {"event_id": event_id},
            )
        suspended_dashboard = await client.get("/api/v1/me/dashboard", headers=member.headers())

    assert member_response.status_code == 200, member_response.text
    member_body = member_response.json()
    assert [item["id"] for item in member_body["upcoming_events"]] == [str(event_id)]
    assert [item["id"] for item in member_body["saved_events"]] == [str(event_id)]
    assert [item["id"] for item in member_body["joined_clubs"]] == [str(club_id)]
    assert len(member_body["notifications"]) == 1
    assert "profile_incomplete" in member_body["profile_blockers"]
    assert outsider_response.json()["upcoming_events"] == []
    assert outsider_response.json()["joined_clubs"] == []
    assert organizer_response.status_code == 200
    assert denied_organizer.status_code == 403
    assert [item["id"] for item in organizer_response.json()["clubs"]] == [str(club_id)]
    assert {item["id"] for item in organizer_response.json()["events"]} == {
        str(event_id),
        str(private_event_id),
    }
    assert cash_dashboard.json()["upcoming_events"][0]["registration_state"] == ("cash_pending")
    assert waitlist_dashboard.json()["upcoming_events"][0]["registration_state"] == ("waitlisted")
    assert cancelled_dashboard.json()["upcoming_events"] == []
    assert suspended_dashboard.json()["upcoming_events"] == []
    assert suspended_dashboard.json()["saved_events"] == []
