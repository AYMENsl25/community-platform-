from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.modules.me.repository import (
    list_user_clubs,
    list_user_managed_events,
    list_user_registrations,
    list_user_saved_events,
)
from app.modules.me.schemas import (
    MyClubSummary,
    MyEventSummary,
    MyRegistrationSummary,
    MySavedEventSummary,
)


async def get_my_clubs(
    session: AsyncSession, current_user: CurrentUser
) -> list[MyClubSummary]:
    return await list_user_clubs(session, user_id=current_user.id)


async def get_my_events(
    session: AsyncSession, current_user: CurrentUser
) -> list[MyEventSummary]:
    return await list_user_managed_events(session, user_id=current_user.id)


async def get_my_registrations(
    session: AsyncSession,
    current_user: CurrentUser,
) -> list[MyRegistrationSummary]:
    return await list_user_registrations(session, user_id=current_user.id)


async def get_my_saved_events(
    session: AsyncSession,
    current_user: CurrentUser,
) -> list[MySavedEventSummary]:
    return await list_user_saved_events(session, user_id=current_user.id)
