from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.clubs.repository import get_club_by_slug, list_public_clubs
from app.modules.clubs.schemas import ClubCard, ClubDetail


async def list_clubs(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    city: str | None = None,
    q: str | None = None,
) -> list[ClubCard]:
    return await list_public_clubs(session, limit=limit, offset=offset, city=city, q=q)


async def get_club_detail(session: AsyncSession, slug: str) -> ClubDetail | None:
    return await get_club_by_slug(session, slug)
