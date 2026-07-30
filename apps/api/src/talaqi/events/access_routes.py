from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Request, Response, status

from talaqi.events.access_rate_limits import LazyEventAccessRateLimiter
from talaqi.events.access_runtime import build_event_access_service
from talaqi.events.access_schemas import (
    EventAudienceResponse,
    PrivateLinkCreateRequest,
    PrivateLinkIssuedResponse,
    PrivateLinkResolveRequest,
)
from talaqi.identity.dependencies import (
    CsrfProtection,
    CurrentPrincipal,
    DatabaseSession,
    build_auth_service,
)
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.platform.errors import ErrorEnvelope, request_id_for

router = APIRouter(prefix="/api/v1", tags=["event access"])

_AUTH: dict[str, Any] = {"model": ErrorEnvelope, "description": "Authentication required."}
_FORBIDDEN: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Capability, object authorization, or CSRF denied.",
}
_NOT_FOUND: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Private event access is unavailable.",
}
_CONFLICT: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Private-link state conflicts with the request.",
}
_RATE_LIMITED: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Private-link resolution rate limit exceeded.",
}


async def _optional_principal(request: Request, session: DatabaseSession) -> AuthPrincipal | None:
    if request.cookies.get("talaqi_access") is None:
        return None
    try:
        return await build_auth_service(request, session).require_user(request)
    except ApiError as error:
        if error.status_code == 401:
            return None
        raise


OptionalPrincipal = Annotated[AuthPrincipal | None, Depends(_optional_principal)]


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Vary"] = "Cookie, Authorization"


def _raw_token(
    authorization: str | None,
    body: PrivateLinkResolveRequest | None,
) -> str:
    header_value = None
    if authorization is not None:
        scheme, separator, value = authorization.partition(" ")
        if separator and scheme.lower() == "privatelink":
            header_value = value
    body_value = body.private_link.get_secret_value() if body and body.private_link else None
    if header_value and body_value and header_value != body_value:
        raise ApiError(code="not_found", message_key="errors.not_found", status_code=404)
    value = header_value or body_value
    if value is None:
        raise ApiError(code="not_found", message_key="errors.not_found", status_code=404)
    return value


def _issued(
    event_id: UUID,
    raw_token: str,
    expires_at: datetime,
) -> PrivateLinkIssuedResponse:
    return PrivateLinkIssuedResponse(
        event_id=event_id,
        copy_value=raw_token,
        expires_at=expires_at,
    )


@router.post(
    "/events/{event_id:uuid}/private-link",
    response_model=PrivateLinkIssuedResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createEventPrivateLink",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def create_private_link(
    event_id: UUID,
    body: PrivateLinkCreateRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> PrivateLinkIssuedResponse:
    _private(response)
    raw_token, expires_at = await build_event_access_service(request, session).issue(
        principal,
        event_id,
        expires_in_days=body.expires_in_days,
        rotate=False,
        request_id=UUID(request_id_for(request)),
    )
    return _issued(event_id, raw_token, expires_at)


@router.post(
    "/events/{event_id:uuid}/private-link/rotate",
    response_model=PrivateLinkIssuedResponse,
    operation_id="rotateEventPrivateLink",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def rotate_private_link(
    event_id: UUID,
    body: PrivateLinkCreateRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> PrivateLinkIssuedResponse:
    _private(response)
    raw_token, expires_at = await build_event_access_service(request, session).issue(
        principal,
        event_id,
        expires_in_days=body.expires_in_days,
        rotate=True,
        request_id=UUID(request_id_for(request)),
    )
    return _issued(event_id, raw_token, expires_at)


@router.delete(
    "/events/{event_id:uuid}/private-link",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="revokeEventPrivateLink",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND},
)
async def revoke_private_link(
    event_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> None:
    _private(response)
    await build_event_access_service(request, session).revoke(
        principal,
        event_id,
        request_id=UUID(request_id_for(request)),
    )


@router.post(
    "/event-access/resolve",
    response_model=EventAudienceResponse,
    operation_id="resolveEventPrivateLink",
    responses={404: _NOT_FOUND, 429: _RATE_LIMITED},
)
async def resolve_private_link(
    request: Request,
    response: Response,
    session: DatabaseSession,
    principal: OptionalPrincipal,
    body: Annotated[PrivateLinkResolveRequest | None, Body()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> EventAudienceResponse:
    _private(response)
    raw_token = _raw_token(authorization, body)
    limiter: LazyEventAccessRateLimiter = request.app.state.event_access_rate_limits
    await limiter.check(
        client_host=request.client.host if request.client else None,
        raw_token=raw_token,
    )
    projection = await build_event_access_service(request, session).resolve(
        raw_token, principal=principal
    )
    return EventAudienceResponse.model_validate(projection)


__all__ = ["router"]
