from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_authenticated_user
from app.db.session import get_db_session
from app.modules.organizer_requests.schemas import (
    OrganizerRequestCreate,
    OrganizerRequestReview,
    OrganizerRequestState,
)
from app.modules.organizer_requests.service import (
    AdminRequiredError,
    OrganizerRequestActionFailedError,
    OrganizerRequestNotFoundError,
    get_my_organizer_request,
    list_admin_organizer_requests,
    review_admin_organizer_request,
    submit_my_organizer_request,
)

router = APIRouter(tags=["organizer-requests"])


@router.get("/me/organizer-request", response_model=OrganizerRequestState | None)
async def get_my_request(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> OrganizerRequestState | None:
    return await get_my_organizer_request(session, current_user=current_user)


@router.post(
    "/me/organizer-request",
    response_model=OrganizerRequestState,
    status_code=status.HTTP_201_CREATED,
)
async def submit_my_request(
    payload: OrganizerRequestCreate,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> OrganizerRequestState:
    try:
        return await submit_my_organizer_request(
            session, current_user=current_user, payload=payload
        )
    except OrganizerRequestActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Organizer request failed"
        ) from exc


@router.get("/admin/organizer-requests", response_model=list[OrganizerRequestState])
async def list_requests(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    status_filter: str | None = Query(
        default=None, pattern="^(pending|approved|rejected)$"
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[OrganizerRequestState]:
    try:
        return await list_admin_organizer_requests(
            session,
            current_user=current_user,
            status_filter=status_filter,
            limit=limit,
            offset=offset,
        )
    except AdminRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        ) from exc


@router.post(
    "/admin/organizer-requests/{request_id}/approve",
    response_model=OrganizerRequestState,
)
async def approve_request(
    request_id: str,
    payload: OrganizerRequestReview,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> OrganizerRequestState:
    return await _review_request(session, current_user, request_id, "approved", payload)


@router.post(
    "/admin/organizer-requests/{request_id}/reject",
    response_model=OrganizerRequestState,
)
async def reject_request(
    request_id: str,
    payload: OrganizerRequestReview,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> OrganizerRequestState:
    return await _review_request(session, current_user, request_id, "rejected", payload)


async def _review_request(
    session: AsyncSession,
    current_user: CurrentUser,
    request_id: str,
    review_status: str,
    payload: OrganizerRequestReview,
) -> OrganizerRequestState:
    try:
        return await review_admin_organizer_request(
            session,
            current_user=current_user,
            request_id=request_id,
            review_status=review_status,
            payload=payload,
        )
    except AdminRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        ) from exc
    except OrganizerRequestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organizer request not found"
        ) from exc
    except OrganizerRequestActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organizer request review failed",
        ) from exc
