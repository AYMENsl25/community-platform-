from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.profiles.models import Profile, ProfileReplacement
from talaqi.profiles.service import ProfileService
from talaqi.regions.models import ProfileRegion

USER_ID = UUID("019b0000-0000-7000-8000-000000000101")
NOW = datetime(2026, 7, 16, tzinfo=UTC)


class FakeRepository:
    def __init__(self) -> None:
        self.profile: Profile | None = None
        self.replacement: ProfileReplacement | None = None

    async def get(self, user_id: UUID) -> Profile | None:
        assert user_id == USER_ID
        return self.profile

    async def replace(
        self, user_id: UUID, replacement: ProfileReplacement, completed_at: datetime
    ) -> Profile:
        assert user_id == USER_ID
        self.replacement = replacement
        self.profile = Profile.from_replacement(user_id, replacement, completed_at)
        return self.profile


class FakeRegions:
    def __init__(self) -> None:
        self.locked = False

    async def lock_profile_region(self, country_code: str, city_slug: str) -> ProfileRegion:
        self.locked = True
        assert (country_code, city_slug) == ("TR", "istanbul")
        return ProfileRegion(
            country_code="TR",
            city_slug="istanbul",
            supported_locales=("en", "tr"),
            default_currency="TRY",
            time_zone="Europe/Istanbul",
            club_limit=1,
            independent_event_limit=3,
        )


def replacement(**overrides: object) -> ProfileReplacement:
    values: dict[str, object] = {
        "username": " Member_25 ",
        "display_name": "  Talaqi Member  ",
        "country_code": "tr",
        "city_slug": "ISTANBUL",
        "locale": "tr",
        "time_zone": "Europe/Istanbul",
        "preferred_currency": "try",
        "notify_event_email": True,
        "notify_community_email": False,
        "organizer_rules_version": "2026-07-11",
        "community_rules_version": "2026-07-11",
    }
    values.update(overrides)
    return ProfileReplacement(**values)  # pyright: ignore[reportArgumentType]


@pytest.mark.asyncio
async def test_replace_normalizes_and_completes_current_valid_profile() -> None:
    repository = FakeRepository()
    regions = FakeRegions()
    service = ProfileService(
        repository,
        regions,
        current_organizer_rules_version="2026-07-11",
        current_community_rules_version="2026-07-11",
    )

    profile = await service.replace(USER_ID, replacement(), now=NOW)

    assert repository.replacement == replace(
        replacement(),
        username="member_25",
        display_name="Talaqi Member",
        country_code="TR",
        city_slug="istanbul",
        preferred_currency="TRY",
    )
    assert profile.profile_completed_at == NOW
    assert profile.notify_security_email is True
    assert profile.avatar is None
    assert regions.locked is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("locale", "fr"),
        ("time_zone", "Africa/Algiers"),
        ("preferred_currency", "DZD"),
        ("organizer_rules_version", "old"),
        ("community_rules_version", "old"),
    ],
)
async def test_replace_rejects_incompatible_region_or_stale_rules(field: str, value: str) -> None:
    service = ProfileService(
        FakeRepository(),
        FakeRegions(),
        current_organizer_rules_version="2026-07-11",
        current_community_rules_version="2026-07-11",
    )

    with pytest.raises(ApiError, match="invalid_profile"):
        await service.replace(USER_ID, replacement(**{field: value}), now=NOW)


@pytest.mark.asyncio
async def test_get_is_server_owned_and_returns_only_callers_profile() -> None:
    repository = FakeRepository()
    regions = FakeRegions()
    service = ProfileService(
        repository,
        regions,
        current_organizer_rules_version="2026-07-11",
        current_community_rules_version="2026-07-11",
    )
    principal = AuthPrincipal(USER_ID, UUID(int=2), True, "active", False)

    assert await service.get(principal) is None
