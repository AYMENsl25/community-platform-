from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.audit import AuditRepository, AuditService
from talaqi.identity.dependencies import CsrfProtection, CurrentPrincipal, DatabaseSession
from talaqi.platform import IdempotencyCoordinator, IdempotencyRepository, hash_request_body
from talaqi.platform.errors import ErrorEnvelope, request_id_for
from talaqi.runtime import LazySessionFactory
from talaqi.settings.models import FeatureFlag, PlatformSetting
from talaqi.settings.repository import PlatformSettingsRepository
from talaqi.settings.schemas import (
    FeatureFlagChangeRequest,
    FeatureFlagPageResponse,
    FeatureFlagPreviewResponse,
    FeatureFlagResponse,
    FeatureFlagUpdateResponse,
)
from talaqi.settings.service import PlatformSettingsService

router = APIRouter(prefix="/api/v1/admin/settings", tags=["settings"])

_AUTH: dict[str, Any] = {"model": ErrorEnvelope, "description": "Authentication required."}
_FORBIDDEN: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Platform-admin access, MFA, or CSRF denied.",
}
_NOT_FOUND: dict[str, Any] = {"model": ErrorEnvelope, "description": "Setting not found."}
_CONFLICT: dict[str, Any] = {"model": ErrorEnvelope, "description": "Revision conflicted."}

IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=16, max_length=200),
]


def _service(session: AsyncSession) -> PlatformSettingsService:
    return PlatformSettingsService(
        PlatformSettingsRepository(session),
        AuditService(AuditRepository(session)),
    )


def _response(value: PlatformSetting) -> FeatureFlagResponse:
    return FeatureFlagResponse(key=value.key, enabled=value.enabled, revision=value.revision)


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie"


@router.get(
    "/feature-flags",
    response_model=FeatureFlagPageResponse,
    operation_id="listFeatureFlags",
    responses={401: _AUTH, 403: _FORBIDDEN},
)
async def list_feature_flags(
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> FeatureFlagPageResponse:
    _private(response)
    values = await _service(session).list_flags(principal)
    return FeatureFlagPageResponse(items=[_response(value) for value in values])


@router.post(
    "/feature-flags/{key}/preview",
    response_model=FeatureFlagPreviewResponse,
    operation_id="previewFeatureFlag",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def preview_feature_flag(
    key: FeatureFlag,
    body: FeatureFlagChangeRequest,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> FeatureFlagPreviewResponse:
    _private(response)
    current, proposed = await _service(session).preview(
        principal,
        key,
        enabled=body.enabled,
        revision=body.revision,
    )
    return FeatureFlagPreviewResponse(
        current=_response(current),
        proposed=_response(proposed),
        changed=current.enabled != proposed.enabled,
    )


@router.patch(
    "/feature-flags/{key}",
    response_model=FeatureFlagUpdateResponse,
    operation_id="updateFeatureFlag",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def update_feature_flag(
    key: FeatureFlag,
    body: FeatureFlagChangeRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
    idempotency_key: IdempotencyKey,
) -> FeatureFlagUpdateResponse:
    _private(response)
    current = datetime.now(UTC)
    runtime: LazySessionFactory = request.app.state.database_runtime
    idempotency = IdempotencyRepository(runtime.resolve())
    acquisition = await IdempotencyCoordinator(idempotency).acquire(
        actor_id=principal.user_id,
        http_method="PATCH",
        route_fingerprint=f"/api/v1/admin/settings/feature-flags/{key}",
        key=idempotency_key,
        request_hash=hash_request_body(await request.body()),
        now=current,
        lease_duration=timedelta(seconds=30),
        expires_at=current + timedelta(hours=24),
        session=session,
    )
    if acquisition.outcome == "replay":
        return FeatureFlagUpdateResponse.model_validate(acquisition.response_body)
    if acquisition.claim is None:
        raise RuntimeError("acquired feature flag operation has no claim")
    updated = await _service(session).update(
        principal,
        key,
        enabled=body.enabled,
        revision=body.revision,
        reason=body.reason,
        request_id=UUID(request_id_for(request)),
    )
    result = FeatureFlagUpdateResponse(setting=_response(updated))
    await idempotency.complete(
        acquisition.claim,
        response_status=200,
        response_body=result.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
        session=session,
    )
    return result


__all__ = ["router"]
