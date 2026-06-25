from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.clubs.schemas import ClubCard, ClubDetail
from app.modules.clubs.service import get_club_detail, list_clubs

router = APIRouter(prefix="/clubs", tags=["clubs"])


@router.get("", response_model=list[ClubCard])
async def list_club_cards(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    city: str | None = None,
    q: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[ClubCard]:
    return await list_clubs(session, limit=limit, offset=offset, city=city, q=q)


@router.get("/{slug}", response_model=ClubDetail)
async def get_club(slug: str, session: AsyncSession = Depends(get_db_session)) -> ClubDetail:
    club = await get_club_detail(session, slug)
    if club is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found")
    return club
