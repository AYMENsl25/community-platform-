from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_authenticated_user
from app.db.session import get_db_session
from app.modules.me.schemas import (
    MyClubSummary,
    MyEventSummary,
    MyRegistrationSummary,
    MySavedEventSummary,
)
from app.modules.me.service import (
    get_my_clubs,
    get_my_events,
    get_my_registrations,
    get_my_saved_events,
)

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/clubs", response_model=list[MyClubSummary])
async def list_my_clubs(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> list[MyClubSummary]:
    return await get_my_clubs(session, current_user)


@router.get("/events", response_model=list[MyEventSummary])
async def list_my_events(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> list[MyEventSummary]:
    return await get_my_events(session, current_user)


@router.get("/registrations", response_model=list[MyRegistrationSummary])
async def list_my_registrations(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> list[MyRegistrationSummary]:
    return await get_my_registrations(session, current_user)


@router.get("/saved-events", response_model=list[MySavedEventSummary])
async def list_my_saved_events(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> list[MySavedEventSummary]:
    return await get_my_saved_events(session, current_user)
