from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_authenticated_user
from app.db.session import get_db_session
from app.modules.clubs.schemas import (
    ClubCard,
    ClubCreate,
    ClubDeletionState,
    ClubDetail,
    ClubEventSummary,
    ClubMemberPreview,
    ClubMembershipState,
    ClubUpdate,
    ClubViewerState,
)
from app.modules.clubs.service import (
    ClubActionFailedError,
    ClubForbiddenError,
    ClubMembershipNotFoundError,
    ClubNotFoundError,
    create_club_action,
    delete_club_action,
    get_club_detail,
    get_club_events,
    get_club_members,
    get_my_club_membership_state,
    join_club_action,
    leave_club_action,
    list_clubs,
    update_club_action,
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


@router.post("", response_model=ClubDetail, status_code=status.HTTP_201_CREATED)
async def create_club(
    payload: ClubCreate,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> ClubDetail:
    try:
        return await create_club_action(
            session, payload=payload, current_user=current_user
        )
    except ClubActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Club creation failed"
        ) from exc


@router.patch("/{club_id}", response_model=ClubDetail)
async def update_club(
    club_id: str,
    payload: ClubUpdate,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> ClubDetail:
    try:
        return await update_club_action(
            session, club_id=club_id, payload=payload, current_user=current_user
        )
    except ClubNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club not found"
        ) from exc
    except ClubForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this club.",
        ) from exc
    except ClubActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Club update failed"
        ) from exc


@router.delete("/{club_id}", response_model=ClubDeletionState)
async def delete_club(
    club_id: str,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> ClubDeletionState:
    try:
        return await delete_club_action(
            session, club_id=club_id, current_user=current_user
        )
    except ClubNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club not found"
        ) from exc
    except ClubForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this club.",
        ) from exc
    except ClubActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Club deletion failed"
        ) from exc


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


@router.get("/{club_id}/members", response_model=list[ClubMemberPreview])
async def list_club_members_preview(
    club_id: str,
    limit: int = Query(default=6, ge=1, le=24),
    session: AsyncSession = Depends(get_db_session),
) -> list[ClubMemberPreview]:
    try:
        return await get_club_members(session, club_id=club_id, limit=limit)
    except ClubNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club not found"
        ) from exc


@router.get("/{club_id}/events", response_model=list[ClubEventSummary])
async def list_club_events_preview(
    club_id: str,
    limit: int = Query(default=6, ge=1, le=24),
    session: AsyncSession = Depends(get_db_session),
) -> list[ClubEventSummary]:
    try:
        return await get_club_events(session, club_id=club_id, limit=limit)
    except ClubNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club not found"
        ) from exc


@router.get("/{club_id}/membership", response_model=ClubViewerState)
async def get_club_membership_state(
    club_id: str,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> ClubViewerState:
    try:
        return await get_my_club_membership_state(
            session,
            club_id=club_id,
            current_user=current_user,
        )
    except ClubNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club not found"
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
