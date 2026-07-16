from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest
from talaqi.identity.models import AuthPrincipal
from talaqi.profiles.eligibility import CreationEligibilityService
from talaqi.profiles.models import EligibilityState, Profile
from talaqi.regions.models import ProfileRegion

USER_ID = UUID("019b0000-0000-7000-8000-000000000201")
NOW = datetime(2026, 7, 16, tzinfo=UTC)


def profile() -> Profile:
    return Profile(
        user_id=USER_ID,
        username="member",
        display_name="Member",
        country_code="TR",
        city_slug="istanbul",
        locale="tr",
        time_zone="Europe/Istanbul",
        preferred_currency="TRY",
        notify_security_email=True,
        notify_event_email=True,
        notify_community_email=True,
        organizer_rules_version="2026-07-11",
        community_rules_version="2026-07-11",
        profile_completed_at=NOW,
        avatar=None,
    )


def state(**overrides: object) -> EligibilityState:
    values: dict[str, object] = {
        "profile": profile(),
        "terms_version": "2026-07-11",
        "privacy_version": "2026-07-11",
        "organizer_rules_version": "2026-07-11",
        "community_rules_version": "2026-07-11",
        "owned_club_count": 0,
        "active_independent_event_count": 0,
        "has_active_mfa": False,
    }
    values.update(overrides)
    return EligibilityState(**values)  # pyright: ignore[reportArgumentType]


class FakeRepository:
    def __init__(self, value: EligibilityState) -> None:
        self.value = value

    async def eligibility_state(self, user_id: UUID) -> EligibilityState:
        assert user_id == USER_ID
        return self.value


class FakeRegions:
    def __init__(
        self,
        value: ProfileRegion | Exception | None = None,
    ) -> None:
        self.value = value or ProfileRegion(
            country_code="TR",
            city_slug="istanbul",
            supported_locales=("en", "tr"),
            default_currency="TRY",
            time_zone="Europe/Istanbul",
            club_limit=1,
            independent_event_limit=3,
        )
        self.calls: list[tuple[str, str]] = []

    async def resolve_profile_region(self, country_code: str, city_slug: str) -> ProfileRegion:
        self.calls.append((country_code, city_slug))
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


@pytest.mark.asyncio
async def test_unverified_incomplete_member_has_exact_restricted_capabilities() -> None:
    principal = AuthPrincipal(USER_ID, UUID(int=3), False, "active", False)
    service = CreationEligibilityService(
        FakeRepository(state(profile=None)),
        FakeRegions(),
        current_terms_version="2026-07-11",
        current_privacy_version="2026-07-11",
        current_organizer_rules_version="2026-07-11",
        current_community_rules_version="2026-07-11",
        admin_mfa_required=True,
    )

    capabilities = await service.evaluate(principal)

    assert capabilities.create_club is False
    assert capabilities.create_independent_event is False
    assert capabilities.save_event is False
    assert capabilities.register_event is False
    assert capabilities.access_admin is False
    assert capabilities.blockers == ("email_verification_required", "profile_incomplete")


@pytest.mark.asyncio
async def test_verified_complete_member_is_automatically_eligible_until_limits() -> None:
    principal = AuthPrincipal(USER_ID, UUID(int=4), True, "active", False)
    service = CreationEligibilityService(
        FakeRepository(state()),
        FakeRegions(),
        current_terms_version="2026-07-11",
        current_privacy_version="2026-07-11",
        current_organizer_rules_version="2026-07-11",
        current_community_rules_version="2026-07-11",
        admin_mfa_required=True,
    )

    capabilities = await service.evaluate(principal)

    assert capabilities.model_dump() == {
        "create_club": True,
        "create_independent_event": True,
        "save_event": True,
        "register_event": True,
        "access_admin": False,
        "blockers": (),
    }


@pytest.mark.asyncio
async def test_limits_and_stale_rules_have_stable_sorted_blockers() -> None:
    principal = AuthPrincipal(USER_ID, UUID(int=5), True, "active", False)
    value = replace(
        state(),
        organizer_rules_version="old",
        owned_club_count=1,
        active_independent_event_count=3,
    )
    service = CreationEligibilityService(
        FakeRepository(value),
        FakeRegions(),
        current_terms_version="2026-07-11",
        current_privacy_version="2026-07-11",
        current_organizer_rules_version="2026-07-11",
        current_community_rules_version="2026-07-11",
        admin_mfa_required=False,
    )

    capabilities = await service.evaluate(principal)

    assert capabilities.blockers == (
        "rules_acceptance_required",
        "club_limit_reached",
        "independent_event_limit_reached",
    )
    assert not any(
        (
            capabilities.create_club,
            capabilities.create_independent_event,
            capabilities.save_event,
            capabilities.register_event,
        )
    )


@pytest.mark.asyncio
async def test_admin_mfa_blocker_applies_only_to_platform_admin() -> None:
    service = CreationEligibilityService(
        FakeRepository(state()),
        FakeRegions(),
        current_terms_version="2026-07-11",
        current_privacy_version="2026-07-11",
        current_organizer_rules_version="2026-07-11",
        current_community_rules_version="2026-07-11",
        admin_mfa_required=True,
    )
    member = await service.evaluate(AuthPrincipal(USER_ID, UUID(int=6), True, "active", False))
    admin = await service.evaluate(AuthPrincipal(USER_ID, UUID(int=7), True, "active", True))

    assert "admin_mfa_required" not in member.blockers
    assert member.access_admin is False
    assert admin.blockers == ("admin_mfa_required",)
    assert admin.access_admin is False

    service_with_mfa = CreationEligibilityService(
        FakeRepository(replace(state(), has_active_mfa=True)),
        FakeRegions(),
        current_terms_version="2026-07-11",
        current_privacy_version="2026-07-11",
        current_organizer_rules_version="2026-07-11",
        current_community_rules_version="2026-07-11",
        admin_mfa_required=True,
    )
    allowed = await service_with_mfa.evaluate(
        AuthPrincipal(USER_ID, UUID(int=8), True, "active", True)
    )
    assert allowed.access_admin is True


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["suspended", "deleted"])
async def test_unavailable_account_has_only_account_blocker(status: str) -> None:
    service = CreationEligibilityService(
        FakeRepository(state()),
        FakeRegions(),
        current_terms_version="2026-07-11",
        current_privacy_version="2026-07-11",
        current_organizer_rules_version="2026-07-11",
        current_community_rules_version="2026-07-11",
        admin_mfa_required=False,
    )

    capabilities = await service.evaluate(
        AuthPrincipal(
            USER_ID,
            UUID(int=9),
            True,
            status,  # pyright: ignore[reportArgumentType]
            True,
        )
    )

    assert capabilities.blockers == ("account_unavailable",)
    assert not any(
        (
            capabilities.create_club,
            capabilities.create_independent_event,
            capabilities.save_event,
            capabilities.register_event,
            capabilities.access_admin,
        )
    )


@pytest.mark.asyncio
async def test_admin_cannot_bypass_profile_and_verification_requirements() -> None:
    service = CreationEligibilityService(
        FakeRepository(state(profile=None, has_active_mfa=True)),
        FakeRegions(),
        current_terms_version="2026-07-11",
        current_privacy_version="2026-07-11",
        current_organizer_rules_version="2026-07-11",
        current_community_rules_version="2026-07-11",
        admin_mfa_required=True,
    )

    capabilities = await service.evaluate(
        AuthPrincipal(USER_ID, UUID(int=10), False, "active", True)
    )

    assert capabilities.access_admin is False
    assert capabilities.blockers == (
        "email_verification_required",
        "profile_incomplete",
    )


@pytest.mark.asyncio
async def test_current_region_resolver_is_authoritative_for_limits() -> None:
    principal = AuthPrincipal(USER_ID, UUID(int=11), True, "active", False)
    regions = FakeRegions(
        ProfileRegion(
            country_code="TR",
            city_slug="istanbul",
            supported_locales=("en", "tr"),
            default_currency="TRY",
            time_zone="Europe/Istanbul",
            club_limit=2,
            independent_event_limit=4,
        )
    )
    service = CreationEligibilityService(
        FakeRepository(
            state(
                owned_club_count=1,
                active_independent_event_count=3,
            )
        ),
        regions,
        current_terms_version="2026-07-11",
        current_privacy_version="2026-07-11",
        current_organizer_rules_version="2026-07-11",
        current_community_rules_version="2026-07-11",
        admin_mfa_required=False,
    )

    capabilities = await service.evaluate(principal)

    assert capabilities.blockers == ()
    assert capabilities.create_club is True
    assert capabilities.create_independent_event is True
    assert regions.calls == [("TR", "istanbul")]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("locale", "fr"),
        ("preferred_currency", "DZD"),
        ("time_zone", "Africa/Algiers"),
    ],
)
async def test_current_region_mismatch_fails_closed_without_limit_blockers(
    field: str,
    value: str,
) -> None:
    changed_profile = replace(profile(), **{field: value})
    service = CreationEligibilityService(
        FakeRepository(
            state(
                profile=changed_profile,
                owned_club_count=100,
                active_independent_event_count=100,
            )
        ),
        FakeRegions(),
        current_terms_version="2026-07-11",
        current_privacy_version="2026-07-11",
        current_organizer_rules_version="2026-07-11",
        current_community_rules_version="2026-07-11",
        admin_mfa_required=False,
    )

    capabilities = await service.evaluate(
        AuthPrincipal(USER_ID, UUID(int=12), True, "active", True)
    )

    assert capabilities.blockers == ("region_unavailable",)
    assert not any(
        (
            capabilities.create_club,
            capabilities.create_independent_event,
            capabilities.save_event,
            capabilities.register_event,
            capabilities.access_admin,
        )
    )


@pytest.mark.asyncio
async def test_region_resolution_failure_fails_closed_without_limit_blockers() -> None:
    region_error = RuntimeError("regional catalog unavailable")

    service = CreationEligibilityService(
        FakeRepository(
            state(
                owned_club_count=100,
                active_independent_event_count=100,
                has_active_mfa=True,
            )
        ),
        FakeRegions(region_error),
        current_terms_version="2026-07-11",
        current_privacy_version="2026-07-11",
        current_organizer_rules_version="2026-07-11",
        current_community_rules_version="2026-07-11",
        admin_mfa_required=True,
    )

    capabilities = await service.evaluate(
        AuthPrincipal(USER_ID, UUID(int=13), True, "active", True)
    )

    assert capabilities.blockers == ("region_unavailable",)
    assert not any(
        capabilities.model_dump().get(name)
        for name in (
            "create_club",
            "create_independent_event",
            "save_event",
            "register_event",
            "access_admin",
        )
    )
