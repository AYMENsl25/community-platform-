from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.profiles.models import EligibilityState, Profile, ProfileReplacement
from talaqi.regions.models import Locale


def _profile_from_row(row: Mapping[str, object]) -> Profile:
    return Profile(
        user_id=cast(UUID, row["user_id"]),
        username=cast(str, row["username"]),
        display_name=cast(str, row["display_name"]),
        country_code=cast(str, row["country_code"]).strip(),
        city_slug=cast(str, row["city_slug"]),
        locale=cast(Locale, row["locale"]),
        time_zone=cast(str, row["time_zone"]),
        preferred_currency=cast(str, row["preferred_currency"]).strip(),
        notify_security_email=cast(bool, row["notify_security_email"]),
        notify_event_email=cast(bool, row["notify_event_email"]),
        notify_community_email=cast(bool, row["notify_community_email"]),
        organizer_rules_version=cast(str | None, row["organizer_rules_version"]),
        community_rules_version=cast(str | None, row["community_rules_version"]),
        profile_completed_at=cast(datetime | None, row["profile_completed_at"]),
        avatar=None,
    )


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_principal(self, principal: AuthPrincipal) -> AuthPrincipal:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT status::text AS status, email_verified_at,
                               is_platform_admin
                        FROM talaqi.users
                        WHERE id = :user_id
                        FOR UPDATE
                        """
                    ),
                    {"user_id": principal.user_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ApiError(
                code="authentication_required",
                message_key="errors.authentication_required",
                status_code=401,
            )
        return replace(
            principal,
            status=cast(str, row["status"]),  # type: ignore[arg-type]
            email_verified=row["email_verified_at"] is not None,
            is_platform_admin=cast(bool, row["is_platform_admin"]),
        )

    async def get(self, user_id: UUID) -> Profile | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT
                            profile.user_id,
                            profile.username,
                            profile.display_name,
                            country.code AS country_code,
                            city.slug AS city_slug,
                            profile.locale,
                            profile.time_zone,
                            profile.preferred_currency,
                            profile.notify_security_email,
                            profile.notify_event_email,
                            profile.notify_community_email,
                            users.organizer_rules_version,
                            users.community_rules_version,
                            profile.profile_completed_at
                        FROM talaqi.profiles AS profile
                        JOIN talaqi.users AS users ON users.id = profile.user_id
                        JOIN talaqi.countries AS country ON country.id = profile.country_id
                        JOIN talaqi.cities AS city ON city.id = profile.city_id
                        WHERE profile.user_id = :user_id
                        """
                    ),
                    {"user_id": user_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else _profile_from_row(cast(Mapping[str, object], row))

    async def replace(
        self,
        user_id: UUID,
        replacement: ProfileReplacement,
        completed_at: datetime,
    ) -> Profile:
        values = {
            "user_id": user_id,
            "username": replacement.username,
            "display_name": replacement.display_name,
            "country_code": replacement.country_code,
            "city_slug": replacement.city_slug,
            "locale": replacement.locale,
            "time_zone": replacement.time_zone,
            "preferred_currency": replacement.preferred_currency,
            "notify_event_email": replacement.notify_event_email,
            "notify_community_email": replacement.notify_community_email,
            "organizer_rules_version": replacement.organizer_rules_version,
            "community_rules_version": replacement.community_rules_version,
            "completed_at": completed_at,
        }
        try:
            await self._session.execute(
                text(
                    """
                    UPDATE talaqi.users
                    SET organizer_rules_version = :organizer_rules_version,
                        community_rules_version = :community_rules_version
                    WHERE id = :user_id
                    """
                ),
                values,
            )
            row = (
                (
                    await self._session.execute(
                        text(
                            """
                            INSERT INTO talaqi.profiles (
                                user_id,
                                username,
                                display_name,
                                country_id,
                                city_id,
                                locale,
                                time_zone,
                                preferred_currency,
                                notify_security_email,
                                notify_event_email,
                                notify_community_email,
                                profile_completed_at
                            )
                            SELECT
                                :user_id,
                                :username,
                                :display_name,
                                country.id,
                                city.id,
                                :locale,
                                :time_zone,
                                :preferred_currency,
                                true,
                                :notify_event_email,
                                :notify_community_email,
                                :completed_at
                            FROM talaqi.countries AS country
                            JOIN talaqi.cities AS city ON city.country_id = country.id
                            WHERE country.code = :country_code
                              AND city.slug = :city_slug
                              AND country.enabled = true
                              AND city.enabled = true
                              AND city.beta_enabled = true
                            ON CONFLICT (user_id) DO UPDATE SET
                                username = EXCLUDED.username,
                                display_name = EXCLUDED.display_name,
                                country_id = EXCLUDED.country_id,
                                city_id = EXCLUDED.city_id,
                                locale = EXCLUDED.locale,
                                time_zone = EXCLUDED.time_zone,
                                preferred_currency = EXCLUDED.preferred_currency,
                                notify_security_email = true,
                                notify_event_email = EXCLUDED.notify_event_email,
                                notify_community_email = EXCLUDED.notify_community_email,
                                profile_completed_at = EXCLUDED.profile_completed_at
                            RETURNING user_id
                            """
                        ),
                        values,
                    )
                )
                .mappings()
                .one_or_none()
            )
        except IntegrityError:
            raise ApiError(
                code="username_unavailable",
                message_key="errors.username_unavailable",
                status_code=409,
            ) from None
        if row is None:
            raise ApiError(
                code="invalid_profile",
                message_key="errors.invalid_profile",
                status_code=422,
            )
        profile = await self.get(user_id)
        if profile is None:
            raise RuntimeError("profile replacement did not persist")
        return profile

    async def eligibility_state(self, user_id: UUID) -> EligibilityState:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT
                            users.terms_version,
                            users.privacy_version,
                            users.organizer_rules_version,
                            users.community_rules_version,
                            profile.user_id AS profile_user_id,
                            profile.username,
                            profile.display_name,
                            country.code AS country_code,
                            city.slug AS city_slug,
                            profile.locale,
                            profile.time_zone,
                            profile.preferred_currency,
                            profile.notify_security_email,
                            profile.notify_event_email,
                            profile.notify_community_email,
                            profile.profile_completed_at,
                            (
                                SELECT count(*)
                                FROM talaqi.clubs AS club
                                WHERE club.owner_user_id = users.id
                                  AND club.status <> 'closed'
                            ) AS owned_club_count,
                            (
                                SELECT count(*)
                                FROM talaqi.events AS event
                                WHERE event.owner_user_id = users.id
                                  AND event.ownership_type = 'independent'
                                  AND event.status NOT IN ('cancelled', 'completed')
                            ) AS active_independent_event_count,
                            EXISTS (
                                SELECT 1
                                FROM talaqi.user_mfa_factors AS factor
                                WHERE factor.user_id = users.id
                                  AND factor.verified_at IS NOT NULL
                                  AND factor.disabled_at IS NULL
                            ) AS has_active_mfa
                        FROM talaqi.users AS users
                        LEFT JOIN talaqi.profiles AS profile ON profile.user_id = users.id
                        LEFT JOIN talaqi.countries AS country ON country.id = profile.country_id
                        LEFT JOIN talaqi.cities AS city ON city.id = profile.city_id
                        WHERE users.id = :user_id
                        """
                    ),
                    {"user_id": user_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ApiError(
                code="authentication_required",
                message_key="errors.authentication_required",
                status_code=401,
            )
        profile: Profile | None = None
        if row["profile_user_id"] is not None:
            profile_row = dict(row)
            profile_row["user_id"] = profile_row["profile_user_id"]
            profile = _profile_from_row(profile_row)
        return EligibilityState(
            profile=profile,
            terms_version=cast(str, row["terms_version"]),
            privacy_version=cast(str, row["privacy_version"]),
            organizer_rules_version=cast(str | None, row["organizer_rules_version"]),
            community_rules_version=cast(str | None, row["community_rules_version"]),
            owned_club_count=cast(int, row["owned_club_count"]),
            active_independent_event_count=cast(int, row["active_independent_event_count"]),
            has_active_mfa=cast(bool, row["has_active_mfa"]),
        )


__all__ = ["ProfileRepository"]
