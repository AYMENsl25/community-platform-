from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID

PriceType = Literal["free", "cash"]
DiscoveryKind = Literal["event", "club"]


def _search(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(unicodedata.normalize("NFKC", value).casefold().split())
    return normalized or None


def _slug(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


@dataclass(frozen=True, slots=True)
class DiscoveryFilters:
    country: str | None = None
    city: str | None = None
    category: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    price: PriceType | None = None
    search: str | None = None
    sort: Literal["featured"] = "featured"

    def __post_init__(self) -> None:
        country = self.country.strip().upper() if self.country is not None else None
        if country is not None and re.fullmatch(r"[A-Z]{2}", country) is None:
            raise ValueError("country must be an ISO alpha-2 code")
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_to < self.date_from
        ):
            raise ValueError("date_to must not precede date_from")
        object.__setattr__(self, "country", country)
        object.__setattr__(self, "city", _slug(self.city))
        object.__setattr__(self, "category", _slug(self.category))
        object.__setattr__(self, "search", _search(self.search))

    def fingerprint_values(self) -> dict[str, str | None]:
        return {
            "category": self.category,
            "city": self.city,
            "country": self.country,
            "date_from": self.date_from.isoformat() if self.date_from else None,
            "date_to": self.date_to.isoformat() if self.date_to else None,
            "price": self.price,
            "search": self.search,
            "sort": self.sort,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryPosition:
    featured_score: int
    start_at: datetime
    id: UUID


@dataclass(frozen=True, slots=True)
class ClubPosition:
    name_key: str
    id: UUID


@dataclass(frozen=True, slots=True)
class SearchPosition:
    title_key: str
    kind: DiscoveryKind
    id: UUID


@dataclass(frozen=True, slots=True)
class SearchResult:
    kind: DiscoveryKind
    id: UUID
    slug: str | None
    title: str
    description: str
    country_code: str
    city_slug: str
    category_slug: str
    start_at: datetime | None
    title_key: str


@dataclass(frozen=True, slots=True)
class EventCard:
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
    price_type: PriceType
    district: str | None
    public_meeting_area: str | None
    capacity: int | None
    available_places: int | None
    cover_media_id: UUID | None
    club_slug: str | None
    club_name: str | None
    organizer_display_name: str | None
    is_saved: bool
    registration_state: str | None
    featured_score: int = 0


@dataclass(frozen=True, slots=True)
class ClubCard:
    id: UUID
    slug: str
    name: str
    name_key: str
    description: str
    country_code: str
    city_slug: str
    category_slug: str
    cover_media_id: UUID | None
    member_count: int
