from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from talaqi.regions.models import Locale


@dataclass(frozen=True, slots=True)
class ProfileReplacement:
    username: str
    display_name: str
    country_code: str
    city_slug: str
    locale: Locale
    time_zone: str
    preferred_currency: str
    notify_event_email: bool
    notify_community_email: bool
    organizer_rules_version: str
    community_rules_version: str


@dataclass(frozen=True, slots=True)
class Profile:
    user_id: UUID
    username: str
    display_name: str
    country_code: str
    city_slug: str
    locale: Locale
    time_zone: str
    preferred_currency: str
    notify_security_email: bool
    notify_event_email: bool
    notify_community_email: bool
    organizer_rules_version: str | None
    community_rules_version: str | None
    profile_completed_at: datetime | None
    avatar: None = None

    @classmethod
    def from_replacement(
        cls, user_id: UUID, value: ProfileReplacement, completed_at: datetime
    ) -> Profile:
        return cls(
            user_id=user_id,
            username=value.username,
            display_name=value.display_name,
            country_code=value.country_code,
            city_slug=value.city_slug,
            locale=value.locale,
            time_zone=value.time_zone,
            preferred_currency=value.preferred_currency,
            notify_security_email=True,
            notify_event_email=value.notify_event_email,
            notify_community_email=value.notify_community_email,
            organizer_rules_version=value.organizer_rules_version,
            community_rules_version=value.community_rules_version,
            profile_completed_at=completed_at,
        )


@dataclass(frozen=True, slots=True)
class EligibilityState:
    profile: Profile | None
    terms_version: str
    privacy_version: str
    organizer_rules_version: str | None
    community_rules_version: str | None
    owned_club_count: int
    active_independent_event_count: int
    has_active_mfa: bool
