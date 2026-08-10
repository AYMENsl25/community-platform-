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
    ownership_type: Literal["club", "independent"]
    cancellation_cutoff_minutes: int
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
    registration_id: UUID | None
    registration_method: Literal["free", "cash_organizer_confirmed"] | None
    registration_state: RegistrationState | None
    registration_cash_expires_at: datetime | None
    registration_confirmed_at: datetime | None


@dataclass(frozen=True, slots=True)
class ManagerVenueProjection:
    exact_address: str | None
    latitude: float | None
    longitude: float | None


@dataclass(frozen=True, slots=True)
class EventRegistrationTerms:
    id: UUID
    start_at: datetime
    capacity: int | None
    method: Literal["free", "cash_organizer_confirmed"]
    cash_expiry_minutes: int | None


@dataclass(frozen=True, slots=True)
class EventCancellationTerms:
    id: UUID
    start_at: datetime
    capacity: int | None
    method: Literal["free", "cash_organizer_confirmed"]
    cash_expiry_minutes: int | None
    cancellation_cutoff_minutes: int


@dataclass(frozen=True, slots=True)
class PrivateLinkRecord:
    id: UUID
    event_id: UUID
    expires_at: datetime
    revoked_at: datetime | None


__all__ = [
    "EventAudienceProjection",
    "EventCancellationTerms",
    "EventRegistrationTerms",
    "ManagerVenueProjection",
    "PrivateLinkRecord",
    "RegistrationState",
]
