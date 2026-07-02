from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ClubCard(BaseModel):
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


class ClubDetail(ClubCard):
    owner_id: str
    category_id: str | None = None
    visibility: str
    status: str
    owner_name: str
    owner_avatar_url: str | None = None


class ClubMemberPreview(BaseModel):
    user_id: str
    display_name: str
    avatar_url: str | None = None
    role: str
    joined_at: datetime


class ClubEventSummary(BaseModel):
    id: str
    title: str
    slug: str
    event_type: str
    starts_at: datetime
    ends_at: datetime | None = None
    city: str | None = None
    registered_count: int
    waitlist_count: int
    price_amount: Decimal
    currency: str
    cover_image_url: str | None = None


class ClubViewerState(BaseModel):
    club_id: str
    is_member: bool
    member_role: str | None = None
    member_status: str | None = None
    joined_at: datetime | None = None


class ClubMembershipState(BaseModel):
    id: str
    club_id: str
    user_id: str
    role: str
    status: str
    joined_at: datetime
    left_at: datetime | None = None


class ClubCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    slug: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    category_id: str | None = None
    logo_url: str | None = Field(default=None, max_length=500)
    cover_image_url: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default="Riyadh", max_length=120)
    country: str | None = Field(default="Saudi Arabia", max_length=120)
    visibility: str = Field(default="public", pattern="^(public|private)$")
    status: str = Field(default="published", pattern="^(draft|published)$")


class ClubUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    slug: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    category_id: str | None = None
    logo_url: str | None = Field(default=None, max_length=500)
    cover_image_url: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    visibility: str | None = Field(default=None, pattern="^(public|private)$")
    status: str | None = Field(default=None, pattern="^(draft|published|archived)$")


class ClubDeletionState(BaseModel):
    club_id: str
    deleted: bool
