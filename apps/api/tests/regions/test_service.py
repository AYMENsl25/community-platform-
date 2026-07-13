from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from talaqi.platform import ApiError
from talaqi.regions.models import DeadlineObligation, RegionPolicy
from talaqi.regions.service import RegionPolicyService


@pytest.mark.asyncio
async def test_launch_policies_are_seeded_with_approved_defaults(
    region_service: RegionPolicyService,
) -> None:
    turkey = await region_service.get("tr")
    algeria = await region_service.get("DZ")

    assert (turkey.default_locale, turkey.default_currency) == ("tr", "TRY")
    assert (turkey.cash_default_minutes, turkey.cash_bounds) == (1440, (120, 4320))
    assert (algeria.default_locale, algeria.default_currency) == ("fr", "DZD")
    assert (algeria.cash_default_minutes, algeria.cash_bounds) == (2880, (120, 10080))
    assert turkey.cancellation_bounds == algeria.cancellation_bounds == (0, 10080)
    assert turkey.club_limit == algeria.club_limit == 1
    assert turkey.independent_event_limit == algeria.independent_event_limit == 3


@pytest.mark.asyncio
async def test_unknown_and_disabled_regions_share_the_safe_not_found_contract(
    region_service: RegionPolicyService, region_session: AsyncSession
) -> None:
    with pytest.raises(ApiError) as unknown:
        await region_service.get("XX")

    await region_session.execute(
        text("UPDATE talaqi.countries SET enabled = false WHERE code = 'TR'")
    )
    with pytest.raises(ApiError) as disabled:
        await region_service.get("tr")

    for error in (unknown.value, disabled.value):
        assert (error.code, error.message_key, error.status_code) == (
            "region_not_found",
            "errors.region_not_found",
            404,
        )


def test_deadline_validation_rejects_invalid_bounds_and_event_overruns() -> None:
    start = datetime(2026, 8, 1, 12, tzinfo=UTC)
    valid = RegionPolicy(
        country_code="TR",
        default_locale="tr",
        default_currency="TRY",
        allowed_registration_methods=("free", "cash_organizer_confirmed"),
        cash_default_minutes=1440,
        cash_bounds=(120, 4320),
        cancellation_default_minutes=1440,
        cancellation_bounds=(0, 10080),
        club_limit=1,
        independent_event_limit=3,
        exact_venue_public_by_default=False,
        revision=1,
    )

    RegionPolicyService.validate_deadlines(
        valid,
        event_start=start,
        obligations=(
            DeadlineObligation(
                kind="cash",
                issued_at=start - timedelta(days=2),
                deadline=start - timedelta(days=1),
            ),
            DeadlineObligation(
                kind="cancellation",
                issued_at=start - timedelta(days=10),
                deadline=start - timedelta(days=1),
            ),
        ),
    )
    with pytest.raises(ValueError, match="bounds"):
        RegionPolicyService.validate_deadlines(
            replace(valid, cash_bounds=(4320, 120)),
            event_start=start,
        )
    with pytest.raises(ValueError, match="event start"):
        RegionPolicyService.validate_deadlines(
            valid,
            event_start=start,
            obligations=(
                DeadlineObligation(
                    kind="cash",
                    issued_at=start,
                    deadline=start + timedelta(seconds=1),
                ),
            ),
        )


def test_tighter_bounds_cannot_invalidate_active_obligations() -> None:
    start = datetime(2026, 8, 1, 12, tzinfo=UTC)
    policy = RegionPolicy(
        country_code="TR",
        default_locale="tr",
        default_currency="TRY",
        allowed_registration_methods=("free", "cash_organizer_confirmed"),
        cash_default_minutes=60,
        cash_bounds=(30, 60),
        cancellation_default_minutes=60,
        cancellation_bounds=(0, 60),
        club_limit=1,
        independent_event_limit=3,
        exact_venue_public_by_default=False,
        revision=2,
    )

    with pytest.raises(ValueError, match="cash obligation"):
        RegionPolicyService.validate_deadlines(
            policy,
            event_start=start,
            obligations=(
                DeadlineObligation(
                    kind="cash",
                    issued_at=start - timedelta(hours=4),
                    deadline=start - timedelta(hours=2),
                ),
            ),
        )
    with pytest.raises(ValueError, match="cancellation obligation"):
        RegionPolicyService.validate_deadlines(
            policy,
            event_start=start,
            obligations=(
                DeadlineObligation(
                    kind="cancellation",
                    issued_at=start - timedelta(days=1),
                    deadline=start - timedelta(hours=2),
                ),
            ),
        )


def test_obligations_reject_negative_fractional_and_unsupported_durations() -> None:
    start = datetime(2026, 8, 1, 12, tzinfo=UTC)
    policy = RegionPolicy(
        country_code="DZ",
        default_locale="fr",
        default_currency="DZD",
        allowed_registration_methods=("free",),
        cash_default_minutes=120,
        cash_bounds=(0, 10080),
        cancellation_default_minutes=120,
        cancellation_bounds=(0, 10080),
        club_limit=1,
        independent_event_limit=3,
        exact_venue_public_by_default=False,
        revision=1,
    )

    invalid = (
        (
            DeadlineObligation(kind="cash", issued_at=start, deadline=start - timedelta(minutes=1)),
            "negative",
        ),
        (
            DeadlineObligation(
                kind="cash",
                issued_at=start - timedelta(minutes=2),
                deadline=start - timedelta(seconds=1),
            ),
            "whole minutes",
        ),
        (
            DeadlineObligation(
                kind=cast(Any, "unsupported"),
                issued_at=start - timedelta(hours=1),
                deadline=start,
            ),
            "unsupported",
        ),
    )
    for obligation, message in invalid:
        with pytest.raises(ValueError, match=message):
            RegionPolicyService.validate_deadlines(
                policy, event_start=start, obligations=(obligation,)
            )


def test_deadline_validation_rejects_naive_timestamps() -> None:
    policy = RegionPolicy(
        country_code="DZ",
        default_locale="fr",
        default_currency="DZD",
        allowed_registration_methods=("free",),
        cash_default_minutes=2880,
        cash_bounds=(120, 10080),
        cancellation_default_minutes=1440,
        cancellation_bounds=(0, 10080),
        club_limit=1,
        independent_event_limit=3,
        exact_venue_public_by_default=False,
        revision=1,
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        RegionPolicyService.validate_deadlines(policy, event_start=datetime(2026, 8, 1))
    with pytest.raises(ValueError, match="timezone-aware"):
        RegionPolicyService.validate_deadlines(
            policy,
            event_start=datetime(2026, 8, 1, tzinfo=UTC),
            obligations=(
                DeadlineObligation(
                    kind="cash",
                    issued_at=datetime(2026, 7, 31),
                    deadline=datetime(2026, 7, 31, 1, tzinfo=UTC),
                ),
            ),
        )
