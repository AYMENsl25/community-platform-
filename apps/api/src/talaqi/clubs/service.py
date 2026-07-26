from __future__ import annotations

import re
from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlsplit
from uuid import UUID

from talaqi.audit import AuditService
from talaqi.clubs.models import (
    Club,
    ClubPatch,
    ClubRole,
    ClubStatus,
    ManagedClub,
    NewClub,
    WorkspaceCapability,
)
from talaqi.clubs.repository import ClubRepositoryProtocol
from talaqi.db.identifiers import validate_uuid7
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.profiles.schemas import Capabilities
from talaqi.security import can_edit_club

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SOCIAL_KEY = re.compile(r"^[a-z0-9_]{1,32}$")
_REQUIRED_FIELDS = ("description", "category_slug", "country_code", "city_slug")
_CREATE_BLOCKERS = (
    "account_unavailable",
    "email_verification_required",
    "profile_incomplete",
    "rules_acceptance_required",
    "region_unavailable",
    "club_limit_reached",
)


class ClubEligibility(Protocol):
    async def evaluate(self, principal: AuthPrincipal) -> Capabilities: ...


def _invalid_club() -> ApiError:
    return ApiError(code="invalid_club", message_key="errors.validation", status_code=422)


def _not_found() -> ApiError:
    return ApiError(code="not_found", message_key="errors.not_found", status_code=404)


def missing_fields(club: Club | NewClub) -> tuple[str, ...]:
    values = {
        "description": club.description,
        "category_slug": club.category_slug,
        "country_code": club.country_code,
        "city_slug": club.city_slug,
    }
    return tuple(field for field in _REQUIRED_FIELDS if values[field] is None)


def _normalize_slug(value: str) -> str:
    normalized = value.strip().lower()
    if not 2 <= len(normalized) <= 80 or _SLUG.fullmatch(normalized) is None:
        raise _invalid_club()
    try:
        UUID(normalized)
    except ValueError:
        return normalized
    raise _invalid_club()


def _normalize_name(value: str) -> str:
    normalized = value.strip()
    if not 2 <= len(normalized) <= 120:
        raise _invalid_club()
    return normalized


def _normalize_description(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > 20_000:
        raise _invalid_club()
    return normalized


def _normalize_optional_slug(value: str | None, *, maximum: int = 80) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized or len(normalized) > maximum or _SLUG.fullmatch(normalized) is None:
        raise _invalid_club()
    return normalized


def _normalize_country(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise _invalid_club()
    return normalized


def _normalize_social_links(value: dict[str, str] | None) -> dict[str, str]:
    if value is None:
        return {}
    if len(value) > 12:
        raise _invalid_club()
    normalized: dict[str, str] = {}
    for raw_key, raw_url in value.items():
        key = raw_key.strip().lower()
        url = raw_url.strip()
        parsed = urlsplit(url)
        if (
            _SOCIAL_KEY.fullmatch(key) is None
            or len(url) > 2_048
            or parsed.scheme not in {"http", "https"}
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise _invalid_club()
        normalized[key] = url
    return dict(sorted(normalized.items()))


def _normalized_new(value: NewClub) -> NewClub:
    return NewClub(
        slug=_normalize_slug(value.slug),
        name=_normalize_name(value.name),
        description=_normalize_description(value.description),
        category_slug=_normalize_optional_slug(value.category_slug),
        country_code=_normalize_country(value.country_code),
        city_slug=_normalize_optional_slug(value.city_slug),
        membership_policy=value.membership_policy,
        social_links=_normalize_social_links(value.social_links),
        logo_media_id=value.logo_media_id,
        cover_media_id=value.cover_media_id,
    )


class ClubService:
    def __init__(
        self,
        repository: ClubRepositoryProtocol,
        eligibility: ClubEligibility,
        audit: AuditService,
    ) -> None:
        self._repository = repository
        self._eligibility = eligibility
        self._audit = audit

    async def create(
        self,
        principal: AuthPrincipal,
        value: NewClub,
        *,
        request_id: UUID,
        now: datetime | None = None,
    ) -> Club:
        await self._repository.lock_owner_creation(principal.user_id)
        capabilities = await self._eligibility.evaluate(principal)
        if not capabilities.create_club:
            blocker = next(
                (item for item in _CREATE_BLOCKERS if item in capabilities.blockers),
                "forbidden",
            )
            raise ApiError(
                code=blocker,
                message_key=f"blockers.{blocker}",
                status_code=403,
            )
        normalized = _normalized_new(value)
        references = await self._repository.resolve_references(
            owner_user_id=principal.user_id,
            category_slug=normalized.category_slug,
            country_code=normalized.country_code,
            city_slug=normalized.city_slug,
            logo_media_id=normalized.logo_media_id,
            cover_media_id=normalized.cover_media_id,
        )
        current = now or datetime.now(UTC)
        status: ClubStatus = "published" if not missing_fields(normalized) else "draft"
        club = await self._repository.create(
            owner_user_id=principal.user_id,
            slug=normalized.slug,
            name=normalized.name,
            description=normalized.description,
            category_slug=normalized.category_slug,
            country_code=normalized.country_code,
            city_slug=normalized.city_slug,
            membership_policy=normalized.membership_policy,
            social_links=normalized.social_links or {},
            references=references,
            status=status,
            published_at=current if status == "published" else None,
        )
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="organizer",
            action="club.create",
            target_type="club",
            target_id=club.id,
            safe_after={
                "status": club.status,
                "revision": club.revision,
                "missing_fields": list(missing_fields(club)),
            },
            request_id=request_id,
        )
        if club.status == "published":
            await self._audit.record(
                actor_user_id=principal.user_id,
                actor_kind="organizer",
                action="club.publish",
                target_type="club",
                target_id=club.id,
                safe_before={"status": "draft"},
                safe_after={"status": "published", "revision": club.revision},
                request_id=request_id,
            )
        return club

    async def list_managed(self, principal: AuthPrincipal) -> tuple[ManagedClub, ...]:
        if principal.status != "active":
            raise ApiError(code="forbidden", message_key="errors.forbidden", status_code=403)
        return tuple(
            ManagedClub(
                club=club,
                role=role,
                capabilities=self._workspace_capabilities(club, role),
            )
            for club, role in await self._repository.list_managed(principal.user_id)
        )

    async def get(self, principal: AuthPrincipal, club_id: UUID) -> Club:
        club = await self._find(club_id)
        access = await self._repository.get_access(club.id, principal.user_id)
        can_edit_club(principal, club, access)
        return club

    async def update(
        self,
        principal: AuthPrincipal,
        club_id: UUID,
        patch: ClubPatch,
        *,
        request_id: UUID,
        now: datetime | None = None,
    ) -> Club:
        club = await self._find(club_id, for_update=True)
        access = await self._repository.get_access(club.id, principal.user_id, for_update=True)
        can_edit_club(principal, club, access)
        if patch.revision != club.revision:
            raise ApiError(
                code="stale_revision",
                message_key="errors.conflict",
                status_code=409,
            )
        candidate = self._patched(club, patch)
        incomplete = missing_fields(candidate)
        if club.status == "draft":
            status: ClubStatus = "published" if not incomplete else "draft"
        else:
            if incomplete:
                raise _invalid_club()
            status = club.status
        candidate = replace(candidate, status=status)
        references = await self._repository.resolve_references(
            owner_user_id=club.owner_user_id,
            category_slug=candidate.category_slug,
            country_code=candidate.country_code,
            city_slug=candidate.city_slug,
            logo_media_id=candidate.logo_media_id,
            cover_media_id=candidate.cover_media_id,
        )
        current = now or datetime.now(UTC)
        updated = await self._repository.update(
            candidate,
            references=references,
            expected_revision=patch.revision,
            published_at=current if club.status == "draft" and status == "published" else None,
        )
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="organizer",
            action="club.update",
            target_type="club",
            target_id=club.id,
            safe_before={"status": club.status, "revision": club.revision},
            safe_after={
                "status": updated.status,
                "revision": updated.revision,
                "missing_fields": list(missing_fields(updated)),
            },
            request_id=request_id,
        )
        if club.status == "draft" and updated.status == "published":
            await self._audit.record(
                actor_user_id=principal.user_id,
                actor_kind="organizer",
                action="club.publish",
                target_type="club",
                target_id=club.id,
                safe_before={"status": "draft", "revision": club.revision},
                safe_after={"status": "published", "revision": updated.revision},
                request_id=request_id,
            )
        return updated

    @staticmethod
    def _workspace_capabilities(club: Club, role: ClubRole) -> tuple[WorkspaceCapability, ...]:
        if club.status in ("suspended", "closed"):
            return ()
        shared: tuple[WorkspaceCapability, ...] = (
            "edit_profile",
            "manage_members",
        )
        if role == "owner":
            return (
                *shared,
                "change_member_roles",
                "transfer_ownership",
                "close_club",
                "preview_profile",
            )
        return (*shared, "preview_profile")

    async def _find(self, club_id: UUID, *, for_update: bool = False) -> Club:
        try:
            identifier = validate_uuid7(club_id)
        except ValueError:
            raise _not_found() from None
        club = await self._repository.get(identifier, for_update=for_update)
        if club is None:
            raise _not_found()
        return club

    @staticmethod
    def _patched(club: Club, patch: ClubPatch) -> Club:
        fields = patch.changed_fields
        if "slug" in fields and patch.slug is None:
            raise _invalid_club()
        if "name" in fields and patch.name is None:
            raise _invalid_club()
        if "membership_policy" in fields and patch.membership_policy is None:
            raise _invalid_club()
        if "social_links" in fields and patch.social_links is None:
            raise _invalid_club()
        return replace(
            club,
            slug=(
                _normalize_slug(patch.slug)
                if "slug" in fields and patch.slug is not None
                else club.slug
            ),
            name=(
                _normalize_name(patch.name)
                if "name" in fields and patch.name is not None
                else club.name
            ),
            description=(
                _normalize_description(patch.description)
                if "description" in fields
                else club.description
            ),
            category_slug=(
                _normalize_optional_slug(patch.category_slug)
                if "category_slug" in fields
                else club.category_slug
            ),
            country_code=(
                _normalize_country(patch.country_code)
                if "country_code" in fields
                else club.country_code
            ),
            city_slug=(
                _normalize_optional_slug(patch.city_slug)
                if "city_slug" in fields
                else club.city_slug
            ),
            membership_policy=(
                patch.membership_policy
                if "membership_policy" in fields and patch.membership_policy is not None
                else club.membership_policy
            ),
            social_links=(
                _normalize_social_links(patch.social_links)
                if "social_links" in fields
                else club.social_links
            ),
            logo_media_id=(
                patch.logo_media_id if "logo_media_id" in fields else club.logo_media_id
            ),
            cover_media_id=(
                patch.cover_media_id if "cover_media_id" in fields else club.cover_media_id
            ),
        )
