from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class EventCard(BaseModel):
    id: str
    club_id: str
    club_name: str
    title: str
    slug: str
    description: str | None = None
    event_type: str
    starts_at: datetime
    ends_at: datetime | None = None
    city: str | None = None
    country: str | None = None
    location_name: str | None = None
    capacity: int | None = None
    registered_count: int
    waitlist_count: int
    price_amount: Decimal
    currency: str
    cover_image_url: str | None = None
    category_name: str | None = None


class EventDetail(EventCard):
    created_by: str
    timezone: str
    address: str | None = None
    lat: Decimal | None = None
    lng: Decimal | None = None
    status: str
    requires_approval: bool
    club_slug: str
    club_logo_url: str | None = None
    organizer_name: str
    organizer_avatar_url: str | None = None
    is_full: bool


class EventCapacity(BaseModel):
    event_id: str
    capacity: int | None = None
    registered_count: int
    waitlist_count: int
    spots_left: int | None = None
    is_full: bool
