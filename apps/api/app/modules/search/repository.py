from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.search.schemas import SearchResult


async def search_public_index(
    session: AsyncSession,
    *,
    q: str,
    limit: int,
    offset: int,
    entity_type: str | None = None,
    city: str | None = None,
) -> list[SearchResult]:
    filters = ["(title ILIKE :query OR body ILIKE :query)"]
    params: dict[str, object] = {
        "query": f"%{q}%",
        "raw_query": q,
        "limit": limit,
        "offset": offset,
    }

    if entity_type:
        filters.append("entity_type = :entity_type")
        params["entity_type"] = entity_type

    if city:
        filters.append("city ILIKE :city")
        params["city"] = city

    result = await session.execute(
        text(
            f"""
            SELECT
              entity_type,
              entity_id::text AS entity_id,
              title,
              body,
              city,
              country,
              created_at,
              greatest(
                similarity(title, :raw_query),
                similarity(coalesce(body, ''), :raw_query)
              )::float AS rank
            FROM search_index_view
            WHERE {" AND ".join(filters)}
            ORDER BY rank DESC, created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    return [SearchResult.model_validate(row._mapping) for row in result]
