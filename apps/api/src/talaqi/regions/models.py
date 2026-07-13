from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Locale = Literal["en", "tr", "fr", "ar"]


@dataclass(frozen=True, slots=True)
class DeadlineObligation:
    kind: Literal["cash", "cancellation"]
    issued_at: datetime
    deadline: datetime


@dataclass(frozen=True, slots=True)
class Country:
    code: str
    name_key: str
    default_locale: Locale
    default_currency: str


@dataclass(frozen=True, slots=True)
class City:
    country_code: str
    slug: str
    name_key: str
    time_zone: str
    beta_enabled: bool


@dataclass(frozen=True, slots=True)
class Category:
    slug: str
    name_key: str
    icon_key: str
    sort_order: int


@dataclass(frozen=True, slots=True)
class RegionPolicy:
    country_code: str
    default_locale: Locale
    default_currency: str
    allowed_registration_methods: tuple[str, ...]
    cash_default_minutes: int
    cash_bounds: tuple[int, int]
    cancellation_default_minutes: int
    cancellation_bounds: tuple[int, int]
    club_limit: int
    independent_event_limit: int
    exact_venue_public_by_default: bool
    revision: int
