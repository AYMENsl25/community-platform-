from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.platform import ApiError
from talaqi.regions.models import (
    Category,
    City,
    Country,
    Locale,
    ProfileRegionSnapshot,
    RegionPolicy,
)


class RegionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_policy(self, country_code: str) -> RegionPolicy:
        return await self._get_policy(country_code, for_update=False)

    async def lock_policy(self, country_code: str) -> RegionPolicy:
        return await self._get_policy(country_code, for_update=True)

    async def _get_policy(self, country_code: str, *, for_update: bool) -> RegionPolicy:
        locking = " FOR UPDATE OF p" if for_update else ""
        row = (
            (
                await self._session.execute(
                    text(
                        """
                    SELECT
                        c.code, c.default_locale, c.default_currency,
                        p.allowed_registration_methods,
                        p.cash_expiry_default_minutes,
                        p.cash_expiry_min_minutes, p.cash_expiry_max_minutes,
                        p.cancellation_default_minutes,
                        p.cancellation_min_minutes, p.cancellation_max_minutes,
                        p.default_club_ownership_limit,
                        p.default_active_independent_event_limit,
                        p.exact_venue_public_by_default, p.revision
                    FROM talaqi.countries AS c
                    JOIN talaqi.regional_policies AS p ON p.country_id = c.id
                    WHERE c.code = :country_code AND c.enabled = true
                    """
                        + locking
                    ),
                    {"country_code": country_code.strip().upper()},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ApiError(
                code="region_not_found",
                message_key="errors.region_not_found",
                status_code=404,
            )
        return RegionPolicy(
            country_code=row["code"],
            default_locale=cast(Locale, row["default_locale"]),
            default_currency=row["default_currency"],
            allowed_registration_methods=tuple(row["allowed_registration_methods"]),
            cash_default_minutes=row["cash_expiry_default_minutes"],
            cash_bounds=(row["cash_expiry_min_minutes"], row["cash_expiry_max_minutes"]),
            cancellation_default_minutes=row["cancellation_default_minutes"],
            cancellation_bounds=(
                row["cancellation_min_minutes"],
                row["cancellation_max_minutes"],
            ),
            club_limit=row["default_club_ownership_limit"],
            independent_event_limit=row["default_active_independent_event_limit"],
            exact_venue_public_by_default=row["exact_venue_public_by_default"],
            revision=row["revision"],
        )

    async def has_active_mfa(self, user_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                text(
                    """SELECT EXISTS (
                        SELECT 1 FROM talaqi.user_mfa_factors
                        WHERE user_id = :user_id AND verified_at IS NOT NULL AND disabled_at IS NULL
                    )"""
                ),
                {"user_id": user_id},
            )
        )

    async def update_safe_policy_controls(
        self,
        country_code: str,
        *,
        expected_revision: int,
        club_limit: int,
        independent_event_limit: int,
        exact_venue_public_by_default: bool,
    ) -> RegionPolicy | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        UPDATE talaqi.regional_policies AS p
                        SET default_club_ownership_limit = :club_limit,
                            default_active_independent_event_limit = :event_limit,
                            exact_venue_public_by_default = :venue_default,
                            revision = revision + 1
                        FROM talaqi.countries AS c
                        WHERE p.country_id = c.id AND c.code = :country_code
                          AND c.enabled = true AND p.revision = :expected_revision
                        RETURNING c.code, c.default_locale, c.default_currency,
                                  p.allowed_registration_methods,
                                  p.cash_expiry_default_minutes,
                                  p.cash_expiry_min_minutes, p.cash_expiry_max_minutes,
                                  p.cancellation_default_minutes,
                                  p.cancellation_min_minutes, p.cancellation_max_minutes,
                                  p.default_club_ownership_limit,
                                  p.default_active_independent_event_limit,
                                  p.exact_venue_public_by_default, p.revision
                        """
                    ),
                    {
                        "country_code": country_code.strip().upper(),
                        "expected_revision": expected_revision,
                        "club_limit": club_limit,
                        "event_limit": independent_event_limit,
                        "venue_default": exact_venue_public_by_default,
                    },
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return RegionPolicy(
            country_code=row["code"],
            default_locale=cast(Locale, row["default_locale"]),
            default_currency=row["default_currency"],
            allowed_registration_methods=tuple(row["allowed_registration_methods"]),
            cash_default_minutes=row["cash_expiry_default_minutes"],
            cash_bounds=(row["cash_expiry_min_minutes"], row["cash_expiry_max_minutes"]),
            cancellation_default_minutes=row["cancellation_default_minutes"],
            cancellation_bounds=(row["cancellation_min_minutes"], row["cancellation_max_minutes"]),
            club_limit=row["default_club_ownership_limit"],
            independent_event_limit=row["default_active_independent_event_limit"],
            exact_venue_public_by_default=row["exact_venue_public_by_default"],
            revision=row["revision"],
        )

    async def list_countries(self) -> tuple[Country, ...]:
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT code, name_key, default_locale, default_currency
                    FROM talaqi.countries
                    WHERE enabled = true
                    ORDER BY code
                    """
                )
            )
        ).mappings()
        return tuple(
            Country(
                code=row["code"],
                name_key=row["name_key"],
                default_locale=cast(Locale, row["default_locale"]),
                default_currency=row["default_currency"],
            )
            for row in rows
        )

    async def list_cities(self, country_code: str | None = None) -> tuple[City, ...]:
        normalized = country_code.strip().upper() if country_code is not None else None
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT c.code AS country_code, city.slug, city.name_key,
                           city.time_zone, city.beta_enabled
                    FROM talaqi.cities AS city
                    JOIN talaqi.countries AS c ON c.id = city.country_id
                    WHERE city.enabled = true AND city.beta_enabled = true AND c.enabled = true
                      AND (
                          CAST(:country_code AS char(2)) IS NULL
                          OR c.code = CAST(:country_code AS char(2))
                      )
                    ORDER BY c.code, city.slug
                    """
                ),
                {"country_code": normalized},
            )
        ).mappings()
        return tuple(
            City(
                country_code=row["country_code"],
                slug=row["slug"].lower(),
                name_key=row["name_key"],
                time_zone=row["time_zone"],
                beta_enabled=row["beta_enabled"],
            )
            for row in rows
        )

    async def list_categories(self) -> tuple[Category, ...]:
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT slug, name_key, icon_key, sort_order
                    FROM talaqi.categories
                    WHERE enabled = true
                    ORDER BY sort_order, slug
                    """
                )
            )
        ).mappings()
        return tuple(
            Category(
                slug=row["slug"].lower(),
                name_key=row["name_key"],
                icon_key=row["icon_key"],
                sort_order=row["sort_order"],
            )
            for row in rows
        )

    async def get_profile_region(self, country_code: str, city_slug: str) -> ProfileRegionSnapshot:
        return await self._profile_region_snapshot(country_code, city_slug, lock=False)

    async def lock_profile_region(self, country_code: str, city_slug: str) -> ProfileRegionSnapshot:
        return await self._profile_region_snapshot(country_code, city_slug, lock=True)

    async def _profile_region_snapshot(
        self,
        country_code: str,
        city_slug: str,
        *,
        lock: bool,
    ) -> ProfileRegionSnapshot:
        lock_clause = " FOR SHARE OF country, city, policy" if lock else ""
        statement = text(
            """
            SELECT
                country.code,
                country.default_locale,
                country.default_currency,
                country.enabled AS country_enabled,
                city.slug,
                city.time_zone,
                city.enabled AS city_enabled,
                city.beta_enabled,
                policy.default_club_ownership_limit,
                policy.default_active_independent_event_limit
            FROM talaqi.countries AS country
            JOIN talaqi.cities AS city ON city.country_id = country.id
            JOIN talaqi.regional_policies AS policy ON policy.country_id = country.id
            WHERE country.code = :country_code
              AND city.slug = :city_slug
            """
            + lock_clause
        )
        row = (
            (
                await self._session.execute(
                    statement,
                    {
                        "country_code": country_code.strip().upper(),
                        "city_slug": city_slug.strip().lower(),
                    },
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ApiError(
                code="region_not_found",
                message_key="errors.region_not_found",
                status_code=404,
            )
        return ProfileRegionSnapshot(
            country_code=row["code"].strip(),
            city_slug=row["slug"],
            default_locale=cast(Locale, row["default_locale"]),
            default_currency=row["default_currency"].strip(),
            time_zone=row["time_zone"],
            country_enabled=row["country_enabled"],
            city_enabled=row["city_enabled"],
            beta_enabled=row["beta_enabled"],
            club_limit=row["default_club_ownership_limit"],
            independent_event_limit=row["default_active_independent_event_limit"],
        )
