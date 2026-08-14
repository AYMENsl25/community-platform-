from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator


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


class RegionPolicyChangeRequest(BaseModel):
    """Safe, prospective regional controls; active records are never rewritten."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    revision: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=1_000)
    club_limit: int | None = Field(default=None, ge=0, le=100)
    independent_event_limit: int | None = Field(default=None, ge=0, le=100)
    exact_venue_public_by_default: StrictBool | None = None

    @model_validator(mode="after")
    def require_change(self) -> RegionPolicyChangeRequest:
        if (
            self.club_limit is None
            and self.independent_event_limit is None
            and self.exact_venue_public_by_default is None
        ):
            raise ValueError("at least one policy field is required")
        return self


class RegionPolicyPreviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    current: RegionPolicyResponse
    proposed: RegionPolicyResponse
    changed_fields: tuple[str, ...]
    impact: str = (
        "Changes affect future ownership and event drafts only; existing records remain unchanged."
    )


class RegionPolicyUpdateResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    policy: RegionPolicyResponse
    status: Literal["updated"] = "updated"
