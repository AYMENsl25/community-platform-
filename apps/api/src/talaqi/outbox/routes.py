from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, Response

from talaqi.audit import AuditRepository, AuditService
from talaqi.identity.dependencies import CsrfProtection, CurrentPrincipal, DatabaseSession
from talaqi.outbox.repository import OutboxRepository
from talaqi.outbox.schemas import (
    OperationalOutboxEventResponse,
    OperationalOutboxPageResponse,
    OutboxRetryRequest,
    OutboxRetryResponse,
)
from talaqi.outbox.service import OutboxOperationsService
from talaqi.platform import IdempotencyCoordinator, IdempotencyRepository, hash_request_body
from talaqi.platform.errors import request_id_for
from talaqi.runtime import LazySessionFactory

router = APIRouter(prefix="/api/v1/admin/outbox-events", tags=["outbox"])
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=200)]
OutboxStatus = Literal["pending", "processing", "retryable_failed", "permanent_failed", "delivered"]


def _service(session: DatabaseSession) -> OutboxOperationsService:
    return OutboxOperationsService(
        OutboxRepository(session), AuditService(AuditRepository(session))
    )


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie"


@router.get("", response_model=OperationalOutboxPageResponse, operation_id="listOutboxEvents")
async def list_outbox_events(
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    status: OutboxStatus | None = None,
    event_type: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> OperationalOutboxPageResponse:
    _private(response)
    events = await _service(session).list(
        principal, status=status, event_type=event_type, limit=limit
    )
    return OperationalOutboxPageResponse(
        items=[OperationalOutboxEventResponse.model_validate(event) for event in events]
    )


@router.get(
    "/{event_id}", response_model=OperationalOutboxEventResponse, operation_id="getOutboxEvent"
)
async def get_outbox_event(
    event_id: UUID, response: Response, principal: CurrentPrincipal, session: DatabaseSession
) -> OperationalOutboxEventResponse:
    _private(response)
    return OperationalOutboxEventResponse.model_validate(
        await _service(session).get(principal, event_id)
    )


@router.post(
    "/{event_id}/retry", response_model=OutboxRetryResponse, operation_id="retryOutboxEvent"
)
async def retry_outbox_event(
    event_id: UUID,
    body: OutboxRetryRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
    idempotency_key: IdempotencyKey,
) -> OutboxRetryResponse:
    _private(response)
    now = datetime.now(UTC)
    runtime: LazySessionFactory = request.app.state.database_runtime
    idempotency = IdempotencyRepository(runtime.resolve())
    acquisition = await IdempotencyCoordinator(idempotency).acquire(
        actor_id=principal.user_id,
        http_method="POST",
        route_fingerprint=f"/api/v1/admin/outbox-events/{event_id}/retry",
        key=idempotency_key,
        request_hash=hash_request_body(await request.body()),
        now=now,
        lease_duration=timedelta(seconds=30),
        expires_at=now + timedelta(hours=24),
        session=session,
    )
    if acquisition.outcome == "replay":
        return OutboxRetryResponse.model_validate(acquisition.response_body)
    if acquisition.claim is None:
        raise RuntimeError("acquired outbox retry has no claim")
    event = await _service(session).retry(
        principal, event_id, reason=body.reason, now=now, request_id=UUID(request_id_for(request))
    )
    result = OutboxRetryResponse(event=OperationalOutboxEventResponse.model_validate(event))
    await idempotency.complete(
        acquisition.claim,
        response_status=200,
        response_body=result.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
        session=session,
    )
    return result


__all__ = ["router"]
