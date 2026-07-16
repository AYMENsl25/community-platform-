from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from talaqi.identity.models import AuthPrincipal
from talaqi.identity.passwords import normalize_username
from talaqi.platform import ApiError
from talaqi.profiles.models import Profile, ProfileReplacement
from talaqi.regions.models import ProfileRegion


class ProfileRepositoryProtocol(Protocol):
    async def get(self, user_id: UUID) -> Profile | None: ...
    async def replace(
        self, user_id: UUID, replacement: ProfileReplacement, completed_at: datetime
    ) -> Profile: ...


class ProfileRegionResolver(Protocol):
    async def lock_profile_region(self, country_code: str, city_slug: str) -> ProfileRegion: ...


def _invalid_profile() -> ApiError:
    return ApiError(code="invalid_profile", message_key="errors.invalid_profile", status_code=422)


class ProfileService:
    def __init__(
        self,
        repository: ProfileRepositoryProtocol,
        regions: ProfileRegionResolver,
        *,
        current_organizer_rules_version: str,
        current_community_rules_version: str,
    ) -> None:
        self._repository = repository
        self._regions = regions
        self._organizer_rules = current_organizer_rules_version
        self._community_rules = current_community_rules_version

    async def get(self, principal: AuthPrincipal) -> Profile | None:
        return await self._repository.get(principal.user_id)

    async def replace(
        self, user_id: UUID, replacement_value: ProfileReplacement, *, now: datetime | None = None
    ) -> Profile:
        try:
            username = normalize_username(replacement_value.username)
        except ApiError:
            raise _invalid_profile() from None
        display_name = replacement_value.display_name.strip()
        if not 1 <= len(display_name) <= 80:
            raise _invalid_profile()
        country_code = replacement_value.country_code.strip().upper()
        city_slug = replacement_value.city_slug.strip().lower()
        currency = replacement_value.preferred_currency.strip().upper()
        try:
            region = await self._regions.lock_profile_region(country_code, city_slug)
        except ApiError:
            raise _invalid_profile() from None
        if (
            replacement_value.locale not in region.supported_locales
            or replacement_value.time_zone != region.time_zone
            or currency != region.default_currency
            or replacement_value.organizer_rules_version != self._organizer_rules
            or replacement_value.community_rules_version != self._community_rules
        ):
            raise _invalid_profile()
        normalized = replace(
            replacement_value,
            username=username,
            display_name=display_name,
            country_code=country_code,
            city_slug=city_slug,
            preferred_currency=currency,
        )
        return await self._repository.replace(user_id, normalized, now or datetime.now(UTC))
