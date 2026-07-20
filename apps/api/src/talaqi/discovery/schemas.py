from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventCardResponse(BaseModel):
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
    price_type: Literal["free", "cash"]
    district: str | None
    public_meeting_area: str | None
    capacity: int
    available_places: int
    cover_storage_key: str | None
    club_slug: str | None
    club_name: str | None
    organizer_display_name: str | None
    is_saved: bool
    registration_state: str | None


class EventPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[EventCardResponse]
    next_cursor: str | None


class ClubCardResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    id: UUID
    slug: str
    name: str
    description: str
    country_code: str
    city_slug: str
    category_slug: str
    cover_storage_key: str | None


class ClubPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[ClubCardResponse]
    next_cursor: str | None


class ClubDetailResponse(ClubCardResponse):
    events: list[EventCardResponse]


class SearchItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["event", "club"]
    id: UUID
    slug: str | None
    title: str
    description: str
    country_code: str
    city_slug: str
    category_slug: str
    start_at: datetime | None


class SearchPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[SearchItemResponse]
    next_cursor: str | None


class DiscoveryMetadataResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    countries: list[dict[str, str]]
    cities: list[dict[str, str]]
    categories: list[dict[str, str]]
    price_types: tuple[Literal["free"], Literal["cash"]] = ("free", "cash")
    sort: Literal["featured"] = "featured"


class DiscoveryQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country: str | None = Field(default=None, min_length=2, max_length=2)
    city: str | None = Field(default=None, min_length=1, max_length=80)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    search: str | None = Field(default=None, min_length=1, max_length=120)
