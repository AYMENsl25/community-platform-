from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class EventAudienceResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    id: UUID
    title: str
    description: str
    country_code: str
    city_slug: str
    category_slug: str
    start_at: datetime
    end_at: datetime
    time_zone: str
    ownership_type: Literal["club", "independent"]
    cancellation_cutoff_minutes: int = Field(ge=0)
    price_type: Literal["free", "cash"]
    district: str | None
    public_meeting_area: str | None
    exact_address: str | None
    latitude: float | None
    longitude: float | None
    capacity: int | None
    available_places: int | None
    cover_media_id: UUID | None
    club_slug: str | None
    club_name: str | None
    organizer_display_name: str | None
    is_saved: bool
    registration_state: str | None


class PrivateLinkCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expires_in_days: int = Field(default=30, ge=1, le=365)


class PrivateLinkIssuedResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: UUID
    copy_value: str
    expires_at: datetime


class PrivateLinkResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    private_link: SecretStr | None = Field(
        default=None,
        description="Private-link value from the explicit copy field or URL fragment.",
    )


__all__ = [
    "EventAudienceResponse",
    "PrivateLinkCreateRequest",
    "PrivateLinkIssuedResponse",
    "PrivateLinkResolveRequest",
]
