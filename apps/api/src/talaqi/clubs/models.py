from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

ClubMembershipPolicy = Literal["open", "approval_required"]
ClubStatus = Literal["draft", "published", "unpublished", "suspended", "closed"]
ClubRole = Literal["owner", "admin", "member"]
ManagedClubRole = Literal["owner", "admin"]
WorkspaceCapability = Literal[
    "edit_profile",
    "manage_members",
    "change_member_roles",
    "transfer_ownership",
    "close_club",
    "preview_profile",
]


@dataclass(frozen=True, slots=True)
class NewClub:
    slug: str
    name: str
    description: str | None = None
    category_slug: str | None = None
    country_code: str | None = None
    city_slug: str | None = None
    membership_policy: ClubMembershipPolicy = "open"
    social_links: dict[str, str] | None = None
    logo_media_id: UUID | None = None
    cover_media_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ClubPatch:
    revision: int
    changed_fields: frozenset[str]
    slug: str | None = None
    name: str | None = None
    description: str | None = None
    category_slug: str | None = None
    country_code: str | None = None
    city_slug: str | None = None
    membership_policy: ClubMembershipPolicy | None = None
    social_links: dict[str, str] | None = None
    logo_media_id: UUID | None = None
    cover_media_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ClubReferences:
    category_id: UUID | None
    country_id: UUID | None
    city_id: UUID | None
    logo_media_id: UUID | None
    cover_media_id: UUID | None


@dataclass(frozen=True, slots=True)
class Club:
    id: UUID
    owner_user_id: UUID
    slug: str
    name: str
    description: str | None
    category_slug: str | None
    country_code: str | None
    city_slug: str | None
    membership_policy: ClubMembershipPolicy
    social_links: dict[str, str]
    logo_media_id: UUID | None
    cover_media_id: UUID | None
    revision: int
    status: ClubStatus
    published_at: datetime | None
    suspended_at: datetime | None
    suspension_reason: str | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ClubAccess:
    club_id: UUID
    user_id: UUID
    role: ClubRole


@dataclass(frozen=True, slots=True)
class ManagedClub:
    club: Club
    role: ManagedClubRole
    capabilities: tuple[WorkspaceCapability, ...]
