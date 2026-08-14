from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.audit import AuditRepository, AuditService
from talaqi.identity.dependencies import CsrfProtection, CurrentPrincipal, DatabaseSession
from talaqi.moderation.rate_limits import LazyModerationRateLimiter
from talaqi.moderation.repository import ModerationRepository
from talaqi.moderation.schemas import ReportRequest, ReportResponse
from talaqi.moderation.service import ModerationService, emergency_notice
from talaqi.platform import IdempotencyCoordinator, IdempotencyRepository, hash_request_body
from talaqi.platform.errors import ErrorEnvelope, request_id_for
from talaqi.runtime import LazySessionFactory
from talaqi.settings.repository import PlatformSettingsRepository
from talaqi.settings.service import PlatformSettingsService

router = APIRouter(prefix="/api/v1", tags=["moderation"])

_AUTH: dict[str, Any] = {"model": ErrorEnvelope, "description": "Authentication required."}
_FORBIDDEN: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "CSRF protection denied the report.",
}

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=16,
        max_length=200,
        description="Stable key for retrying one report submission.",
    ),
]


def _service(session: AsyncSession) -> ModerationService:
    return ModerationService(
        ModerationRepository(session),
        AuditService(AuditRepository(session)),
        PlatformSettingsService(PlatformSettingsRepository(session)),
    )


@router.post(
    "/reports",
    response_model=ReportResponse,
    status_code=201,
    operation_id="submitReport",
    responses={401: _AUTH, 403: _FORBIDDEN},
)
async def submit_report(
    body: ReportRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
    idempotency_key: IdempotencyKey,
) -> ReportResponse:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie"
    current = datetime.now(UTC)
    runtime: LazySessionFactory = request.app.state.database_runtime
    idempotency = IdempotencyRepository(runtime.resolve())
    acquisition = await IdempotencyCoordinator(idempotency).acquire(
        actor_id=principal.user_id,
        http_method="POST",
        route_fingerprint="/api/v1/reports",
        key=idempotency_key,
        request_hash=hash_request_body(await request.body()),
        now=current,
        lease_duration=timedelta(seconds=30),
        expires_at=current + timedelta(hours=24),
        session=session,
    )
    if acquisition.outcome == "replay":
        return ReportResponse.model_validate(acquisition.response_body)
    if acquisition.claim is None:
        raise RuntimeError("acquired report idempotency operation has no claim")
    limiter: LazyModerationRateLimiter = request.app.state.moderation_rate_limits
    await limiter.check_report(
        reporter_id=str(principal.user_id),
        target_key=f"{body.target_type}:{body.target_id}",
    )
    case = await _service(session).submit_report(
        principal,
        target_type=body.target_type,
        target_id=body.target_id,
        category=body.category,
        description=body.description,
        source_path=body.source_path,
        request_id=request_id_for(request),
        now=current,
    )
    result = ReportResponse(
        id=case.id,
        status="open",
        priority=case.priority,
        emergency_notice=emergency_notice(case),
        created_at=case.created_at,
    )
    await idempotency.complete(
        acquisition.claim,
        response_status=201,
        response_body=result.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
        session=session,
    )
    return result


__all__ = ["router"]
