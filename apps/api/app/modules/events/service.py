from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.events.repository import get_event_by_id, get_event_capacity_by_id, list_public_events
from app.modules.events.schemas import EventCapacity, EventCard, EventDetail


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


async def get_event_capacity(session: AsyncSession, event_id: str) -> EventCapacity | None:
    return await get_event_capacity_by_id(session, event_id)
