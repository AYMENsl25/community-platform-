from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class CountryResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    code: str
    name_key: str
    default_locale: Literal["en", "tr", "fr", "ar"]
    default_currency: str


class CityResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    country_code: str
    slug: str
    name_key: str
    time_zone: str
    beta_enabled: bool


class CategoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    slug: str
    name_key: str
    icon_key: str
    sort_order: int


class RegionPolicyResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    country_code: str
    default_locale: Literal["en", "tr", "fr", "ar"]
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
