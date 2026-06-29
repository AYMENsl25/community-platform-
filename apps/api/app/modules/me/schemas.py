from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class MyProfile(BaseModel):
    id: str
    clerk_user_id: str
    email: str
    username: str | None = None
    display_name: str
    avatar_url: str | None = None
    bio: str | None = None
    city: str | None = None
    country: str | None = None
    platform_role: str
    is_onboarded: bool


class MyProfileUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=80)
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=1000)
    city: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    is_onboarded: bool | None = None


class MyPreferences(BaseModel):
    interest_categories: list[str]
    interest_tags: list[str]
    preferred_city: str | None = None
    max_distance_km: int | None = None
    notify_email: bool
    notify_push: bool


class MyPreferencesUpdate(BaseModel):
    interest_categories: list[str] | None = None
    interest_tags: list[str] | None = None
    preferred_city: str | None = Field(default=None, max_length=120)
    max_distance_km: int | None = Field(default=None, gt=0)
    notify_email: bool | None = None
    notify_push: bool | None = None


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


class MyNotificationSummary(BaseModel):
    id: str
    kind: str
    title: str
    body: str
    entity_type: str | None = None
    entity_id: str | None = None
    read_at: datetime | None = None
    created_at: datetime
    is_read: bool


class NotificationReadState(BaseModel):
    id: str
    read_at: datetime


class NotificationsReadAllState(BaseModel):
    updated_count: int
