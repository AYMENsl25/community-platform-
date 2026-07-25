from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

SocialLinks = Annotated[dict[str, AnyHttpUrl], Field(max_length=12)]


class ClubCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=20_000)
    category_slug: str | None = Field(default=None, min_length=1, max_length=80)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    city_slug: str | None = Field(default=None, min_length=1, max_length=80)
    membership_policy: Literal["open", "approval_required"] = "open"
    social_links: SocialLinks = Field(default_factory=dict)
    logo_media_id: UUID | None = None
    cover_media_id: UUID | None = None


class ClubPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: int = Field(ge=1)
    slug: str | None = Field(default=None, min_length=2, max_length=80)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=20_000)
    category_slug: str | None = Field(default=None, min_length=1, max_length=80)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    city_slug: str | None = Field(default=None, min_length=1, max_length=80)
    membership_policy: Literal["open", "approval_required"] | None = None
    social_links: SocialLinks | None = None
    logo_media_id: UUID | None = None
    cover_media_id: UUID | None = None

    @model_validator(mode="after")
    def require_change(self) -> ClubPatchRequest:
        if self.model_fields_set == {"revision"}:
            raise ValueError("at least one club field must be supplied")
        return self


class ClubResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    slug: str
    name: str
    description: str | None
    category_slug: str | None
    country_code: str | None
    city_slug: str | None
    membership_policy: Literal["open", "approval_required"]
    social_links: dict[str, str]
    logo_media_id: UUID | None
    cover_media_id: UUID | None
    revision: int
    status: Literal["draft", "published", "unpublished", "suspended", "closed"]
    missing_fields: tuple[str, ...]
    published_at: datetime | None
    suspended_at: datetime | None
    suspension_reason: str | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
