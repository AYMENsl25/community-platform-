from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.me.schemas import (
    MyClubSummary,
    MyEventSummary,
    MyRegistrationSummary,
    MySavedEventSummary,
)


async def list_user_clubs(
    session: AsyncSession, *, user_id: str
) -> list[MyClubSummary]:
    result = await session.execute(
        text(
            """
            SELECT
              cd.id::text AS id,
              cd.name,
              cd.slug,
              cd.description,
              cd.logo_url,
              cd.cover_image_url,
              cd.city,
              cd.country,
              cd.member_count,
              cd.category_name,
              cd.visibility::text AS visibility,
              cd.status::text AS status,
              cm.role::text AS member_role,
              cm.status::text AS member_status
            FROM club_members cm
            JOIN club_detail_view cd ON cd.id = cm.club_id
            WHERE cm.user_id = CAST(:user_id AS uuid)
              AND cm.status IN ('active', 'pending')
            ORDER BY cm.joined_at DESC
            """
        ),
        {"user_id": user_id},
    )
    return [MyClubSummary.model_validate(row._mapping) for row in result]


async def list_user_managed_events(
    session: AsyncSession, *, user_id: str
) -> list[MyEventSummary]:
    result = await session.execute(
        text(
            """
            SELECT DISTINCT
              ev.id::text AS id,
              ev.club_id::text AS club_id,
              ev.club_name,
              ev.title,
              ev.slug,
              ev.event_type,
              ev.starts_at,
              ev.ends_at,
              ev.city,
              ev.status::text AS status,
              ev.capacity,
              ev.registered_count,
              ev.waitlist_count,
              ev.price_amount,
              ev.currency,
              ev.cover_image_url
            FROM event_detail_view ev
            JOIN clubs c ON c.id = ev.club_id
            LEFT JOIN club_members cm
              ON cm.club_id = ev.club_id
             AND cm.user_id = CAST(:user_id AS uuid)
            WHERE ev.created_by = CAST(:user_id AS uuid)
               OR c.owner_id = CAST(:user_id AS uuid)
               OR (cm.role IN ('owner', 'admin') AND cm.status = 'active')
            ORDER BY ev.starts_at DESC
            """
        ),
        {"user_id": user_id},
    )
    return [MyEventSummary.model_validate(row._mapping) for row in result]


async def list_user_registrations(
    session: AsyncSession,
    *,
    user_id: str,
) -> list[MyRegistrationSummary]:
    result = await session.execute(
        text(
            """
            SELECT
              ev.id::text AS event_id,
              ev.club_id::text AS club_id,
              c.name AS club_name,
              ev.title,
              ev.slug,
              ev.event_type,
              ev.starts_at,
              urev.registration_status::text AS registration_status,
              urev.registered_at,
              ev.city,
              ev.cover_image_url
            FROM user_registered_events_view urev
            JOIN events ev ON ev.id = urev.id
            JOIN clubs c ON c.id = ev.club_id
            WHERE urev.user_id = CAST(:user_id AS uuid)
            ORDER BY ev.starts_at ASC
            """
        ),
        {"user_id": user_id},
    )
    return [MyRegistrationSummary.model_validate(row._mapping) for row in result]


async def list_user_saved_events(
    session: AsyncSession,
    *,
    user_id: str,
) -> list[MySavedEventSummary]:
    result = await session.execute(
        text(
            """
            SELECT
              ev.id::text AS event_id,
              ev.club_id::text AS club_id,
              ev.club_name,
              ev.title,
              ev.slug,
              ev.event_type,
              ev.starts_at,
              ev.city,
              se.created_at AS saved_at,
              ev.cover_image_url
            FROM saved_events se
            JOIN event_detail_view ev ON ev.id = se.event_id
            WHERE se.user_id = CAST(:user_id AS uuid)
            ORDER BY se.created_at DESC
            """
        ),
        {"user_id": user_id},
    )
    return [MySavedEventSummary.model_validate(row._mapping) for row in result]
