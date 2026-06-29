import re

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.modules.events.policies import can_manage_club
from app.modules.events.repository import (
    cancel_user_event_registration,
    get_club_management_context,
    get_event_by_id,
    get_event_capacity_by_id,
    get_event_management_context,
    get_user_event_registration,
    insert_event,
    list_public_events,
    register_user_for_event,
    save_event_for_user,
    soft_delete_event_by_id,
    unsave_event_for_user,
    update_event_by_id,
)
from app.modules.events.schemas import (
    EventCapacity,
    EventCard,
    EventCreate,
    EventDeletionState,
    EventDetail,
    EventRegistrationState,
    EventUpdate,
    SavedEventState,
)


class EventNotFoundError(Exception):
    pass


class EventRegistrationNotFoundError(Exception):
    pass


class EventForbiddenError(Exception):
    pass


class EventActionFailedError(Exception):
    pass


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "event"


def can_manage_event_from_context(
    current_user: CurrentUser,
    context: dict[str, str | None],
) -> bool:
    return can_manage_club(
        current_user,
        owner_id=str(context["owner_id"]),
        member_role=context.get("member_role"),
        member_status=context.get("member_status"),
    )


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


async def create_event_action(
    session: AsyncSession,
    *,
    payload: EventCreate,
    current_user: CurrentUser,
) -> EventDetail:
    context = await get_club_management_context(
        session, club_id=payload.club_id, user_id=current_user.id
    )
    if context is None:
        raise EventNotFoundError
    if not can_manage_event_from_context(current_user, context):
        raise EventForbiddenError

    slug = payload.slug or slugify(payload.title)
    try:
        event_id = await insert_event(
            session,
            payload=payload,
            created_by=current_user.id,
            slug=slug,
        )
        event = await get_event_by_id(session, event_id)
        if event is None:
            raise EventNotFoundError
        await session.commit()
        return event
    except EventNotFoundError:
        await session.rollback()
        raise
    except SQLAlchemyError as exc:
        await session.rollback()
        raise EventActionFailedError(str(exc)) from exc


async def update_event_action(
    session: AsyncSession,
    *,
    event_id: str,
    payload: EventUpdate,
    current_user: CurrentUser,
) -> EventDetail:
    context = await get_event_management_context(
        session, event_id=event_id, user_id=current_user.id
    )
    if context is None:
        raise EventNotFoundError
    if not can_manage_event_from_context(current_user, context):
        raise EventForbiddenError

    try:
        await update_event_by_id(session, event_id=event_id, payload=payload)
        event = await get_event_by_id(session, event_id)
        if event is None:
            raise EventNotFoundError
        await session.commit()
        return event
    except EventNotFoundError:
        await session.rollback()
        raise
    except SQLAlchemyError as exc:
        await session.rollback()
        raise EventActionFailedError(str(exc)) from exc


async def delete_event_action(
    session: AsyncSession,
    *,
    event_id: str,
    current_user: CurrentUser,
) -> EventDeletionState:
    context = await get_event_management_context(
        session, event_id=event_id, user_id=current_user.id
    )
    if context is None:
        raise EventNotFoundError
    if not can_manage_event_from_context(current_user, context):
        raise EventForbiddenError

    try:
        await soft_delete_event_by_id(session, event_id=event_id)
        await session.commit()
        return EventDeletionState(event_id=event_id, deleted=True)
    except SQLAlchemyError as exc:
        await session.rollback()
        raise EventActionFailedError(str(exc)) from exc


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
