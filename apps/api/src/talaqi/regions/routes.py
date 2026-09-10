from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.audit import AuditRepository, AuditService
from talaqi.identity.dependencies import CsrfProtection, CurrentPrincipal
from talaqi.platform import IdempotencyCoordinator, IdempotencyRepository, hash_request_body
from talaqi.platform.errors import ErrorEnvelope, request_id_for
from talaqi.regions.repository import RegionRepository
from talaqi.regions.schemas import (
    CategoryResponse,
    CityResponse,
    CountryResponse,
    RegionPolicyChangeRequest,
    RegionPolicyPreviewResponse,
    RegionPolicyResponse,
    RegionPolicyUpdateResponse,
)
from talaqi.regions.service import RegionPolicyService
from talaqi.runtime import LazySessionFactory, get_db_session

router = APIRouter(prefix="/api/v1", tags=["regions"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session, scope="function")]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=200)]


def _service(session: AsyncSession) -> RegionPolicyService:
    return RegionPolicyService(RegionRepository(session))


def _admin_service(session: AsyncSession) -> RegionPolicyService:
    return RegionPolicyService(RegionRepository(session), AuditService(AuditRepository(session)))


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie"


@router.get(
    "/countries",
    response_model=list[CountryResponse],
    operation_id="listCountries",
)
async def list_countries(session: DatabaseSession) -> list[CountryResponse]:
    countries = await _service(session).list_countries()
    return [CountryResponse.model_validate(country) for country in countries]


@router.get(
    "/cities",
    response_model=list[CityResponse],
    operation_id="listCities",
)
async def list_cities(
    session: DatabaseSession,
    country_code: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
) -> list[CityResponse]:
    cities = await _service(session).list_cities(country_code)
    return [CityResponse.model_validate(city) for city in cities]


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
    operation_id="listCategories",
)
async def list_categories(session: DatabaseSession) -> list[CategoryResponse]:
    categories = await _service(session).list_categories()
    return [CategoryResponse.model_validate(category) for category in categories]


@router.get(
    "/regions/{country_code}/policy",
    response_model=RegionPolicyResponse,
    operation_id="getRegionPolicy",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorEnvelope,
            "description": "The requested enabled region does not exist.",
        }
    },
)
async def get_region_policy(country_code: str, session: DatabaseSession) -> RegionPolicyResponse:
    policy = await _service(session).get(country_code)
    return RegionPolicyResponse.model_validate(policy)


@router.get(
    "/admin/regions/{country_code}/policy",
    response_model=RegionPolicyResponse,
    operation_id="getAdminRegionPolicy",
)
async def get_admin_region_policy(
    country_code: str,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> RegionPolicyResponse:
    _private(response)
    policy = await _admin_service(session).get_admin(principal, country_code)
    return RegionPolicyResponse.model_validate(policy)


@router.post(
    "/admin/regions/{country_code}/policy/preview",
    response_model=RegionPolicyPreviewResponse,
    operation_id="previewAdminRegionPolicy",
)
async def preview_admin_region_policy(
    country_code: str,
    body: RegionPolicyChangeRequest,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> RegionPolicyPreviewResponse:
    _private(response)
    current, proposed, changed = await _admin_service(session).preview_admin(
        principal, country_code, body
    )
    return RegionPolicyPreviewResponse(
        current=RegionPolicyResponse.model_validate(current),
        proposed=RegionPolicyResponse.model_validate(proposed),
        changed_fields=changed,
    )


@router.patch(
    "/admin/regions/{country_code}/policy",
    response_model=RegionPolicyUpdateResponse,
    operation_id="updateAdminRegionPolicy",
)
async def update_admin_region_policy(
    country_code: str,
    body: RegionPolicyChangeRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
    idempotency_key: IdempotencyKey,
) -> RegionPolicyUpdateResponse:
    _private(response)
    now = datetime.now(UTC)
    runtime: LazySessionFactory = request.app.state.database_runtime
    repository = IdempotencyRepository(runtime.resolve())
    acquisition = await IdempotencyCoordinator(repository).acquire(
        actor_id=principal.user_id,
        http_method="PATCH",
        route_fingerprint=f"/api/v1/admin/regions/{country_code.upper()}/policy",
        key=idempotency_key,
        request_hash=hash_request_body(await request.body()),
        now=now,
        lease_duration=timedelta(seconds=30),
        expires_at=now + timedelta(hours=24),
        session=session,
    )
    if acquisition.outcome == "replay":
        return RegionPolicyUpdateResponse.model_validate(acquisition.response_body)
    if acquisition.claim is None:
        raise RuntimeError("acquired regional policy operation has no claim")
    policy = await _admin_service(session).update_admin(
        principal, country_code, body, request_id=UUID(request_id_for(request))
    )
    result = RegionPolicyUpdateResponse(policy=RegionPolicyResponse.model_validate(policy))
    await repository.complete(
        acquisition.claim,
        response_status=200,
        response_body=result.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
        session=session,
    )
    return result
