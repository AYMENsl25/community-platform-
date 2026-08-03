from __future__ import annotations

import hashlib
import re
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Header, Request, Response, status

from talaqi.config import Settings
from talaqi.events.access_rate_limits import LazyEventAccessRateLimiter
from talaqi.events.access_tokens import PrivateLinkTokenCodec
from talaqi.identity.dependencies import CsrfProtection, CurrentPrincipal, DatabaseSession
from talaqi.platform import IdempotencyCoordinator, IdempotencyRepository
from talaqi.platform.errors import ApiError, ErrorEnvelope, request_id_for
from talaqi.registrations.runtime import build_registration_service
from talaqi.registrations.schemas import RegistrationCreateRequest, RegistrationResponse
from talaqi.runtime import LazySessionFactory

router = APIRouter(prefix="/api/v1/events", tags=["registrations"])

_TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")
_AUTH: dict[str, Any] = {"model": ErrorEnvelope, "description": "Authentication required."}
_FORBIDDEN: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Registration eligibility or CSRF denied.",
}
_NOT_FOUND: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Event or private access is unavailable.",
}
_CONFLICT: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Registration deadline or idempotency conflict.",
}

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=16,
        max_length=200,
        description="Stable key for retrying event registration.",
    ),
]


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Vary"] = "Cookie, Authorization"


def _private_link(authorization: str | None, body: RegistrationCreateRequest | None) -> str | None:
    header_value = None
    if authorization is not None:
        scheme, separator, value = authorization.partition(" ")
        if separator and scheme.lower() == "privatelink":
            header_value = value
    body_value = body.private_link.get_secret_value() if body and body.private_link else None
    if header_value and body_value and header_value != body_value:
        raise ApiError(code="not_found", message_key="errors.not_found", status_code=404)
    selected = header_value or body_value
    if selected is not None and _TOKEN.fullmatch(selected) is None:
        raise ApiError(code="not_found", message_key="errors.not_found", status_code=404)
    return selected


def _response(result: object) -> RegistrationResponse:
    return RegistrationResponse.model_validate(asdict(result))  # type: ignore[arg-type]


def _request_hash(event_id: UUID, private_link_hash: bytes | None) -> bytes:
    visibility_proof = b"\x00" if private_link_hash is None else b"\x01" + private_link_hash
    return hashlib.sha256(
        b"talaqi:event-registration-request:v1\x00" + event_id.bytes + visibility_proof
    ).digest()


@router.post(
    "/{event_id:uuid}/registrations",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createEventRegistration",
    responses={
        200: {"model": RegistrationResponse, "description": "Existing active registration."},
        401: _AUTH,
        403: _FORBIDDEN,
        404: _NOT_FOUND,
        409: _CONFLICT,
    },
)
async def create_registration(
    event_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
    idempotency_key: IdempotencyKey,
    registration_request: Annotated[RegistrationCreateRequest | None, Body()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> RegistrationResponse:
    _private(response)
    raw_private_link = _private_link(authorization, registration_request)
    if raw_private_link is not None:
        limiter: LazyEventAccessRateLimiter = request.app.state.event_access_rate_limits
        await limiter.check(
            client_host=request.client.host if request.client else None,
            raw_token=raw_private_link,
        )

    settings: Settings = request.app.state.settings_factory()
    private_link_hash = (
        PrivateLinkTokenCodec(settings.session_secret.get_secret_value().encode("utf-8")).digest(
            raw_private_link
        )
        if raw_private_link is not None
        else None
    )

    current = datetime.now(UTC)
    runtime: LazySessionFactory = request.app.state.database_runtime
    idempotency = IdempotencyRepository(runtime.resolve())
    acquisition = await IdempotencyCoordinator(idempotency).acquire(
        actor_id=principal.user_id,
        http_method="POST",
        route_fingerprint="/api/v1/events/{event_id}/registrations",
        key=idempotency_key,
        request_hash=_request_hash(event_id, private_link_hash),
        now=current,
        lease_duration=timedelta(seconds=30),
        expires_at=current + timedelta(hours=24),
        session=session,
    )
    if acquisition.outcome == "replay":
        if acquisition.response_status is None:
            raise RuntimeError("completed idempotency operation has no response status")
        response.status_code = acquisition.response_status
        return RegistrationResponse.model_validate(acquisition.response_body)
    if acquisition.claim is None:
        raise RuntimeError("acquired idempotency operation has no claim")

    result = await build_registration_service(request, session).register(
        principal,
        event_id,
        private_link_hash=private_link_hash,
        request_id=UUID(request_id_for(request)),
        now=current,
    )
    response_body = _response(result.registration)
    response.status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    await idempotency.complete(
        acquisition.claim,
        response_status=response.status_code,
        response_body=response_body.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
        session=session,
    )
    return response_body


__all__ = ["router"]
