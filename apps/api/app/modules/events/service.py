from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.modules.events.repository import (
    cancel_user_event_registration,
    get_event_by_id,
    get_event_capacity_by_id,
    get_user_event_registration,
    list_public_events,
    register_user_for_event,
    save_event_for_user,
    unsave_event_for_user,
)
from app.modules.events.schemas import (
    EventCapacity,
    EventCard,
    EventDetail,
    EventRegistrationState,
    SavedEventState,
)


class EventNotFoundError(Exception):
    pass


class EventRegistrationNotFoundError(Exception):
    pass


class EventActionFailedError(Exception):
    pass


async def list_events(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    city: str | None = None,
    event_type: str | None = None,
    q: str | None = None,
) -> list[EventCard]:
    return await list_public_events(
        session,
        limit=limit,
        offset=offset,
        city=city,
        event_type=event_type,
        q=q,
    )


async def get_event_detail(session: AsyncSession, event_id: str) -> EventDetail | None:
    return await get_event_by_id(session, event_id)


async def get_event_capacity(
    session: AsyncSession, event_id: str
) -> EventCapacity | None:
    return await get_event_capacity_by_id(session, event_id)


async def register_for_event_action(
    session: AsyncSession,
    *,
    event_id: str,
    current_user: CurrentUser,
) -> EventRegistrationState:
    if await get_event_by_id(session, event_id) is None:
        raise EventNotFoundError

    try:
        registration = await register_user_for_event(
            session, user_id=current_user.id, event_id=event_id
        )
        await session.commit()
        return registration
    except SQLAlchemyError as exc:
        await session.rollback()
        raise EventActionFailedError(str(exc)) from exc


async def cancel_registration_action(
    session: AsyncSession,
    *,
    event_id: str,
    current_user: CurrentUser,
) -> EventRegistrationState:
    if await get_event_by_id(session, event_id) is None:
        raise EventNotFoundError

    try:
        await cancel_user_event_registration(
            session, user_id=current_user.id, event_id=event_id
        )
        registration = await get_user_event_registration(
            session, user_id=current_user.id, event_id=event_id
        )
        if registration is None:
            raise EventRegistrationNotFoundError
        await session.commit()
        return registration
    except EventRegistrationNotFoundError:
        await session.rollback()
        raise
    except SQLAlchemyError as exc:
        await session.rollback()
        raise EventActionFailedError(str(exc)) from exc


async def save_event_action(
    session: AsyncSession,
    *,
    event_id: str,
    current_user: CurrentUser,
) -> SavedEventState:
    if await get_event_by_id(session, event_id) is None:
        raise EventNotFoundError

    try:
        saved_event = await save_event_for_user(
            session, user_id=current_user.id, event_id=event_id
        )
        await session.commit()
        return saved_event
    except SQLAlchemyError as exc:
        await session.rollback()
        raise EventActionFailedError(str(exc)) from exc


async def unsave_event_action(
    session: AsyncSession,
    *,
    event_id: str,
    current_user: CurrentUser,
) -> SavedEventState:
    if await get_event_by_id(session, event_id) is None:
        raise EventNotFoundError

    try:
        saved_event = await unsave_event_for_user(
            session, user_id=current_user.id, event_id=event_id
        )
        await session.commit()
        return saved_event
    except SQLAlchemyError as exc:
        await session.rollback()
        raise EventActionFailedError(str(exc)) from exc
