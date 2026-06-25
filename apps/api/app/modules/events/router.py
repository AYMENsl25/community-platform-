from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.events.schemas import EventCapacity, EventCard, EventDetail
from app.modules.events.service import get_event_capacity, get_event_detail, list_events

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


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(event_id: str, session: AsyncSession = Depends(get_db_session)) -> EventDetail:
    event = await get_event_detail(session, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.get("/{event_id}/capacity", response_model=EventCapacity)
async def get_capacity(event_id: str, session: AsyncSession = Depends(get_db_session)) -> EventCapacity:
    capacity = await get_event_capacity(session, event_id)
    if capacity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return capacity
