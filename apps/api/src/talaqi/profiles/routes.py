from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.config import Settings
from talaqi.identity.dependencies import (
    CsrfProtection,
    CurrentPrincipal,
    DatabaseSession,
)
from talaqi.platform.errors import ErrorEnvelope
from talaqi.profiles.eligibility import CreationEligibilityService
from talaqi.profiles.models import Profile, ProfileReplacement
from talaqi.profiles.repository import ProfileRepository
from talaqi.profiles.schemas import Capabilities, ProfileReplacementRequest, ProfileResponse
from talaqi.profiles.service import ProfileService
from talaqi.regions.repository import RegionRepository
from talaqi.regions.service import RegionPolicyService
from talaqi.settings.repository import PlatformSettingsRepository
from talaqi.settings.service import PlatformSettingsService

router = APIRouter(prefix="/api/v1/me", tags=["profiles"])

_AUTH_FAILURE: dict[str, Any] = {"model": ErrorEnvelope, "description": "Authentication failed."}
_CSRF_FAILURE: dict[str, Any] = {"model": ErrorEnvelope, "description": "CSRF validation failed."}
_INPUT_FAILURE: dict[str, Any] = {"model": ErrorEnvelope, "description": "Input was rejected."}
_CONFLICT: dict[str, Any] = {"model": ErrorEnvelope, "description": "Username is unavailable."}


def _services(
    request: Request, session: AsyncSession
) -> tuple[ProfileService, CreationEligibilityService]:
    settings: Settings = request.app.state.settings_factory()
    repository = ProfileRepository(session)
    regions = RegionPolicyService(RegionRepository(session))
    profile_service = ProfileService(
        repository,
        regions,
        current_organizer_rules_version=settings.current_organizer_rules_version,
        current_community_rules_version=settings.current_community_rules_version,
    )
    eligibility = CreationEligibilityService(
        repository,
        regions,
        current_terms_version=settings.current_terms_version,
        current_privacy_version=settings.current_privacy_version,
        current_organizer_rules_version=settings.current_organizer_rules_version,
        current_community_rules_version=settings.current_community_rules_version,
        admin_mfa_required=settings.admin_mfa_required,
        feature_flags=PlatformSettingsService(PlatformSettingsRepository(session)),
    )
    return profile_service, eligibility


def _response(profile: Profile | None) -> ProfileResponse:
    if profile is None:
        return ProfileResponse(
            username=None,
            display_name=None,
            country_code=None,
            city_slug=None,
            locale=None,
            time_zone=None,
            preferred_currency=None,
            notify_security_email=True,
            notify_event_email=True,
            notify_community_email=True,
            organizer_rules_version=None,
            community_rules_version=None,
            profile_completed_at=None,
            avatar=None,
        )
    return ProfileResponse(
        username=profile.username,
        display_name=profile.display_name,
        country_code=profile.country_code,
        city_slug=profile.city_slug,
        locale=profile.locale,
        time_zone=profile.time_zone,
        preferred_currency=profile.preferred_currency,
        notify_security_email=True,
        notify_event_email=profile.notify_event_email,
        notify_community_email=profile.notify_community_email,
        organizer_rules_version=profile.organizer_rules_version,
        community_rules_version=profile.community_rules_version,
        profile_completed_at=profile.profile_completed_at,
        avatar=None,
    )


@router.get(
    "",
    response_model=ProfileResponse,
    operation_id="getMyProfile",
    responses={401: _AUTH_FAILURE},
)
async def get_my_profile(
    request: Request,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> ProfileResponse:
    profile_service, _eligibility = _services(request, session)
    return _response(await profile_service.get(principal))


@router.patch(
    "",
    response_model=ProfileResponse,
    operation_id="replaceMyProfile",
    responses={
        401: _AUTH_FAILURE,
        403: _CSRF_FAILURE,
        409: _CONFLICT,
        422: _INPUT_FAILURE,
    },
)
async def replace_my_profile(
    body: ProfileReplacementRequest,
    request: Request,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> ProfileResponse:
    profile_service, _eligibility = _services(request, session)
    replacement = ProfileReplacement(**body.model_dump())
    profile = await profile_service.replace(principal.user_id, replacement)
    return _response(profile)


@router.get(
    "/capabilities",
    response_model=Capabilities,
    operation_id="getMyCapabilities",
    responses={401: _AUTH_FAILURE},
)
async def get_my_capabilities(
    request: Request,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> Capabilities:
    _profile_service, eligibility = _services(request, session)
    return await eligibility.evaluate(principal)


__all__ = ["router"]
