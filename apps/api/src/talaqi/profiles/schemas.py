from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProfileReplacementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=30)
    display_name: str = Field(min_length=1, max_length=80)
    country_code: str = Field(min_length=2, max_length=2)
    city_slug: str = Field(min_length=1, max_length=80)
    locale: Literal["en", "tr", "fr", "ar"]
    time_zone: str = Field(min_length=3, max_length=64)
    preferred_currency: str = Field(min_length=3, max_length=3)
    notify_event_email: bool
    notify_community_email: bool
    organizer_rules_version: str = Field(min_length=1, max_length=64)
    community_rules_version: str = Field(min_length=1, max_length=64)


class ProfileResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    username: str | None
    display_name: str | None
    country_code: str | None
    city_slug: str | None
    locale: Literal["en", "tr", "fr", "ar"] | None
    time_zone: str | None
    preferred_currency: str | None
    notify_security_email: Literal[True]
    notify_event_email: bool
    notify_community_email: bool
    organizer_rules_version: str | None
    community_rules_version: str | None
    profile_completed_at: datetime | None
    avatar: None = None


class AccountDeletionResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    requested_at: datetime
    anonymize_after: datetime


class Capabilities(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    create_club: bool
    create_independent_event: bool
    save_event: bool
    register_event: bool
    access_admin: bool
    blockers: tuple[str, ...]
