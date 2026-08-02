from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class EventCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ownership_type: Literal["club", "independent"]
    club_id: UUID | None = None
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=20_000)
    category_slug: str | None = Field(default=None, min_length=2, max_length=80)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    city_slug: str | None = Field(default=None, min_length=2, max_length=80)
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None
    time_zone: str | None = Field(default=None, min_length=3, max_length=64)
    capacity: int | None = Field(default=None, gt=0)
    visibility: Literal["public", "private_link"] = "public"
    registration_method: Literal["free", "cash_organizer_confirmed"] | None = None
    cash_expiry_minutes: int | None = Field(default=None, ge=0)
    cancellation_cutoff_minutes: int | None = Field(default=None, ge=0)
    district: str | None = Field(default=None, min_length=1, max_length=120)
    public_meeting_area: str | None = Field(default=None, min_length=1, max_length=300)
    exact_address: str | None = Field(default=None, min_length=1, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    exact_venue_is_public: bool = False
    cover_media_id: UUID | None = None
    publish: bool = False


class EventPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=20_000)
    category_slug: str | None = Field(default=None, min_length=2, max_length=80)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    city_slug: str | None = Field(default=None, min_length=2, max_length=80)
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None
    time_zone: str | None = Field(default=None, min_length=3, max_length=64)
    capacity: int | None = Field(default=None, gt=0)
    visibility: Literal["public", "private_link"] | None = None
    registration_method: Literal["free", "cash_organizer_confirmed"] | None = None
    cash_expiry_minutes: int | None = Field(default=None, ge=0)
    cancellation_cutoff_minutes: int | None = Field(default=None, ge=0)
    district: str | None = Field(default=None, min_length=1, max_length=120)
    public_meeting_area: str | None = Field(default=None, min_length=1, max_length=300)
    exact_address: str | None = Field(default=None, min_length=1, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    exact_venue_is_public: bool | None = None
    cover_media_id: UUID | None = None
    publish: bool | None = None


EventWorkspaceCapability = Literal[
    "edit",
    "duplicate",
    "cancel",
    "complete",
    "delete_draft",
    "preview",
]


class EventRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: int = Field(ge=1)


class ManagedEventResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    ownership_type: Literal["club", "independent"]
    club_id: UUID | None
    owner_user_id: UUID | None
    title: str
    description: str
    category_slug: str | None
    country_code: str | None
    city_slug: str | None
    start_at: datetime | None
    end_at: datetime | None
    time_zone: str | None
    capacity: int | None
    visibility: Literal["public", "private_link"]
    status: Literal["draft", "published", "cancelled", "completed", "suspended"]
    registration_method: Literal["free", "cash_organizer_confirmed"] | None
    cash_expiry_minutes: int | None
    cancellation_cutoff_minutes: int | None
    district: str | None
    public_meeting_area: str | None
    exact_address: str | None
    latitude: float | None
    longitude: float | None
    exact_venue_is_public: bool
    cover_media_id: UUID | None
    revision: int
    published_at: datetime | None
    cancelled_at: datetime | None
    completed_at: datetime | None
    suspended_at: datetime | None
    suspension_reason: str | None
    created_at: datetime
    updated_at: datetime
    capabilities: tuple[EventWorkspaceCapability, ...] = ()
    validation_blockers: tuple[str, ...] = ()


class ManagedEventPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[ManagedEventResponse]
