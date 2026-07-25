from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.audit import AuditRepository, AuditService
from talaqi.clubs.models import Club, ClubPatch, NewClub
from talaqi.clubs.repository import ClubRepository
from talaqi.clubs.schemas import ClubCreateRequest, ClubPatchRequest, ClubResponse
from talaqi.clubs.service import ClubService, missing_fields
from talaqi.config import Settings
from talaqi.identity.dependencies import CsrfProtection, CurrentPrincipal, DatabaseSession
from talaqi.platform import (
    IdempotencyCoordinator,
    IdempotencyRepository,
    hash_request_body,
)
from talaqi.platform.errors import ErrorEnvelope, request_id_for
from talaqi.profiles.eligibility import CreationEligibilityService
from talaqi.profiles.repository import ProfileRepository
from talaqi.regions.repository import RegionRepository
from talaqi.regions.service import RegionPolicyService
from talaqi.runtime import LazySessionFactory

router = APIRouter(prefix="/api/v1/clubs", tags=["clubs"])

_AUTH: dict[str, Any] = {"model": ErrorEnvelope, "description": "Authentication required."}
_FORBIDDEN: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Capability, object authorization, or CSRF denied.",
}
_NOT_FOUND: dict[str, Any] = {"model": ErrorEnvelope, "description": "Club not found."}
_CONFLICT: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Slug, revision, or idempotency conflict.",
}
_INVALID: dict[str, Any] = {"model": ErrorEnvelope, "description": "Club input was rejected."}

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=16,
        max_length=200,
        description="Stable key for retrying this club creation request.",
    ),
]


def _service(request: Request, session: AsyncSession) -> ClubService:
    settings: Settings = request.app.state.settings_factory()
    regions = RegionPolicyService(RegionRepository(session))
    eligibility = CreationEligibilityService(
        ProfileRepository(session),
        regions,
        current_terms_version=settings.current_terms_version,
        current_privacy_version=settings.current_privacy_version,
        current_organizer_rules_version=settings.current_organizer_rules_version,
        current_community_rules_version=settings.current_community_rules_version,
        admin_mfa_required=settings.admin_mfa_required,
    )
    return ClubService(
        ClubRepository(session),
        eligibility,
        AuditService(AuditRepository(session)),
    )


def _response(club: Club) -> ClubResponse:
    return ClubResponse(
        id=club.id,
        slug=club.slug,
        name=club.name,
        description=club.description,
        category_slug=club.category_slug,
        country_code=club.country_code,
        city_slug=club.city_slug,
        membership_policy=club.membership_policy,
        social_links=club.social_links,
        logo_media_id=club.logo_media_id,
        cover_media_id=club.cover_media_id,
        revision=club.revision,
        status=club.status,
        missing_fields=missing_fields(club),
        published_at=club.published_at,
        suspended_at=club.suspended_at,
        suspension_reason=club.suspension_reason,
        closed_at=club.closed_at,
        created_at=club.created_at,
        updated_at=club.updated_at,
    )


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie"


def _new_club(body: ClubCreateRequest) -> NewClub:
    return NewClub(
        slug=body.slug,
        name=body.name,
        description=body.description,
        category_slug=body.category_slug,
        country_code=body.country_code,
        city_slug=body.city_slug,
        membership_policy=body.membership_policy,
        social_links={key: str(value) for key, value in body.social_links.items()},
        logo_media_id=body.logo_media_id,
        cover_media_id=body.cover_media_id,
    )


def _patch(body: ClubPatchRequest) -> ClubPatch:
    social_links = (
        None
        if body.social_links is None
        else {key: str(value) for key, value in body.social_links.items()}
    )
    return ClubPatch(
        revision=body.revision,
        changed_fields=frozenset(body.model_fields_set - {"revision"}),
        slug=body.slug,
        name=body.name,
        description=body.description,
        category_slug=body.category_slug,
        country_code=body.country_code,
        city_slug=body.city_slug,
        membership_policy=body.membership_policy,
        social_links=social_links,
        logo_media_id=body.logo_media_id,
        cover_media_id=body.cover_media_id,
    )


@router.post(
    "",
    response_model=ClubResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createClub",
    responses={401: _AUTH, 403: _FORBIDDEN, 409: _CONFLICT, 422: _INVALID},
)
async def create_club(
    body: ClubCreateRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
    idempotency_key: IdempotencyKey,
) -> ClubResponse:
    _private(response)
    current = datetime.now(UTC)
    runtime: LazySessionFactory = request.app.state.database_runtime
    idempotency = IdempotencyRepository(runtime.resolve())
    acquisition = await IdempotencyCoordinator(idempotency).acquire(
        actor_id=principal.user_id,
        http_method="POST",
        route_fingerprint="/api/v1/clubs",
        key=idempotency_key,
        request_hash=hash_request_body(await request.body()),
        now=current,
        lease_duration=timedelta(seconds=30),
        expires_at=current + timedelta(hours=24),
        session=session,
    )
    if acquisition.outcome == "replay":
        return ClubResponse.model_validate(acquisition.response_body)
    if acquisition.claim is None:
        raise RuntimeError("acquired idempotency operation has no claim")

    result = _response(
        await _service(request, session).create(
            principal,
            _new_club(body),
            request_id=UUID(request_id_for(request)),
            now=current,
        )
    )
    await idempotency.complete(
        acquisition.claim,
        response_status=status.HTTP_201_CREATED,
        response_body=result.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
        session=session,
    )
    return result


@router.get(
    "/{club_id:uuid}",
    response_model=ClubResponse,
    operation_id="getManagedClub",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND},
)
async def get_managed_club(
    club_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> ClubResponse:
    _private(response)
    return _response(await _service(request, session).get(principal, club_id))


@router.patch(
    "/{club_id:uuid}",
    response_model=ClubResponse,
    operation_id="updateClub",
    responses={
        401: _AUTH,
        403: _FORBIDDEN,
        404: _NOT_FOUND,
        409: _CONFLICT,
        422: _INVALID,
    },
)
async def update_club(
    club_id: UUID,
    body: ClubPatchRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> ClubResponse:
    _private(response)
    return _response(
        await _service(request, session).update(
            principal,
            club_id,
            _patch(body),
            request_id=UUID(request_id_for(request)),
        )
    )


__all__ = ["router"]
