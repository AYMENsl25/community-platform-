from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DashboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def member(self, user_id: UUID) -> dict[str, object]:
        upcoming = await self._rows(
            """SELECT event.id, event.title, event.start_at, event.status::text,
                      registration.state::text AS registration_state,
                      '/events/' || event.id::text AS action_path
               FROM talaqi.registrations AS registration
               JOIN talaqi.events AS event ON event.id = registration.event_id
               LEFT JOIN talaqi.clubs AS club ON club.id = event.club_id
               WHERE registration.user_id = :user_id
                 AND registration.state IN ('confirmed', 'cash_pending', 'waitlisted')
                 AND event.status = 'published'
                 AND event.suspended_at IS NULL
                 AND (club.id IS NULL OR club.status = 'published')
                 AND (event.start_at IS NULL OR event.start_at >= clock_timestamp())
               ORDER BY event.start_at NULLS LAST, event.id LIMIT 12""",
            user_id,
        )
        saved = await self._rows(
            """SELECT event.id, event.title, event.start_at, event.status::text,
                      '/events/' || event.id::text AS action_path
               FROM talaqi.saved_events AS saved
               JOIN talaqi.events AS event ON event.id = saved.event_id
               LEFT JOIN talaqi.clubs AS club ON club.id = event.club_id
               WHERE saved.user_id = :user_id
                 AND event.status = 'published' AND event.visibility = 'public'
                 AND event.suspended_at IS NULL
                 AND (club.id IS NULL OR club.status = 'published')
               ORDER BY saved.created_at DESC, event.id LIMIT 8""",
            user_id,
        )
        clubs = await self._rows(
            """SELECT club.id, club.name, club.slug, membership.role::text,
                      club.status::text, '/clubs/' || club.slug AS action_path
               FROM talaqi.club_memberships AS membership
               JOIN talaqi.clubs AS club ON club.id = membership.club_id
               WHERE membership.user_id = :user_id
               ORDER BY membership.joined_at DESC, club.id LIMIT 12""",
            user_id,
        )
        notifications = await self._rows(
            """SELECT id, type_key, title_key, body_key, action_path, read_at, created_at
               FROM talaqi.notifications WHERE recipient_user_id = :user_id
               ORDER BY created_at DESC, id DESC LIMIT 10""",
            user_id,
        )
        return {
            "upcoming_events": upcoming,
            "saved_events": saved,
            "joined_clubs": clubs,
            "notifications": notifications,
            "profile_blockers": (),
        }

    async def organizer(self, user_id: UUID) -> dict[str, object]:
        clubs = await self._rows(
            """SELECT club.id, club.name, club.slug, membership.role::text,
                      club.status::text,
                      count(request.id) FILTER (WHERE request.status = 'pending')::int
                          AS pending_requests,
                      '/organizer/clubs' AS action_path
               FROM talaqi.club_memberships AS membership
               JOIN talaqi.clubs AS club ON club.id = membership.club_id
               LEFT JOIN talaqi.club_join_requests AS request ON request.club_id = club.id
               WHERE membership.user_id = :user_id
                 AND membership.role IN ('owner', 'admin')
               GROUP BY club.id, membership.role
               ORDER BY club.created_at DESC, club.id LIMIT 20""",
            user_id,
        )
        events = await self._rows(
            """SELECT event.id, event.title, event.start_at, event.status::text,
                      event.capacity,
                      count(registration.id) FILTER (
                          WHERE registration.state IN ('confirmed', 'cash_pending')
                      )::int AS held,
                      count(registration.id) FILTER (
                          WHERE registration.state = 'cash_pending'
                      )::int AS cash_pending,
                      '/organizer/events' AS action_path
               FROM talaqi.events AS event
               LEFT JOIN talaqi.club_memberships AS membership
                 ON membership.club_id = event.club_id
                AND membership.user_id = :user_id
                AND membership.role IN ('owner', 'admin')
               LEFT JOIN talaqi.registrations AS registration
                 ON registration.event_id = event.id
               WHERE (event.ownership_type = 'independent'
                      AND event.owner_user_id = :user_id)
                  OR membership.user_id IS NOT NULL
               GROUP BY event.id
               ORDER BY event.start_at NULLS LAST, event.id LIMIT 24""",
            user_id,
        )
        alerts: list[dict[str, str]] = []
        if any(int(row.get("pending_requests") or 0) for row in clubs):
            alerts.append({"key": "membership_requests", "action_path": "/organizer/clubs"})
        if any(int(row.get("cash_pending") or 0) for row in events):
            alerts.append(
                {
                    "key": "cash_pending",
                    "action_path": "/organizer/events?state=cash_pending",
                }
            )
        if any(row.get("status") == "draft" for row in events):
            alerts.append({"key": "draft_events", "action_path": "/organizer/events?status=draft"})
        return {"clubs": clubs, "events": events, "alerts": tuple(alerts)}

    async def _rows(self, query: str, user_id: UUID) -> list[Mapping[str, Any]]:
        rows = (await self._session.execute(text(query), {"user_id": user_id})).mappings()
        return [dict(row) for row in rows]


__all__ = ["DashboardRepository"]
