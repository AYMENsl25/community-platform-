from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_authenticated_user
from app.db.session import get_db_session
from app.modules.events.schemas import (
    EventCapacity,
    EventCard,
    EventCreate,
    EventDeletionState,
    EventDetail,
    EventRegistrationAttendee,
    EventRegistrationState,
    EventUpdate,
    SavedEventState,
)
from app.modules.events.service import (
    EventActionFailedError,
    EventForbiddenError,
    EventNotFoundError,
    EventRegistrationNotFoundError,
    cancel_registration_action,
    create_event_action,
    delete_event_action,
    get_event_capacity,
    get_event_detail,
    list_event_attendees_action,
    list_events,
    register_for_event_action,
    save_event_action,
    unsave_event_action,
    update_event_action,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventCard])
async def list_event_cards(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    city: str | None = None,
    event_type: str | None = None,
    q: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[EventCard]:
    return await list_events(
        session,
        limit=limit,
        offset=offset,
        city=city,
        event_type=event_type,
        q=q,
    )


@router.post("", response_model=EventDetail, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> EventDetail:
    try:
        return await create_event_action(
            session, payload=payload, current_user=current_user
        )
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club not found"
        ) from exc
    except EventForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create events for this club.",
        ) from exc
    except EventActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Event creation failed"
        ) from exc


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: str, session: AsyncSession = Depends(get_db_session)
) -> EventDetail:
    event = await get_event_detail(session, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return event


@router.patch("/{event_id}", response_model=EventDetail)
async def update_event(
    event_id: str,
    payload: EventUpdate,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> EventDetail:
    try:
        return await update_event_action(
            session, event_id=event_id, payload=payload, current_user=current_user
        )
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        ) from exc
    except EventForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this event.",
        ) from exc
    except EventActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Event update failed"
        ) from exc


@router.delete("/{event_id}", response_model=EventDeletionState)
async def delete_event(
    event_id: str,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> EventDeletionState:
    try:
        return await delete_event_action(
            session, event_id=event_id, current_user=current_user
        )
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        ) from exc
    except EventForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this event.",
        ) from exc
    except EventActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Event deletion failed"
        ) from exc


@router.get("/{event_id}/registrations", response_model=list[EventRegistrationAttendee])
async def list_event_registrations(
    event_id: str,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> list[EventRegistrationAttendee]:
    try:
        return await list_event_attendees_action(
            session,
            event_id=event_id,
            current_user=current_user,
        )
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        ) from exc
    except EventForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to see event registrations.",
        ) from exc


@router.get("/{event_id}/capacity", response_model=EventCapacity)
async def get_capacity(
    event_id: str, session: AsyncSession = Depends(get_db_session)
) -> EventCapacity:
    capacity = await get_event_capacity(session, event_id)
    if capacity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return capacity


@router.post("/{event_id}/register", response_model=EventRegistrationState)
async def register_for_event(
    event_id: str,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    session: AsyncSession = Depends(get_db_session),
) -> EventRegistrationState:
    try:
        return await register_for_event_action(
            session,
            event_id=event_id,
            current_user=current_user,
            idempotency_key=idempotency_key,
        )
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        ) from exc
    except EventActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Event registration failed"
        ) from exc


@router.post("/{event_id}/cancel-registration", response_model=EventRegistrationState)
async def cancel_event_registration(
    event_id: str,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> EventRegistrationState:
    try:
        return await cancel_registration_action(
            session, event_id=event_id, current_user=current_user
        )
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        ) from exc
    except EventRegistrationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event registration not found"
        ) from exc
    except EventActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event registration cancellation failed",
        ) from exc


@router.post("/{event_id}/save", response_model=SavedEventState)
async def save_event(
    event_id: str,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> SavedEventState:
    try:
        return await save_event_action(
            session, event_id=event_id, current_user=current_user
        )
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        ) from exc
    except EventActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Event save failed"
        ) from exc


@router.delete("/{event_id}/save", response_model=SavedEventState)
async def unsave_event(
    event_id: str,
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    session: AsyncSession = Depends(get_db_session),
) -> SavedEventState:
    try:
        return await unsave_event_action(
            session, event_id=event_id, current_user=current_user
        )
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        ) from exc
    except EventActionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Event unsave failed"
        ) from exc
