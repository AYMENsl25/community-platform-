from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.clubs.schemas import ClubCard, ClubDetail


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
