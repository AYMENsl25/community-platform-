from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.config import Settings
from talaqi.profiles.eligibility import (
    CreationEligibilityService,
    RegistrationEligibilityService,
)
from talaqi.profiles.repository import ProfileRepository
from talaqi.regions.repository import RegionRepository
from talaqi.regions.service import RegionPolicyService


def build_registration_eligibility_service(
    session: AsyncSession, settings: Settings
) -> RegistrationEligibilityService:
    repository = ProfileRepository(session)
    eligibility = CreationEligibilityService(
        repository,
        RegionPolicyService(RegionRepository(session)),
        current_terms_version=settings.current_terms_version,
        current_privacy_version=settings.current_privacy_version,
        current_organizer_rules_version=settings.current_organizer_rules_version,
        current_community_rules_version=settings.current_community_rules_version,
        admin_mfa_required=settings.admin_mfa_required,
    )
    return RegistrationEligibilityService(repository, eligibility)


__all__ = ["build_registration_eligibility_service"]
