from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID

from talaqi.audit import AuditService
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.regions.models import (
    Category,
    City,
    Country,
    DeadlineObligation,
    Locale,
    ProfileRegion,
    ProfileRegionSnapshot,
    RegionPolicy,
)
from talaqi.regions.repository import RegionRepository
from talaqi.regions.schemas import RegionPolicyChangeRequest
from talaqi.security import can_access_admin, can_moderate


class RegionPolicyService:
    def __init__(self, repository: RegionRepository, audit: AuditService | None = None) -> None:
        self._repository = repository
        self._audit = audit

    async def get(self, country_code: str) -> RegionPolicy:
        return await self._repository.get_policy(country_code)

    async def get_admin(self, principal: AuthPrincipal, country_code: str) -> RegionPolicy:
        can_access_admin(principal)
        return await self.get(country_code)

    async def preview_admin(
        self, principal: AuthPrincipal, country_code: str, change: RegionPolicyChangeRequest
    ) -> tuple[RegionPolicy, RegionPolicy, tuple[str, ...]]:
        await self._require_mfa_admin(principal)
        current = await self.get(country_code)
        return self._proposed(current, change)

    async def update_admin(
        self,
        principal: AuthPrincipal,
        country_code: str,
        change: RegionPolicyChangeRequest,
        *,
        request_id: UUID,
    ) -> RegionPolicy:
        await self._require_mfa_admin(principal)
        current = await self._repository.lock_policy(country_code)
        current, proposed, changed = self._proposed(current, change)
        if not changed:
            raise ApiError(code="no_changes", message_key="errors.validation", status_code=422)
        updated = await self._repository.update_safe_policy_controls(
            country_code,
            expected_revision=current.revision,
            club_limit=proposed.club_limit,
            independent_event_limit=proposed.independent_event_limit,
            exact_venue_public_by_default=proposed.exact_venue_public_by_default,
        )
        if updated is None:
            raise ApiError(code="stale_revision", message_key="errors.conflict", status_code=409)
        if self._audit is None:
            raise RuntimeError("regional policy updates require audit service")
        await self._audit.record(
            actor_user_id=principal.user_id,
            actor_kind="admin",
            action="regions.policy.update",
            target_type="regional_policy",
            target_id=None,
            reason=change.reason.strip(),
            safe_before={name: getattr(current, name) for name in changed}
            | {"country_code": current.country_code, "revision": current.revision},
            safe_after={name: getattr(updated, name) for name in changed}
            | {"country_code": updated.country_code, "revision": updated.revision},
            request_id=request_id,
        )
        return updated

    def _proposed(
        self, current: RegionPolicy, change: RegionPolicyChangeRequest
    ) -> tuple[RegionPolicy, RegionPolicy, tuple[str, ...]]:
        if len(change.reason.strip()) < 3:
            raise ApiError(code="invalid_reason", message_key="errors.validation", status_code=422)
        if current.revision != change.revision:
            raise ApiError(code="stale_revision", message_key="errors.conflict", status_code=409)
        values = {
            "club_limit": change.club_limit
            if change.club_limit is not None
            else current.club_limit,
            "independent_event_limit": change.independent_event_limit
            if change.independent_event_limit is not None
            else current.independent_event_limit,
            "exact_venue_public_by_default": change.exact_venue_public_by_default
            if change.exact_venue_public_by_default is not None
            else current.exact_venue_public_by_default,
        }
        changed = tuple(name for name, value in values.items() if value != getattr(current, name))
        proposed = replace(current, **values, revision=current.revision + bool(changed))
        return current, proposed, changed

    async def _require_mfa_admin(self, principal: AuthPrincipal) -> None:
        can_access_admin(principal)
        can_moderate(
            principal, has_active_mfa=await self._repository.has_active_mfa(principal.user_id)
        )

    async def list_countries(self) -> tuple[Country, ...]:
        return await self._repository.list_countries()

    async def list_cities(self, country_code: str | None = None) -> tuple[City, ...]:
        return await self._repository.list_cities(country_code)

    async def list_categories(self) -> tuple[Category, ...]:
        return await self._repository.list_categories()

    async def resolve_profile_region(self, country_code: str, city_slug: str) -> ProfileRegion:
        snapshot = await self._repository.get_profile_region(country_code, city_slug)
        return _validated_profile_region(snapshot)

    async def lock_profile_region(self, country_code: str, city_slug: str) -> ProfileRegion:
        """Resolve and lock profile region metadata until the request transaction ends."""

        snapshot = await self._repository.lock_profile_region(country_code, city_slug)
        return _validated_profile_region(snapshot)

    @staticmethod
    def validate_deadlines(
        policy: RegionPolicy,
        *,
        event_start: datetime,
        obligations: Iterable[DeadlineObligation] = (),
    ) -> None:
        if event_start.tzinfo is None or event_start.utcoffset() is None:
            raise ValueError("event start must be timezone-aware")
        for label, default, bounds in (
            ("cash", policy.cash_default_minutes, policy.cash_bounds),
            ("cancellation", policy.cancellation_default_minutes, policy.cancellation_bounds),
        ):
            lower, upper = bounds
            if lower < 0 or upper < 0 or lower > upper or not lower <= default <= upper:
                raise ValueError(f"{label} deadline bounds are invalid")
        for obligation in obligations:
            timestamps = (obligation.issued_at, obligation.deadline)
            if any(value.tzinfo is None or value.utcoffset() is None for value in timestamps):
                raise ValueError("active obligation timestamps must be timezone-aware")
            if obligation.issued_at > obligation.deadline:
                raise ValueError("active obligation duration cannot be negative")
            if obligation.deadline > event_start:
                raise ValueError("active obligation deadline cannot pass event start")
            if obligation.kind == "cash":
                duration = _whole_minutes(obligation.deadline - obligation.issued_at)
                if not policy.cash_bounds[0] <= duration <= policy.cash_bounds[1]:
                    raise ValueError("cash obligation falls outside proposed bounds")
            elif obligation.kind == "cancellation":
                duration = _whole_minutes(event_start - obligation.deadline)
                if not policy.cancellation_bounds[0] <= duration <= policy.cancellation_bounds[1]:
                    raise ValueError("cancellation obligation falls outside proposed bounds")
            else:
                raise ValueError("active obligation kind is unsupported")


def _whole_minutes(duration: timedelta) -> int:
    total_seconds = duration.total_seconds()
    if total_seconds < 0 or total_seconds % 60 != 0:
        raise ValueError("active obligation duration must be non-negative whole minutes")
    return int(total_seconds // 60)


_SUPPORTED_PROFILE_LOCALES: dict[str, tuple[Locale, ...]] = {
    "TR": ("en", "tr"),
    "DZ": ("en", "fr", "ar"),
}


def _validated_profile_region(snapshot: ProfileRegionSnapshot) -> ProfileRegion:
    if not snapshot.country_enabled or not snapshot.city_enabled or not snapshot.beta_enabled:
        raise ApiError(
            code="region_not_found",
            message_key="errors.region_not_found",
            status_code=404,
        )
    return ProfileRegion(
        country_code=snapshot.country_code,
        city_slug=snapshot.city_slug,
        supported_locales=_SUPPORTED_PROFILE_LOCALES.get(
            snapshot.country_code,
            (snapshot.default_locale,),
        ),
        default_currency=snapshot.default_currency,
        time_zone=snapshot.time_zone,
        club_limit=snapshot.club_limit,
        independent_event_limit=snapshot.independent_event_limit,
    )
