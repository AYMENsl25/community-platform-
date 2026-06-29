from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.clubs.schemas import ClubCard, ClubDetail, ClubMembershipState


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
            """
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
            """
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
            WHERE id = CAST(:club_id AS uuid)
            LIMIT 1
            """
        ),
        {"club_id": club_id},
    )
    row = result.first()
    return ClubDetail.model_validate(row._mapping) if row else None


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
