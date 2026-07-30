from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from talaqi.events.models import (
    Event,
    EventValidationError,
    NewEvent,
    normalize_new_event,
    validate_publishable,
)
from talaqi.regions.models import RegionPolicy

NOW = datetime(2026, 8, 1, 12, tzinfo=UTC)
CLUB_ID = UUID("01900000-0000-7000-8000-000000000301")
OWNER_ID = UUID("01900000-0000-7000-8000-000000000302")


def policy() -> RegionPolicy:
    return RegionPolicy(
        country_code="TR",
        default_locale="tr",
        default_currency="TRY",
        allowed_registration_methods=("free", "cash_organizer_confirmed"),
        cash_default_minutes=1_440,
        cash_bounds=(120, 4_320),
        cancellation_default_minutes=1_440,
        cancellation_bounds=(0, 10_080),
        club_limit=1,
        independent_event_limit=3,
        exact_venue_public_by_default=False,
        revision=1,
    )


def complete_new_event(**changes: object) -> NewEvent:
    values: dict[str, object] = {
        "ownership_type": "club",
        "club_id": CLUB_ID,
        "title": "Talaqi Morning Run",
        "description": "A welcoming community run along the waterfront.",
        "category_slug": "sports",
        "country_code": "tr",
        "city_slug": "istanbul",
        "start_at": NOW + timedelta(days=7),
        "end_at": NOW + timedelta(days=7, hours=2),
        "time_zone": "Europe/Istanbul",
        "capacity": None,
        "visibility": "public",
        "registration_method": "free",
        "cash_expiry_minutes": None,
        "cancellation_cutoff_minutes": 1_440,
        "district": "Kadikoy",
        "public_meeting_area": "Waterfront entrance",
        "exact_address": "Example address",
        "latitude": 40.991,
        "longitude": 29.027,
        "exact_venue_is_public": False,
        "cover_media_id": None,
        "publish": True,
    }
    values.update(changes)
    return NewEvent(**values)  # type: ignore[arg-type]


def persisted_event(**changes: object) -> Event:
    normalized = normalize_new_event(complete_new_event())
    values: dict[str, object] = {
        "id": UUID("01900000-0000-7000-8000-000000000303"),
        "ownership_type": normalized.ownership_type,
        "club_id": normalized.club_id,
        "owner_user_id": None,
        "title": normalized.title,
        "description": normalized.description,
        "category_slug": normalized.category_slug,
        "country_code": normalized.country_code,
        "city_slug": normalized.city_slug,
        "start_at": normalized.start_at,
        "end_at": normalized.end_at,
        "time_zone": normalized.time_zone,
        "capacity": normalized.capacity,
        "visibility": normalized.visibility,
        "status": "draft",
        "registration_method": normalized.registration_method,
        "cash_expiry_minutes": normalized.cash_expiry_minutes,
        "cancellation_cutoff_minutes": normalized.cancellation_cutoff_minutes,
        "district": normalized.district,
        "public_meeting_area": normalized.public_meeting_area,
        "exact_address": normalized.exact_address,
        "latitude": normalized.latitude,
        "longitude": normalized.longitude,
        "exact_venue_is_public": normalized.exact_venue_is_public,
        "cover_media_id": normalized.cover_media_id,
        "revision": 1,
        "published_at": None,
        "cancelled_at": None,
        "completed_at": None,
        "suspended_at": None,
        "suspension_reason": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(changes)
    return Event(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [
        complete_new_event(ownership_type="club", club_id=None),
        complete_new_event(ownership_type="independent", club_id=CLUB_ID),
    ],
)
def test_ownership_shape_is_explicit_and_server_owned(value: NewEvent) -> None:
    with pytest.raises(EventValidationError, match="invalid_event"):
        normalize_new_event(value)


@pytest.mark.parametrize(
    "changes",
    [
        {"start_at": NOW + timedelta(hours=2), "end_at": NOW + timedelta(hours=1)},
        {"start_at": datetime(2026, 8, 2, 12), "end_at": NOW + timedelta(days=2)},
        {"time_zone": "Europe/Not-A-Zone"},
        {"capacity": 0},
        {"latitude": 41.0, "longitude": None},
        {"latitude": 91.0, "longitude": 1.0},
        {"country_code": None, "city_slug": "istanbul"},
        {"registration_method": "free", "cash_expiry_minutes": 120},
    ],
)
def test_drafts_reject_structurally_invalid_values(changes: dict[str, object]) -> None:
    with pytest.raises(EventValidationError, match="invalid_event"):
        normalize_new_event(complete_new_event(publish=False, **changes))


def test_normalization_retains_iana_zone_and_utc_instants() -> None:
    normalized = normalize_new_event(
        complete_new_event(
            title="  Talaqi Morning Run  ",
            country_code="tr",
            city_slug=" Istanbul ",
        )
    )
    assert normalized.title == "Talaqi Morning Run"
    assert normalized.country_code == "TR"
    assert normalized.city_slug == "istanbul"
    assert normalized.time_zone == "Europe/Istanbul"
    assert normalized.start_at is not None
    assert normalized.start_at.utcoffset() == timedelta(0)


def test_publishable_event_allows_unlimited_capacity() -> None:
    event = persisted_event(capacity=None)
    validate_publishable(event, policy(), now=NOW)


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"description": ""}, "event_not_publishable"),
        ({"start_at": NOW - timedelta(minutes=1)}, "event_not_publishable"),
        ({"registration_method": "card"}, "registration_method_not_allowed"),
        (
            {
                "registration_method": "cash_organizer_confirmed",
                "cash_expiry_minutes": 60,
            },
            "invalid_event_deadline",
        ),
        ({"cancellation_cutoff_minutes": 20_000}, "invalid_event_deadline"),
    ],
)
def test_publish_validation_enforces_policy(changes: dict[str, object], expected: str) -> None:
    event = replace(persisted_event(), **changes)
    with pytest.raises(EventValidationError, match=expected):
        validate_publishable(event, policy(), now=NOW)


def test_revision_and_lifecycle_shape_are_immutable_values() -> None:
    event = persisted_event()
    published = replace(event, status="published", revision=2, published_at=NOW)
    cancelled = replace(published, status="cancelled", revision=3, cancelled_at=NOW)
    assert event.status == "draft"
    assert published.revision == 2
    assert cancelled.status == "cancelled"
    assert cancelled.published_at == NOW
