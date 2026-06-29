from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.modules.me.repository import (
    list_user_clubs,
    list_user_managed_events,
    list_user_notifications,
    list_user_registrations,
    list_user_saved_events,
    mark_all_user_notifications_read,
    mark_user_notification_read,
)
from app.modules.me.schemas import (
    MyClubSummary,
    MyEventSummary,
    MyNotificationSummary,
    MyRegistrationSummary,
    MySavedEventSummary,
    NotificationReadState,
    NotificationsReadAllState,
)


class NotificationNotFoundError(Exception):
    pass


class NotificationActionFailedError(Exception):
    pass


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


async def get_my_notifications(
    session: AsyncSession,
    current_user: CurrentUser,
    *,
    limit: int,
    offset: int,
    unread_only: bool,
) -> list[MyNotificationSummary]:
    return await list_user_notifications(
        session,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )


async def mark_my_notification_read(
    session: AsyncSession,
    current_user: CurrentUser,
    *,
    notification_id: str,
) -> NotificationReadState:
    try:
        state = await mark_user_notification_read(
            session,
            user_id=current_user.id,
            notification_id=notification_id,
        )
        if state is None:
            raise NotificationNotFoundError
        await session.commit()
        return state
    except NotificationNotFoundError:
        await session.rollback()
        raise
    except SQLAlchemyError as exc:
        await session.rollback()
        raise NotificationActionFailedError(str(exc)) from exc


async def mark_all_my_notifications_read(
    session: AsyncSession,
    current_user: CurrentUser,
) -> NotificationsReadAllState:
    try:
        updated_count = await mark_all_user_notifications_read(
            session, user_id=current_user.id
        )
        await session.commit()
        return NotificationsReadAllState(updated_count=updated_count)
    except SQLAlchemyError as exc:
        await session.rollback()
        raise NotificationActionFailedError(str(exc)) from exc
