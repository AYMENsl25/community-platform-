from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.search.repository import search_public_index
from app.modules.search.schemas import SearchResult


async def search_public_content(
    session: AsyncSession,
    *,
    q: str,
    limit: int,
    offset: int,
    entity_type: str | None = None,
    city: str | None = None,
) -> list[SearchResult]:
    normalized_query = q.strip()
    return await search_public_index(
        session,
        q=normalized_query,
        limit=limit,
        offset=offset,
        entity_type=entity_type,
        city=city,
    )
