from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

RegistrationState = Literal[
    "confirmed",
    "cash_pending",
    "waitlisted",
    "cancelled",
    "expired",
]


@dataclass(frozen=True, slots=True)
class EventAudienceProjection:
    id: UUID
    title: str
    description: str
    country_code: str
    city_slug: str
    category_slug: str
    start_at: datetime
    end_at: datetime
    time_zone: str
    price_type: Literal["free", "cash"]
    district: str | None
    public_meeting_area: str | None
    exact_address: str | None
    latitude: float | None
    longitude: float | None
    capacity: int | None
    available_places: int | None
    cover_storage_key: str | None
    club_slug: str | None
    club_name: str | None
    organizer_display_name: str | None
    is_saved: bool
    registration_state: RegistrationState | None


@dataclass(frozen=True, slots=True)
class ManagerVenueProjection:
    exact_address: str | None
    latitude: float | None
    longitude: float | None


@dataclass(frozen=True, slots=True)
class PrivateLinkRecord:
    id: UUID
    event_id: UUID
    expires_at: datetime
    revoked_at: datetime | None


__all__ = [
    "EventAudienceProjection",
    "ManagerVenueProjection",
    "PrivateLinkRecord",
    "RegistrationState",
]
