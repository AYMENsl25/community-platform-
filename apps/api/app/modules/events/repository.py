from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.events.schemas import (
    EventCapacity,
    EventCard,
    EventCreate,
    EventDetail,
    EventRegistrationState,
    EventUpdate,
    SavedEventState,
)


async def list_public_events(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    city: str | None = None,
    event_type: str | None = None,
    q: str | None = None,
) -> list[EventCard]:
    filters = []
    params: dict[str, object] = {"limit": limit, "offset": offset}

    if city:
        filters.append("city ILIKE :city")
        params["city"] = city

    if event_type:
        filters.append("event_type = :event_type")
        params["event_type"] = event_type

    if q:
        filters.append(
            "(title ILIKE :q OR description ILIKE :q OR location_name ILIKE :q)"
        )
        params["q"] = f"%{q}%"

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    result = await session.execute(
        text(
            f"""
            SELECT
              id::text AS id,
              club_id::text AS club_id,
              club_name,
              title,
              slug,
              description,
              event_type,
              starts_at,
              ends_at,
              city,
              country,
              location_name,
              capacity,
              registered_count,
              waitlist_count,
              price_amount,
              currency,
              cover_image_url,
              category_name
            FROM public_event_cards
            {where_clause}
            ORDER BY starts_at ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    return [EventCard.model_validate(row._mapping) for row in result]


async def get_event_by_id(session: AsyncSession, event_id: str) -> EventDetail | None:
    result = await session.execute(
        text(
            """
            SELECT
              id::text AS id,
              club_id::text AS club_id,
              created_by::text AS created_by,
              title,
              slug,
              description,
              event_type,
              starts_at,
              ends_at,
              timezone,
              location_name,
              address,
              city,
              country,
              lat,
              lng,
              capacity,
              registered_count,
              waitlist_count,
              price_amount,
              currency,
              status::text AS status,
              requires_approval,
              cover_image_url,
              club_name,
              club_slug,
              club_logo_url,
              organizer_name,
              organizer_avatar_url,
              is_full
            FROM event_detail_view
            WHERE id = CAST(:event_id AS uuid)
            LIMIT 1
            """
        ),
        {"event_id": event_id},
    )
    row = result.first()
    return EventDetail.model_validate(row._mapping) if row else None


async def get_club_management_context(
    session: AsyncSession,
    *,
    club_id: str,
    user_id: str,
) -> dict[str, str | None] | None:
    result = await session.execute(
        text(
            """
            SELECT
              c.owner_id::text AS owner_id,
              cm.role::text AS member_role,
              cm.status::text AS member_status
            FROM clubs c
            LEFT JOIN club_members cm
              ON cm.club_id = c.id
             AND cm.user_id = CAST(:user_id AS uuid)
            WHERE c.id = CAST(:club_id AS uuid)
              AND c.deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"club_id": club_id, "user_id": user_id},
    )
    row = result.first()
    return dict(row._mapping) if row else None


async def get_event_management_context(
    session: AsyncSession,
    *,
    event_id: str,
    user_id: str,
) -> dict[str, str | None] | None:
    result = await session.execute(
        text(
            """
            SELECT
              e.id::text AS event_id,
              e.club_id::text AS club_id,
              c.owner_id::text AS owner_id,
              cm.role::text AS member_role,
              cm.status::text AS member_status
            FROM events e
            JOIN clubs c ON c.id = e.club_id
            LEFT JOIN club_members cm
              ON cm.club_id = c.id
             AND cm.user_id = CAST(:user_id AS uuid)
            WHERE e.id = CAST(:event_id AS uuid)
              AND e.deleted_at IS NULL
              AND c.deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"event_id": event_id, "user_id": user_id},
    )
    row = result.first()
    return dict(row._mapping) if row else None


async def insert_event(
    session: AsyncSession,
    *,
    payload: EventCreate,
    created_by: str,
    slug: str,
) -> str:
    values: dict[str, Any] = payload.model_dump()
    values.update({"created_by": created_by, "slug": slug})
    result = await session.execute(
        text(
            """
            INSERT INTO events (
              club_id,
              created_by,
              title,
              slug,
              description,
              event_type,
              starts_at,
              ends_at,
              timezone,
              location_name,
              address,
              city,
              country,
              lat,
              lng,
              capacity,
              price_amount,
              currency,
              status,
              requires_approval,
              cover_image_url
            )
            VALUES (
              CAST(:club_id AS uuid),
              CAST(:created_by AS uuid),
              :title,
              :slug,
              :description,
              :event_type,
              :starts_at,
              :ends_at,
              :timezone,
              :location_name,
              :address,
              :city,
              :country,
              :lat,
              :lng,
              :capacity,
              :price_amount,
              :currency,
              CAST(:status AS event_status),
              :requires_approval,
              :cover_image_url
            )
            RETURNING id::text AS id
            """
        ),
        values,
    )
    return str(result.one()._mapping["id"])


async def update_event_by_id(
    session: AsyncSession,
    *,
    event_id: str,
    payload: EventUpdate,
) -> None:
    values: dict[str, Any] = payload.model_dump(exclude_unset=True)
    if not values:
        return

    assignments: list[str] = []
    params: dict[str, Any] = {"event_id": event_id}
    for field_name, field_value in values.items():
        params[field_name] = field_value
        if field_name == "status":
            assignments.append("status = CAST(:status AS event_status)")
        else:
            assignments.append(f"{field_name} = :{field_name}")

    assignments.append("updated_at = now()")
    await session.execute(
        text(
            f"""
            UPDATE events
            SET {", ".join(assignments)}
            WHERE id = CAST(:event_id AS uuid)
              AND deleted_at IS NULL
            """
        ),
        params,
    )


async def soft_delete_event_by_id(session: AsyncSession, *, event_id: str) -> None:
    await session.execute(
        text(
            """
            UPDATE events
            SET deleted_at = now(),
                status = 'cancelled',
                updated_at = now()
            WHERE id = CAST(:event_id AS uuid)
              AND deleted_at IS NULL
            """
        ),
        {"event_id": event_id},
    )


async def get_event_capacity_by_id(
    session: AsyncSession, event_id: str
) -> EventCapacity | None:
    result = await session.execute(
        text(
            """
            SELECT
              event_id::text AS event_id,
              capacity,
              registered_count,
              waitlist_count,
              spots_left,
              is_full
            FROM event_capacity_view
            WHERE event_id = CAST(:event_id AS uuid)
            LIMIT 1
            """
        ),
        {"event_id": event_id},
    )
    row = result.first()
    return EventCapacity.model_validate(row._mapping) if row else None


async def register_user_for_event(
    session: AsyncSession, *, user_id: str, event_id: str
) -> EventRegistrationState:
    result = await session.execute(
        text(
            """
            SELECT
              id::text AS id,
              event_id::text AS event_id,
              user_id::text AS user_id,
              status::text AS status,
              waitlist_position,
              note,
              registered_at,
              confirmed_at,
              cancelled_at
            FROM register_for_event(CAST(:user_id AS uuid), CAST(:event_id AS uuid))
            """
        ),
        {"user_id": user_id, "event_id": event_id},
    )
    row = result.one()
    return EventRegistrationState.model_validate(row._mapping)


async def cancel_user_event_registration(
    session: AsyncSession, *, user_id: str, event_id: str
) -> None:
    await session.execute(
        text(
            "SELECT cancel_event_registration(CAST(:user_id AS uuid), CAST(:event_id AS uuid))"
        ),
        {"user_id": user_id, "event_id": event_id},
    )


async def get_user_event_registration(
    session: AsyncSession,
    *,
    user_id: str,
    event_id: str,
) -> EventRegistrationState | None:
    result = await session.execute(
        text(
            """
            SELECT
              id::text AS id,
              event_id::text AS event_id,
              user_id::text AS user_id,
              status::text AS status,
              waitlist_position,
              note,
              registered_at,
              confirmed_at,
              cancelled_at
            FROM event_registrations
            WHERE user_id = CAST(:user_id AS uuid)
              AND event_id = CAST(:event_id AS uuid)
            LIMIT 1
            """
        ),
        {"user_id": user_id, "event_id": event_id},
    )
    row = result.first()
    return EventRegistrationState.model_validate(row._mapping) if row else None


async def save_event_for_user(
    session: AsyncSession, *, user_id: str, event_id: str
) -> SavedEventState:
    await session.execute(
        text(
            """
            INSERT INTO saved_events (user_id, event_id)
            VALUES (CAST(:user_id AS uuid), CAST(:event_id AS uuid))
            ON CONFLICT (user_id, event_id) DO NOTHING
            """
        ),
        {"user_id": user_id, "event_id": event_id},
    )
    result = await session.execute(
        text(
            """
            SELECT
              user_id::text AS user_id,
              event_id::text AS event_id,
              true AS saved,
              created_at
            FROM saved_events
            WHERE user_id = CAST(:user_id AS uuid)
              AND event_id = CAST(:event_id AS uuid)
            LIMIT 1
            """
        ),
        {"user_id": user_id, "event_id": event_id},
    )
    row = result.one()
    return SavedEventState.model_validate(row._mapping)


async def unsave_event_for_user(
    session: AsyncSession, *, user_id: str, event_id: str
) -> SavedEventState:
    await session.execute(
        text(
            """
            DELETE FROM saved_events
            WHERE user_id = CAST(:user_id AS uuid)
              AND event_id = CAST(:event_id AS uuid)
            """
        ),
        {"user_id": user_id, "event_id": event_id},
    )
    return SavedEventState(user_id=user_id, event_id=event_id, saved=False)
