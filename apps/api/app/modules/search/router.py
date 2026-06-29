from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.search.schemas import SearchResult
from app.modules.search.service import search_public_content

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchResult])
async def search(
    q: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    entity_type: str | None = Query(default=None, pattern="^(club|event)$"),
    city: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[SearchResult]:
    return await search_public_content(
        session,
        q=q,
        limit=limit,
        offset=offset,
        entity_type=entity_type,
        city=city,
    )
