from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.clubs.schemas import (
    ClubCard,
    ClubCreate,
    ClubDetail,
    ClubEventSummary,
    ClubMemberPreview,
    ClubMembershipState,
    ClubUpdate,
    ClubViewerState,
)


CLUB_DETAIL_SELECT = """
SELECT
  id::text AS id,
  owner_id::text AS owner_id,
  category_id::text AS category_id,
  name,
  slug,
  description,
  logo_url,
  cover_image_url,
  city,
  country,
  visibility::text AS visibility,
  status::text AS status,
  member_count,
  category_name,
  owner_name,
  owner_avatar_url
FROM club_detail_view
"""


async def list_public_clubs(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    city: str | None = None,
    q: str | None = None,
) -> list[ClubCard]:
    filters = []
    params: dict[str, object] = {"limit": limit, "offset": offset}

    if city:
        filters.append("city ILIKE :city")
        params["city"] = city

    if q:
        filters.append("(name ILIKE :q OR description ILIKE :q)")
        params["q"] = f"%{q}%"

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    result = await session.execute(
        text(
            f"""
            SELECT
              id::text AS id,
              name,
              slug,
              description,
              logo_url,
              cover_image_url,
              city,
              country,
              member_count,
              category_name
            FROM public_club_cards
            {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    return [ClubCard.model_validate(row._mapping) for row in result]


async def get_club_by_slug(session: AsyncSession, slug: str) -> ClubDetail | None:
    result = await session.execute(
        text(
            f"""
            {CLUB_DETAIL_SELECT}
            WHERE slug = :slug
            LIMIT 1
            """
        ),
        {"slug": slug},
    )
    row = result.first()
    return ClubDetail.model_validate(row._mapping) if row else None


async def get_club_by_id(session: AsyncSession, club_id: str) -> ClubDetail | None:
    result = await session.execute(
        text(
            f"""
            {CLUB_DETAIL_SELECT}
            WHERE id = CAST(:club_id AS uuid)
            LIMIT 1
            """
        ),
        {"club_id": club_id},
    )
    row = result.first()
    return ClubDetail.model_validate(row._mapping) if row else None


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


async def insert_club(
    session: AsyncSession,
    *,
    payload: ClubCreate,
    owner_id: str,
    slug: str,
) -> str:
    values: dict[str, Any] = payload.model_dump()
    values.update({"owner_id": owner_id, "slug": slug})
    result = await session.execute(
        text(
            """
            INSERT INTO clubs (
              owner_id,
              category_id,
              name,
              slug,
              description,
              logo_url,
              cover_image_url,
              city,
              country,
              visibility,
              status
            )
            VALUES (
              CAST(:owner_id AS uuid),
              CAST(:category_id AS uuid),
              :name,
              :slug,
              :description,
              :logo_url,
              :cover_image_url,
              :city,
              :country,
              CAST(:visibility AS club_visibility),
              CAST(:status AS club_status)
            )
            RETURNING id::text AS id
            """
        ),
        values,
    )
    return str(result.one()._mapping["id"])


async def add_club_owner_membership(
    session: AsyncSession,
    *,
    club_id: str,
    owner_id: str,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO club_members (club_id, user_id, role, status)
            VALUES (CAST(:club_id AS uuid), CAST(:owner_id AS uuid), 'owner', 'active')
            ON CONFLICT (club_id, user_id)
            DO UPDATE SET
              role = 'owner',
              status = 'active',
              left_at = NULL,
              updated_at = now()
            """
        ),
        {"club_id": club_id, "owner_id": owner_id},
    )


async def update_club_by_id(
    session: AsyncSession,
    *,
    club_id: str,
    payload: ClubUpdate,
) -> None:
    values: dict[str, Any] = payload.model_dump(exclude_unset=True)
    if not values:
        return

    assignments: list[str] = []
    params: dict[str, Any] = {"club_id": club_id}
    for field_name, field_value in values.items():
        params[field_name] = field_value
        if field_name == "visibility":
            assignments.append("visibility = CAST(:visibility AS club_visibility)")
        elif field_name == "status":
            assignments.append("status = CAST(:status AS club_status)")
        elif field_name == "category_id":
            assignments.append("category_id = CAST(:category_id AS uuid)")
        else:
            assignments.append(f"{field_name} = :{field_name}")

    assignments.append("updated_at = now()")
    await session.execute(
        text(
            f"""
            UPDATE clubs
            SET {", ".join(assignments)}
            WHERE id = CAST(:club_id AS uuid)
              AND deleted_at IS NULL
            """
        ),
        params,
    )


async def soft_delete_club_by_id(session: AsyncSession, *, club_id: str) -> None:
    await session.execute(
        text(
            """
            UPDATE clubs
            SET deleted_at = now(),
                status = 'archived',
                updated_at = now()
            WHERE id = CAST(:club_id AS uuid)
              AND deleted_at IS NULL
            """
        ),
        {"club_id": club_id},
    )


async def list_club_member_preview(
    session: AsyncSession,
    *,
    club_id: str,
    limit: int,
) -> list[ClubMemberPreview]:
    result = await session.execute(
        text(
            """
            SELECT
              u.id::text AS user_id,
              u.display_name,
              u.avatar_url,
              cm.role::text AS role,
              cm.joined_at
            FROM club_members cm
            JOIN users u ON u.id = cm.user_id
            WHERE cm.club_id = CAST(:club_id AS uuid)
              AND cm.status = 'active'
              AND u.deleted_at IS NULL
            ORDER BY
              CASE cm.role
                WHEN 'owner' THEN 0
                WHEN 'admin' THEN 1
                ELSE 2
              END,
              cm.joined_at ASC
            LIMIT :limit
            """
        ),
        {"club_id": club_id, "limit": limit},
    )
    return [ClubMemberPreview.model_validate(row._mapping) for row in result]


async def list_club_upcoming_events(
    session: AsyncSession,
    *,
    club_id: str,
    limit: int,
) -> list[ClubEventSummary]:
    result = await session.execute(
        text(
            """
            SELECT
              id::text AS id,
              title,
              slug,
              event_type,
              starts_at,
              ends_at,
              city,
              registered_count,
              waitlist_count,
              price_amount,
              currency,
              cover_image_url
            FROM event_detail_view
            WHERE club_id = CAST(:club_id AS uuid)
              AND status = 'published'
              AND starts_at >= now()
            ORDER BY starts_at ASC
            LIMIT :limit
            """
        ),
        {"club_id": club_id, "limit": limit},
    )
    return [ClubEventSummary.model_validate(row._mapping) for row in result]


async def get_club_viewer_state(
    session: AsyncSession,
    *,
    club_id: str,
    user_id: str,
) -> ClubViewerState:
    result = await session.execute(
        text(
            """
            SELECT
              CAST(:club_id AS uuid)::text AS club_id,
              cm.role::text AS member_role,
              cm.status::text AS member_status,
              cm.joined_at,
              COALESCE(cm.status = 'active', false) AS is_member
            FROM clubs c
            LEFT JOIN club_members cm
              ON cm.club_id = c.id
             AND cm.user_id = CAST(:user_id AS uuid)
             AND cm.status IN ('active', 'pending')
            WHERE c.id = CAST(:club_id AS uuid)
              AND c.deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"club_id": club_id, "user_id": user_id},
    )
    row = result.first()
    if row is None:
        return ClubViewerState(club_id=club_id, is_member=False)
    return ClubViewerState.model_validate(row._mapping)


async def join_club_for_user(
    session: AsyncSession, *, user_id: str, club_id: str
) -> ClubMembershipState:
    result = await session.execute(
        text(
            """
            SELECT
              id::text AS id,
              club_id::text AS club_id,
              user_id::text AS user_id,
              role::text AS role,
              status::text AS status,
              joined_at,
              left_at
            FROM join_club(CAST(:user_id AS uuid), CAST(:club_id AS uuid))
            """
        ),
        {"user_id": user_id, "club_id": club_id},
    )
    row = result.one()
    return ClubMembershipState.model_validate(row._mapping)


async def leave_club_for_user(
    session: AsyncSession, *, user_id: str, club_id: str
) -> None:
    await session.execute(
        text("SELECT leave_club(CAST(:user_id AS uuid), CAST(:club_id AS uuid))"),
        {"user_id": user_id, "club_id": club_id},
    )


async def get_user_club_membership(
    session: AsyncSession,
    *,
    user_id: str,
    club_id: str,
) -> ClubMembershipState | None:
    result = await session.execute(
        text(
            """
            SELECT
              id::text AS id,
              club_id::text AS club_id,
              user_id::text AS user_id,
              role::text AS role,
              status::text AS status,
              joined_at,
              left_at
            FROM club_members
            WHERE user_id = CAST(:user_id AS uuid)
              AND club_id = CAST(:club_id AS uuid)
            LIMIT 1
            """
        ),
        {"user_id": user_id, "club_id": club_id},
    )
    row = result.first()
    return ClubMembershipState.model_validate(row._mapping) if row else None
