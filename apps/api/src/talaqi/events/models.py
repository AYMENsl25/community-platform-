from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from talaqi.regions.models import RegionPolicy

EventOwnershipType = Literal["club", "independent"]
EventVisibility = Literal["public", "private_link"]
EventStatus = Literal["draft", "published", "cancelled", "completed", "suspended"]
RegistrationMethod = Literal["free", "cash_organizer_confirmed"]


class EventValidationError(ValueError):
    def __init__(self, code: str = "invalid_event") -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class NewEvent:
    ownership_type: EventOwnershipType
    title: str
    club_id: UUID | None = None
    description: str = ""
    category_slug: str | None = None
    country_code: str | None = None
    city_slug: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    time_zone: str | None = None
    capacity: int | None = None
    visibility: EventVisibility = "public"
    registration_method: RegistrationMethod | None = None
    cash_expiry_minutes: int | None = None
    cancellation_cutoff_minutes: int | None = None
    district: str | None = None
    public_meeting_area: str | None = None
    exact_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    exact_venue_is_public: bool = False
    cover_media_id: UUID | None = None
    publish: bool = False


@dataclass(frozen=True, slots=True)
class EventPatch:
    revision: int
    changed_fields: frozenset[str]
    title: str | None = None
    description: str | None = None
    category_slug: str | None = None
    country_code: str | None = None
    city_slug: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    time_zone: str | None = None
    capacity: int | None = None
    visibility: EventVisibility | None = None
    registration_method: RegistrationMethod | None = None
    cash_expiry_minutes: int | None = None
    cancellation_cutoff_minutes: int | None = None
    district: str | None = None
    public_meeting_area: str | None = None
    exact_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    exact_venue_is_public: bool | None = None
    cover_media_id: UUID | None = None
    publish: bool | None = None


@dataclass(frozen=True, slots=True)
class EventReferences:
    category_id: UUID | None
    country_id: UUID | None
    city_id: UUID | None


@dataclass(frozen=True, slots=True)
class Event:
    id: UUID
    ownership_type: EventOwnershipType
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
    visibility: EventVisibility
    status: EventStatus
    registration_method: RegistrationMethod | None
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


def _invalid(code: str = "invalid_event") -> EventValidationError:
    return EventValidationError(code)


def _required_text(value: str, *, minimum: int, maximum: int) -> str:
    normalized = value.strip()
    if not minimum <= len(normalized) <= maximum:
        raise _invalid()
    return normalized


def _optional_text(value: str | None, *, maximum: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise _invalid()
    return normalized


def _slug(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    slug_alphabet = "abcdefghijklmnopqrstuvwxyz0123456789-"  # pragma: allowlist secret
    if (
        not 2 <= len(normalized) <= 80
        or not normalized[0].isalnum()
        or not normalized[-1].isalnum()
        or any(character not in slug_alphabet for character in normalized)
        or "--" in normalized
    ):
        raise _invalid()
    return normalized


def _country(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise _invalid()
    return normalized


def _instant(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise _invalid()
    return value.astimezone(UTC)


def _time_zone(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    try:
        zone = ZoneInfo(normalized)
    except (ValueError, ZoneInfoNotFoundError):
        raise _invalid() from None
    return zone.key


def normalize_new_event(value: NewEvent) -> NewEvent:
    if value.ownership_type == "club":
        if value.club_id is None:
            raise _invalid()
    elif value.ownership_type == "independent":
        if value.club_id is not None:
            raise _invalid()
    else:
        raise _invalid()
    if value.visibility not in ("public", "private_link"):
        raise _invalid()
    if value.registration_method not in (None, "free", "cash_organizer_confirmed"):
        raise _invalid()

    start_at = _instant(value.start_at)
    end_at = _instant(value.end_at)
    if start_at is not None and end_at is not None and end_at <= start_at:
        raise _invalid()
    if value.capacity is not None and (isinstance(value.capacity, bool) or value.capacity <= 0):
        raise _invalid()
    if (value.latitude is None) != (value.longitude is None):
        raise _invalid()
    if (
        value.latitude is not None
        and value.longitude is not None
        and (
            not math.isfinite(value.latitude)
            or not math.isfinite(value.longitude)
            or not -90 <= value.latitude <= 90
            or not -180 <= value.longitude <= 180
        )
    ):
        raise _invalid()
    country_code = _country(value.country_code)
    city_slug = _slug(value.city_slug)
    if city_slug is not None and country_code is None:
        raise _invalid()
    if value.registration_method == "free" and value.cash_expiry_minutes is not None:
        raise _invalid()
    for deadline in (value.cash_expiry_minutes, value.cancellation_cutoff_minutes):
        if deadline is not None and (isinstance(deadline, bool) or deadline < 0):
            raise _invalid()

    description = value.description.strip()
    if len(description) > 20_000:
        raise _invalid()
    return NewEvent(
        ownership_type=value.ownership_type,
        club_id=value.club_id,
        title=_required_text(value.title, minimum=2, maximum=160),
        description=description,
        category_slug=_slug(value.category_slug),
        country_code=country_code,
        city_slug=city_slug,
        start_at=start_at,
        end_at=end_at,
        time_zone=_time_zone(value.time_zone),
        capacity=value.capacity,
        visibility=value.visibility,
        registration_method=value.registration_method,
        cash_expiry_minutes=value.cash_expiry_minutes,
        cancellation_cutoff_minutes=value.cancellation_cutoff_minutes,
        district=_optional_text(value.district, maximum=120),
        public_meeting_area=_optional_text(value.public_meeting_area, maximum=300),
        exact_address=_optional_text(value.exact_address, maximum=500),
        latitude=value.latitude,
        longitude=value.longitude,
        exact_venue_is_public=value.exact_venue_is_public,
        cover_media_id=value.cover_media_id,
        publish=value.publish,
    )


def apply_event_patch(event: Event, patch: EventPatch) -> Event:
    fields = patch.changed_fields
    if patch.revision < 1 or "revision" in fields:
        raise _invalid()
    for required in ("title", "visibility", "exact_venue_is_public"):
        if required in fields and getattr(patch, required) is None:
            raise _invalid()
    candidate = normalize_new_event(
        NewEvent(
            ownership_type=event.ownership_type,
            club_id=event.club_id,
            title=patch.title if "title" in fields and patch.title is not None else event.title,
            description=(
                patch.description
                if "description" in fields and patch.description is not None
                else ""
                if "description" in fields
                else event.description
            ),
            category_slug=(
                patch.category_slug if "category_slug" in fields else event.category_slug
            ),
            country_code=(patch.country_code if "country_code" in fields else event.country_code),
            city_slug=patch.city_slug if "city_slug" in fields else event.city_slug,
            start_at=patch.start_at if "start_at" in fields else event.start_at,
            end_at=patch.end_at if "end_at" in fields else event.end_at,
            time_zone=patch.time_zone if "time_zone" in fields else event.time_zone,
            capacity=patch.capacity if "capacity" in fields else event.capacity,
            visibility=(
                patch.visibility
                if "visibility" in fields and patch.visibility is not None
                else event.visibility
            ),
            registration_method=(
                patch.registration_method
                if "registration_method" in fields
                else event.registration_method
            ),
            cash_expiry_minutes=(
                patch.cash_expiry_minutes
                if "cash_expiry_minutes" in fields
                else event.cash_expiry_minutes
            ),
            cancellation_cutoff_minutes=(
                patch.cancellation_cutoff_minutes
                if "cancellation_cutoff_minutes" in fields
                else event.cancellation_cutoff_minutes
            ),
            district=patch.district if "district" in fields else event.district,
            public_meeting_area=(
                patch.public_meeting_area
                if "public_meeting_area" in fields
                else event.public_meeting_area
            ),
            exact_address=(
                patch.exact_address if "exact_address" in fields else event.exact_address
            ),
            latitude=patch.latitude if "latitude" in fields else event.latitude,
            longitude=patch.longitude if "longitude" in fields else event.longitude,
            exact_venue_is_public=(
                patch.exact_venue_is_public
                if "exact_venue_is_public" in fields and patch.exact_venue_is_public is not None
                else event.exact_venue_is_public
            ),
            cover_media_id=(
                patch.cover_media_id if "cover_media_id" in fields else event.cover_media_id
            ),
            publish=bool(patch.publish) if "publish" in fields else False,
        )
    )
    return replace(
        event,
        title=candidate.title,
        description=candidate.description,
        category_slug=candidate.category_slug,
        country_code=candidate.country_code,
        city_slug=candidate.city_slug,
        start_at=candidate.start_at,
        end_at=candidate.end_at,
        time_zone=candidate.time_zone,
        capacity=candidate.capacity,
        visibility=candidate.visibility,
        registration_method=candidate.registration_method,
        cash_expiry_minutes=candidate.cash_expiry_minutes,
        cancellation_cutoff_minutes=candidate.cancellation_cutoff_minutes,
        district=candidate.district,
        public_meeting_area=candidate.public_meeting_area,
        exact_address=candidate.exact_address,
        latitude=candidate.latitude,
        longitude=candidate.longitude,
        exact_venue_is_public=candidate.exact_venue_is_public,
        cover_media_id=candidate.cover_media_id,
    )


def validate_published_event(event: Event, policy: RegionPolicy) -> None:
    required = (
        event.description.strip(),
        event.category_slug,
        event.country_code,
        event.city_slug,
        event.start_at,
        event.end_at,
        event.time_zone,
        event.registration_method,
        event.cancellation_cutoff_minutes,
    )
    if any(value is None or value == "" for value in required):
        raise _invalid("event_not_publishable")
    if event.start_at is None or event.end_at is None or event.end_at <= event.start_at:
        raise _invalid("event_not_publishable")
    if event.country_code != policy.country_code:
        raise _invalid("event_not_publishable")
    if event.registration_method not in policy.allowed_registration_methods:
        raise _invalid("registration_method_not_allowed")
    if event.registration_method == "cash_organizer_confirmed":
        if event.cash_expiry_minutes is None or not (
            policy.cash_bounds[0] <= event.cash_expiry_minutes <= policy.cash_bounds[1]
        ):
            raise _invalid("invalid_event_deadline")
    elif event.cash_expiry_minutes is not None:
        raise _invalid("invalid_event_deadline")
    if event.cancellation_cutoff_minutes is None or not (
        policy.cancellation_bounds[0]
        <= event.cancellation_cutoff_minutes
        <= policy.cancellation_bounds[1]
    ):
        raise _invalid("invalid_event_deadline")
    if event.capacity is not None and event.capacity <= 0:
        raise _invalid("event_not_publishable")


def validate_publishable(event: Event, policy: RegionPolicy, *, now: datetime) -> None:
    current = _instant(now)
    if current is None:
        raise _invalid()
    validate_published_event(event, policy)
    if event.start_at is None or event.start_at <= current:
        raise _invalid("event_not_publishable")


__all__ = [
    "Event",
    "EventOwnershipType",
    "EventPatch",
    "EventReferences",
    "EventStatus",
    "EventValidationError",
    "EventVisibility",
    "NewEvent",
    "RegistrationMethod",
    "normalize_new_event",
    "validate_publishable",
    "validate_published_event",
]
