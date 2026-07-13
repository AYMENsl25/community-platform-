from __future__ import annotations

from typing import cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.platform import ApiError
from talaqi.regions.models import Category, City, Country, Locale, RegionPolicy


class RegionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_policy(self, country_code: str) -> RegionPolicy:
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
