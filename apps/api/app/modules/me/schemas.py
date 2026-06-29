from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class MyClubSummary(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    logo_url: str | None = None
    cover_image_url: str | None = None
    city: str | None = None
    country: str | None = None
    member_count: int
    category_name: str | None = None
    visibility: str
    status: str
    member_role: str
    member_status: str


class MyEventSummary(BaseModel):
    id: str
    club_id: str
    club_name: str
    title: str
    slug: str
    event_type: str
    starts_at: datetime
    ends_at: datetime | None = None
    city: str | None = None
    status: str
    capacity: int | None = None
    registered_count: int
    waitlist_count: int
    price_amount: Decimal
    currency: str
    cover_image_url: str | None = None


class MyRegistrationSummary(BaseModel):
    event_id: str
    club_id: str
    club_name: str
    title: str
    slug: str
    event_type: str
    starts_at: datetime
    registration_status: str
    registered_at: datetime
    city: str | None = None
    cover_image_url: str | None = None


class MySavedEventSummary(BaseModel):
    event_id: str
    club_id: str
    club_name: str
    title: str
    slug: str
    event_type: str
    starts_at: datetime
    city: str | None = None
    saved_at: datetime
    cover_image_url: str | None = None
