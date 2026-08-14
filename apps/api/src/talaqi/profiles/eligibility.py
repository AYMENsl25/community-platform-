from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from talaqi.identity.models import AuthPrincipal, UserStatus
from talaqi.profiles.models import EligibilityState, Profile
from talaqi.profiles.schemas import Capabilities
from talaqi.regions.models import ProfileRegion
from talaqi.settings.service import PlatformSettingsService

_LOGGER = logging.getLogger(__name__)

BLOCKER_ORDER = (
    "account_unavailable",
    "email_verification_required",
    "profile_incomplete",
    "rules_acceptance_required",
    "region_unavailable",
    "club_limit_reached",
    "independent_event_limit_reached",
    "independent_event_creation_disabled",
    "admin_mfa_required",
)


class EligibilityRepository(Protocol):
    async def eligibility_state(self, user_id: UUID) -> EligibilityState: ...


class CurrentProfileRegionResolver(Protocol):
    async def resolve_profile_region(
        self,
        country_code: str,
        city_slug: str,
    ) -> ProfileRegion: ...


class RegistrationPrincipalLocker(Protocol):
    async def lock_principal(self, principal: AuthPrincipal) -> AuthPrincipal: ...

    async def lock_registration_subject(
        self, user_id: UUID
    ) -> RegistrationEligibilitySubject | None: ...


class EligibilitySubject(Protocol):
    @property
    def user_id(self) -> UUID: ...

    @property
    def email_verified(self) -> bool: ...

    @property
    def status(self) -> UserStatus: ...

    @property
    def is_platform_admin(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class RegistrationEligibilitySubject:
    user_id: UUID
    email_verified: bool
    status: UserStatus
    is_platform_admin: bool


class CreationEligibilityService:
    def __init__(
        self,
        repository: EligibilityRepository,
        regions: CurrentProfileRegionResolver,
        *,
        current_terms_version: str,
        current_privacy_version: str,
        current_organizer_rules_version: str,
        current_community_rules_version: str,
        admin_mfa_required: bool,
        feature_flags: PlatformSettingsService | None = None,
    ) -> None:
        self._repository = repository
        self._regions = regions
        self._terms = current_terms_version
        self._privacy = current_privacy_version
        self._organizer = current_organizer_rules_version
        self._community = current_community_rules_version
        self._admin_mfa_required = admin_mfa_required
        self._feature_flags = feature_flags

    async def evaluate(self, principal: EligibilitySubject) -> Capabilities:
        state = await self._repository.eligibility_state(principal.user_id)
        blockers: set[str] = set()
        if principal.status != "active":
            blockers.add("account_unavailable")
        if not principal.email_verified:
            blockers.add("email_verification_required")
        profile_complete = (
            state.profile is not None and state.profile.profile_completed_at is not None
        )
        if not profile_complete:
            blockers.add("profile_incomplete")
        if profile_complete and (
            state.terms_version != self._terms
            or state.privacy_version != self._privacy
            or state.organizer_rules_version != self._organizer
            or state.community_rules_version != self._community
        ):
            blockers.add("rules_acceptance_required")

        current_region: ProfileRegion | None = None
        if profile_complete and state.profile is not None:
            try:
                candidate = await self._regions.resolve_profile_region(
                    state.profile.country_code,
                    state.profile.city_slug,
                )
            except Exception as error:  # Region resolution is fail-closed by contract.
                _LOGGER.warning(
                    "profile_region_resolution_failed error_type=%s",
                    type(error).__name__,
                )
            else:
                if _profile_matches_region(state.profile, candidate):
                    current_region = candidate
            if current_region is None:
                blockers.add("region_unavailable")

        core_blockers = blockers & {
            "account_unavailable",
            "email_verification_required",
            "profile_incomplete",
            "rules_acceptance_required",
            "region_unavailable",
        }
        core_allowed = not core_blockers
        club_limit_reached = (
            current_region is not None and state.owned_club_count >= current_region.club_limit
        )
        event_limit_reached = (
            current_region is not None
            and state.active_independent_event_count >= current_region.independent_event_limit
        )
        if club_limit_reached:
            blockers.add("club_limit_reached")
        if event_limit_reached:
            blockers.add("independent_event_limit_reached")
        independent_creation_enabled = (
            self._feature_flags is None
            or await self._feature_flags.enabled("features.independent_event_creation_enabled")
        )
        if not independent_creation_enabled:
            blockers.add("independent_event_creation_disabled")

        access_admin = core_allowed and principal.is_platform_admin
        if access_admin and self._admin_mfa_required and not state.has_active_mfa:
            blockers.add("admin_mfa_required")
            access_admin = False

        return Capabilities(
            create_club=core_allowed and not club_limit_reached,
            create_independent_event=(
                core_allowed and not event_limit_reached and independent_creation_enabled
            ),
            save_event=core_allowed,
            register_event=core_allowed,
            access_admin=access_admin,
            blockers=tuple(code for code in BLOCKER_ORDER if code in blockers),
        )


class RegistrationEligibilityService:
    """Public profiles-module boundary for a locked registration eligibility check."""

    def __init__(
        self,
        repository: RegistrationPrincipalLocker,
        eligibility: CreationEligibilityService,
    ) -> None:
        self._repository = repository
        self._eligibility = eligibility

    async def evaluate(self, principal: AuthPrincipal) -> Capabilities:
        current = await self._repository.lock_principal(principal)
        return await self._eligibility.evaluate(current)

    async def evaluate_user(self, user_id: UUID) -> Capabilities | None:
        current = await self._repository.lock_registration_subject(user_id)
        return None if current is None else await self._eligibility.evaluate(current)


def _profile_matches_region(profile: Profile, region: ProfileRegion) -> bool:
    return (
        profile.country_code == region.country_code
        and profile.city_slug == region.city_slug
        and profile.locale in region.supported_locales
        and profile.preferred_currency == region.default_currency
        and profile.time_zone == region.time_zone
    )
