from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.clubs.models import (
    Club,
    ClubAccess,
    ClubMembershipPolicy,
    ClubReferences,
    ClubRole,
    ClubStatus,
    ManagedClubRole,
)
from talaqi.db.identifiers import generate_uuid7
from talaqi.platform import ApiError


def _invalid_club() -> ApiError:
    return ApiError(code="invalid_club", message_key="errors.validation", status_code=422)


def _club(row: Mapping[str, object]) -> Club:
    social_links = cast(dict[str, object], row["social_links"])
    return Club(
        id=cast(UUID, row["id"]),
        owner_user_id=cast(UUID, row["owner_user_id"]),
        slug=cast(str, row["slug"]),
        name=cast(str, row["name"]),
        description=cast(str | None, row["description"]),
        category_slug=cast(str | None, row["category_slug"]),
        country_code=(
            cast(str, row["country_code"]).strip() if row["country_code"] is not None else None
        ),
        city_slug=cast(str | None, row["city_slug"]),
        membership_policy=cast(ClubMembershipPolicy, row["membership_policy"]),
        social_links={key: cast(str, value) for key, value in social_links.items()},
        logo_media_id=cast(UUID | None, row["logo_media_id"]),
        cover_media_id=cast(UUID | None, row["cover_media_id"]),
        revision=cast(int, row["revision"]),
        status=cast(ClubStatus, row["status"]),
        published_at=cast(datetime | None, row["published_at"]),
        suspended_at=cast(datetime | None, row["suspended_at"]),
        suspension_reason=cast(str | None, row["suspension_reason"]),
        closed_at=cast(datetime | None, row["closed_at"]),
        created_at=cast(datetime, row["created_at"]),
        updated_at=cast(datetime, row["updated_at"]),
    )


_CLUB_SELECT = """
    SELECT club.id, club.owner_user_id, club.slug, club.name, club.description,
           category.slug AS category_slug, country.code AS country_code,
           city.slug AS city_slug, club.membership_policy::text AS membership_policy,
           club.social_links, club.logo_media_id, club.cover_media_id, club.revision,
           club.status::text AS status, club.published_at, club.suspended_at,
           club.suspension_reason, club.closed_at, club.created_at, club.updated_at
    FROM talaqi.clubs AS club
    LEFT JOIN talaqi.categories AS category ON category.id = club.category_id
    LEFT JOIN talaqi.countries AS country ON country.id = club.country_id
    LEFT JOIN talaqi.cities AS city ON city.id = club.city_id
    WHERE club.id = :club_id
"""


class ClubRepositoryProtocol(Protocol):
    async def lock_owner_creation(self, user_id: UUID) -> None: ...

    async def resolve_references(
        self,
        *,
        owner_user_id: UUID,
        category_slug: str | None,
        country_code: str | None,
        city_slug: str | None,
        logo_media_id: UUID | None,
        cover_media_id: UUID | None,
    ) -> ClubReferences: ...

    async def create(
        self,
        *,
        owner_user_id: UUID,
        slug: str,
        name: str,
        description: str | None,
        category_slug: str | None,
        country_code: str | None,
        city_slug: str | None,
        membership_policy: ClubMembershipPolicy,
        social_links: dict[str, str],
        references: ClubReferences,
        status: ClubStatus,
        published_at: datetime | None,
    ) -> Club: ...

    async def get(self, club_id: UUID, *, for_update: bool = False) -> Club | None: ...

    async def get_access(
        self,
        club_id: UUID,
        user_id: UUID,
        *,
        for_update: bool = False,
    ) -> ClubAccess | None: ...

    async def list_managed(self, user_id: UUID) -> list[tuple[Club, ManagedClubRole]]: ...

    async def update(
        self,
        club: Club,
        *,
        references: ClubReferences,
        expected_revision: int,
        published_at: datetime | None,
    ) -> Club: ...


class ClubRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_owner_creation(self, user_id: UUID) -> None:
        found = (
            await self._session.execute(
                text("SELECT id FROM talaqi.users WHERE id = :user_id FOR UPDATE"),
                {"user_id": user_id},
            )
        ).scalar_one_or_none()
        if found is None:
            raise ApiError(
                code="authentication_required",
                message_key="errors.authentication_required",
                status_code=401,
            )
        await self._session.execute(
            text(
                """
                SELECT policy.id
                FROM talaqi.profiles AS profile
                JOIN talaqi.countries AS country ON country.id = profile.country_id
                JOIN talaqi.cities AS city ON city.id = profile.city_id
                JOIN talaqi.regional_policies AS policy ON policy.country_id = country.id
                WHERE profile.user_id = :user_id
                FOR SHARE OF country, city, policy
                """
            ),
            {"user_id": user_id},
        )

    async def resolve_references(
        self,
        *,
        owner_user_id: UUID,
        category_slug: str | None,
        country_code: str | None,
        city_slug: str | None,
        logo_media_id: UUID | None,
        cover_media_id: UUID | None,
    ) -> ClubReferences:
        if city_slug is not None and country_code is None:
            raise _invalid_club()
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT
                            (
                                SELECT id FROM talaqi.categories
                                WHERE slug = CAST(:category_slug AS text) AND enabled = true
                                FOR SHARE
                            ) AS category_id,
                            (
                                SELECT id FROM talaqi.countries
                                WHERE code = CAST(:country_code AS char(2)) AND enabled = true
                                FOR SHARE
                            ) AS country_id,
                            (
                                SELECT city.id
                                FROM talaqi.cities AS city
                                JOIN talaqi.countries AS country
                                  ON country.id = city.country_id
                                WHERE country.code = CAST(:country_code AS char(2))
                                  AND city.slug = CAST(:city_slug AS text)
                                  AND country.enabled = true
                                  AND city.enabled = true
                                  AND city.beta_enabled = true
                                FOR SHARE OF country, city
                            ) AS city_id,
                            (
                                SELECT id FROM talaqi.media_assets
                                WHERE id = CAST(:logo_media_id AS uuid)
                                  AND owner_user_id = :owner_user_id
                                  AND status = 'verified'
                                FOR SHARE
                            ) AS logo_media_id,
                            (
                                SELECT id FROM talaqi.media_assets
                                WHERE id = CAST(:cover_media_id AS uuid)
                                  AND owner_user_id = :owner_user_id
                                  AND status = 'verified'
                                FOR SHARE
                            ) AS cover_media_id
                        """
                    ),
                    {
                        "owner_user_id": owner_user_id,
                        "category_slug": category_slug,
                        "country_code": country_code,
                        "city_slug": city_slug,
                        "logo_media_id": logo_media_id,
                        "cover_media_id": cover_media_id,
                    },
                )
            )
            .mappings()
            .one()
        )
        references = ClubReferences(
            category_id=cast(UUID | None, row["category_id"]),
            country_id=cast(UUID | None, row["country_id"]),
            city_id=cast(UUID | None, row["city_id"]),
            logo_media_id=cast(UUID | None, row["logo_media_id"]),
            cover_media_id=cast(UUID | None, row["cover_media_id"]),
        )
        expected = (
            (category_slug, references.category_id),
            (country_code, references.country_id),
            (city_slug, references.city_id),
            (logo_media_id, references.logo_media_id),
            (cover_media_id, references.cover_media_id),
        )
        if any(requested is not None and resolved is None for requested, resolved in expected):
            raise _invalid_club()
        return references

    async def create(
        self,
        *,
        owner_user_id: UUID,
        slug: str,
        name: str,
        description: str | None,
        category_slug: str | None,
        country_code: str | None,
        city_slug: str | None,
        membership_policy: ClubMembershipPolicy,
        social_links: dict[str, str],
        references: ClubReferences,
        status: ClubStatus,
        published_at: datetime | None,
    ) -> Club:
        club_id = generate_uuid7()
        try:
            await self._session.execute(
                text(
                    """
                    INSERT INTO talaqi.clubs (
                        id, owner_user_id, slug, name, description, category_id,
                        country_id, city_id, membership_policy, status, logo_media_id,
                        cover_media_id, social_links, published_at
                    ) VALUES (
                        :id, :owner_user_id, :slug, :name, :description, :category_id,
                        :country_id, :city_id,
                        CAST(:membership_policy AS talaqi.club_membership_policy),
                        CAST(:status AS talaqi.club_status), :logo_media_id,
                        :cover_media_id, CAST(:social_links AS jsonb), :published_at
                    )
                    """
                ),
                {
                    "id": club_id,
                    "owner_user_id": owner_user_id,
                    "slug": slug,
                    "name": name,
                    "description": description,
                    "category_id": references.category_id,
                    "country_id": references.country_id,
                    "city_id": references.city_id,
                    "membership_policy": membership_policy,
                    "status": status,
                    "logo_media_id": references.logo_media_id,
                    "cover_media_id": references.cover_media_id,
                    "social_links": json.dumps(social_links, separators=(",", ":"), sort_keys=True),
                    "published_at": published_at,
                },
            )
            await self._session.execute(
                text(
                    """
                    INSERT INTO talaqi.club_memberships (id, club_id, user_id, role)
                    VALUES (:id, :club_id, :user_id, 'owner')
                    """
                ),
                {
                    "id": generate_uuid7(),
                    "club_id": club_id,
                    "user_id": owner_user_id,
                },
            )
        except IntegrityError:
            raise ApiError(
                code="duplicate_slug",
                message_key="errors.conflict",
                status_code=409,
            ) from None
        created = await self.get(club_id)
        if created is None:
            raise RuntimeError("club creation did not persist")
        return created

    async def get(self, club_id: UUID, *, for_update: bool = False) -> Club | None:
        query = _CLUB_SELECT + (" FOR UPDATE OF club" if for_update else "")
        row = (
            (
                await self._session.execute(
                    text(query),
                    {"club_id": club_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else _club(cast(Mapping[str, object], row))

    async def get_access(
        self,
        club_id: UUID,
        user_id: UUID,
        *,
        for_update: bool = False,
    ) -> ClubAccess | None:
        suffix = " FOR UPDATE OF membership" if for_update else ""
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT membership.club_id, membership.user_id,
                               membership.role::text AS role
                        FROM talaqi.club_memberships AS membership
                        WHERE membership.club_id = :club_id
                          AND membership.user_id = :user_id
                        """
                        + suffix
                    ),
                    {"club_id": club_id, "user_id": user_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return ClubAccess(
            club_id=cast(UUID, row["club_id"]),
            user_id=cast(UUID, row["user_id"]),
            role=cast(ClubRole, row["role"]),
        )

    async def list_managed(self, user_id: UUID) -> list[tuple[Club, ManagedClubRole]]:
        rows = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT club.id, club.owner_user_id, club.slug, club.name,
                               club.description, category.slug AS category_slug,
                               country.code AS country_code, city.slug AS city_slug,
                               club.membership_policy::text AS membership_policy,
                               club.social_links, club.logo_media_id, club.cover_media_id,
                               club.revision, club.status::text AS status,
                               club.published_at, club.suspended_at,
                               club.suspension_reason, club.closed_at,
                               club.created_at, club.updated_at,
                               membership.role::text AS actor_role
                        FROM talaqi.club_memberships AS membership
                        JOIN talaqi.clubs AS club ON club.id = membership.club_id
                        LEFT JOIN talaqi.categories AS category ON category.id = club.category_id
                        LEFT JOIN talaqi.countries AS country ON country.id = club.country_id
                        LEFT JOIN talaqi.cities AS city ON city.id = club.city_id
                        WHERE membership.user_id = :user_id
                          AND membership.role IN ('owner', 'admin')
                        ORDER BY club.updated_at DESC, club.id
                        """
                    ),
                    {"user_id": user_id},
                )
            )
            .mappings()
            .all()
        )
        return [
            (
                _club(cast(Mapping[str, object], row)),
                cast(ManagedClubRole, row["actor_role"]),
            )
            for row in rows
        ]

    async def update(
        self,
        club: Club,
        *,
        references: ClubReferences,
        expected_revision: int,
        published_at: datetime | None,
    ) -> Club:
        try:
            updated_id = (
                await self._session.execute(
                    text(
                        """
                        UPDATE talaqi.clubs
                        SET slug = :slug,
                            name = :name,
                            description = :description,
                            category_id = :category_id,
                            country_id = :country_id,
                            city_id = :city_id,
                            membership_policy = CAST(
                                :membership_policy AS talaqi.club_membership_policy
                            ),
                            status = CAST(:status AS talaqi.club_status),
                            logo_media_id = :logo_media_id,
                            cover_media_id = :cover_media_id,
                            social_links = CAST(:social_links AS jsonb),
                            published_at = COALESCE(published_at, :published_at),
                            revision = revision + 1
                        WHERE id = :club_id AND revision = :expected_revision
                        RETURNING id
                        """
                    ),
                    {
                        "club_id": club.id,
                        "slug": club.slug,
                        "name": club.name,
                        "description": club.description,
                        "category_id": references.category_id,
                        "country_id": references.country_id,
                        "city_id": references.city_id,
                        "membership_policy": club.membership_policy,
                        "status": club.status,
                        "logo_media_id": references.logo_media_id,
                        "cover_media_id": references.cover_media_id,
                        "social_links": json.dumps(
                            club.social_links, separators=(",", ":"), sort_keys=True
                        ),
                        "published_at": published_at,
                        "expected_revision": expected_revision,
                    },
                )
            ).scalar_one_or_none()
        except IntegrityError:
            raise ApiError(
                code="duplicate_slug",
                message_key="errors.conflict",
                status_code=409,
            ) from None
        if updated_id is None:
            raise ApiError(
                code="stale_revision",
                message_key="errors.conflict",
                status_code=409,
            )
        updated = await self.get(club.id)
        if updated is None:
            raise RuntimeError("club update did not persist")
        return updated
