from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_authenticated_user
from app.db.session import get_db_session
from app.modules.clubs.schemas import ClubCard, ClubDetail, ClubMembershipState
from app.modules.clubs.service import (
    ClubActionFailedError,
    ClubMembershipNotFoundError,
    ClubNotFoundError,
    get_club_detail,
    join_club_action,
    leave_club_action,
    list_clubs,
)

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


@router.post("/{club_id}/join", response_model=ClubMembershipState)
async def join_club(
    club_id: str,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> ClubMembershipState:
    try:
        return await join_club_action(
            session, club_id=club_id, current_user=current_user
        )
    except ClubNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club not found"
        ) from exc
    except ClubActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Club join failed"
        ) from exc


@router.post("/{club_id}/leave", response_model=ClubMembershipState)
async def leave_club(
    club_id: str,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> ClubMembershipState:
    try:
        return await leave_club_action(
            session, club_id=club_id, current_user=current_user
        )
    except ClubNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club not found"
        ) from exc
    except ClubMembershipNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club membership not found"
        ) from exc
    except ClubActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Club leave failed"
        ) from exc


@router.get("/{slug}", response_model=ClubDetail)
async def get_club(
    slug: str, session: AsyncSession = Depends(get_db_session)
) -> ClubDetail:
    club = await get_club_detail(session, slug)
    if club is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club not found"
        )
    return club
