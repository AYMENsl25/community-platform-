from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


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


class EventRegistrationState(BaseModel):
    id: str
    event_id: str
    user_id: str
    status: str
    waitlist_position: int | None = None
    note: str | None = None
    registered_at: datetime
    confirmed_at: datetime | None = None
    cancelled_at: datetime | None = None


class SavedEventState(BaseModel):
    user_id: str
    event_id: str
    saved: bool
    created_at: datetime | None = None


class EventCreate(BaseModel):
    club_id: str
    title: str = Field(min_length=3, max_length=160)
    slug: str | None = Field(default=None, min_length=3, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    event_type: str = Field(default="community", min_length=2, max_length=80)
    starts_at: datetime
    ends_at: datetime | None = None
    timezone: str = Field(default="Asia/Riyadh", min_length=1, max_length=80)
    location_name: str | None = Field(default=None, max_length=160)
    address: str | None = Field(default=None, max_length=240)
    city: str | None = Field(default="Riyadh", max_length=120)
    country: str | None = Field(default="Saudi Arabia", max_length=120)
    lat: Decimal | None = None
    lng: Decimal | None = None
    capacity: int | None = Field(default=None, gt=0)
    price_amount: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="SAR", min_length=3, max_length=3)
    status: str = Field(default="draft", pattern="^(draft|published)$")
    requires_approval: bool = False
    cover_image_url: str | None = Field(default=None, max_length=500)
