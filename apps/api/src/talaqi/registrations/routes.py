from __future__ import annotations

import hashlib
import re
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Header, Query, Request, Response, status

from talaqi.config import Settings
from talaqi.db.identifiers import generate_uuid7
from talaqi.events.access_rate_limits import LazyEventAccessRateLimiter
from talaqi.events.access_tokens import PrivateLinkTokenCodec
from talaqi.identity.dependencies import CsrfProtection, CurrentPrincipal, DatabaseSession
from talaqi.platform import (
    CursorCodec,
    IdempotencyCoordinator,
    IdempotencyRepository,
    hash_request_body,
)
from talaqi.platform.errors import ApiError, ErrorEnvelope, request_id_for
from talaqi.registrations.models import Attendee, RegistrationState
from talaqi.registrations.runtime import (
    build_attendee_service,
    build_cancellation_service,
    build_cash_confirmation_service,
    build_registration_service,
)
from talaqi.registrations.schemas import (
    AttendeeExportRequest,
    AttendeeExportResponse,
    AttendeePageResponse,
    AttendeeResponse,
    AttendeeSummaryResponse,
    RegistrationCreateRequest,
    RegistrationResponse,
)
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
        description="Stable key for retrying a registration mutation.",
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


def _cancellation_hash(event_id: UUID) -> bytes:
    return hashlib.sha256(
        b"talaqi:event-registration-cancellation:v1\x00" + event_id.bytes
    ).digest()


def _confirmation_hash(event_id: UUID, registration_id: UUID) -> bytes:
    return hashlib.sha256(
        b"talaqi:cash-confirmation:v1\x00" + event_id.bytes + registration_id.bytes
    ).digest()


def _codec(request: Request) -> CursorCodec:
    secret = request.app.state.settings_factory().session_secret.get_secret_value().encode()
    return CursorCodec(hashlib.sha256(secret).digest())


def _attendee(value: Attendee) -> AttendeeResponse:
    registration = value.registration
    return AttendeeResponse(
        registration_id=registration.id,
        user_id=registration.user_id,
        username=value.username,
        display_name=value.display_name,
        method=registration.method,
        state=registration.state,
        waitlist_sequence=registration.waitlist_sequence,
        cash_expires_at=registration.cash_expires_at,
        confirmed_at=registration.confirmed_at,
        created_at=registration.created_at,
    )


def _attendee_fingerprint(state: RegistrationState | None, search: str | None) -> str:
    normalized = search.strip().casefold() if search is not None else ""
    return hashlib.sha256(f"{state or ''}\x00{normalized}".encode()).hexdigest()[:16]


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


@router.delete(
    "/{event_id:uuid}/registrations/me",
    response_model=RegistrationResponse,
    status_code=status.HTTP_200_OK,
    operation_id="cancelMyEventRegistration",
    responses={
        401: _AUTH,
        403: _FORBIDDEN,
        404: _NOT_FOUND,
        409: _CONFLICT,
    },
)
async def cancel_my_registration(
    event_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
    idempotency_key: IdempotencyKey,
) -> RegistrationResponse:
    _private(response)
    current = datetime.now(UTC)
    runtime: LazySessionFactory = request.app.state.database_runtime
    idempotency = IdempotencyRepository(runtime.resolve())
    acquisition = await IdempotencyCoordinator(idempotency).acquire(
        actor_id=principal.user_id,
        http_method="DELETE",
        route_fingerprint="/api/v1/events/{event_id}/registrations/me",
        key=idempotency_key,
        request_hash=_cancellation_hash(event_id),
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

    cancelled = await build_cancellation_service(request, session).cancel(
        principal,
        event_id,
        request_id=UUID(request_id_for(request)),
        now=current,
    )
    response_body = _response(cancelled)
    await idempotency.complete(
        acquisition.claim,
        response_status=status.HTTP_200_OK,
        response_body=response_body.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
        session=session,
    )
    return response_body


@router.post(
    "/{event_id:uuid}/registrations/{registration_id:uuid}/confirm-cash",
    response_model=RegistrationResponse,
    operation_id="confirmCashRegistration",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def confirm_cash_registration(
    event_id: UUID,
    registration_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
    idempotency_key: IdempotencyKey,
) -> RegistrationResponse:
    _private(response)
    current = datetime.now(UTC)
    runtime: LazySessionFactory = request.app.state.database_runtime
    idempotency = IdempotencyRepository(runtime.resolve())
    acquisition = await IdempotencyCoordinator(idempotency).acquire(
        actor_id=principal.user_id,
        http_method="POST",
        route_fingerprint="/api/v1/events/{event_id}/registrations/{registration_id}/confirm-cash",
        key=idempotency_key,
        request_hash=_confirmation_hash(event_id, registration_id),
        now=current,
        lease_duration=timedelta(seconds=30),
        expires_at=current + timedelta(hours=24),
        session=session,
    )
    if acquisition.outcome == "replay":
        return RegistrationResponse.model_validate(acquisition.response_body)
    if acquisition.claim is None:
        raise RuntimeError("acquired cash confirmation has no claim")
    confirmed = await build_cash_confirmation_service(request, session).confirm(
        principal,
        event_id,
        registration_id,
        request_id=UUID(request_id_for(request)),
        now=current,
    )
    result = _response(confirmed)
    await idempotency.complete(
        acquisition.claim,
        response_status=200,
        response_body=result.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
        session=session,
    )
    return result


@router.get(
    "/{event_id:uuid}/attendees",
    response_model=AttendeePageResponse,
    operation_id="listEventAttendees",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND},
)
async def list_event_attendees(
    event_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    state: Annotated[RegistrationState | None, Query()] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=2_048)] = None,
) -> AttendeePageResponse:
    _private(response)
    after_created_at = None
    after_id = None
    fingerprint = _attendee_fingerprint(state, search)
    if cursor is not None:
        try:
            position = _codec(request).decode(cursor)
            if not isinstance(position.ordering, str):
                raise ValueError
            encoded_fingerprint, encoded_time = position.ordering.split("|", 1)
            if encoded_fingerprint != fingerprint or not encoded_time.endswith("Z"):
                raise ValueError
            after_created_at = datetime.fromisoformat(encoded_time[:-1] + "+00:00")
            after_id = position.tie_breaker
        except (TypeError, ValueError):
            raise ApiError(
                code="invalid_cursor", message_key="errors.invalid_cursor", status_code=400
            ) from None
    attendees = await build_attendee_service(request, session).list(
        principal,
        event_id,
        state=state,
        search=search,
        limit=limit + 1,
        after_created_at=after_created_at,
        after_id=after_id,
    )
    visible = attendees[:limit]
    next_cursor = None
    if len(attendees) > limit and visible:
        last = visible[-1].registration
        instant = last.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
        next_cursor = _codec(request).encode(
            ordering=f"{fingerprint}|{instant}", tie_breaker=last.id
        )
    return AttendeePageResponse(
        items=[_attendee(item) for item in visible], next_cursor=next_cursor
    )


@router.get(
    "/{event_id:uuid}/attendees/summary",
    response_model=AttendeeSummaryResponse,
    operation_id="getEventAttendeeSummary",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND},
)
async def get_event_attendee_summary(
    event_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> AttendeeSummaryResponse:
    _private(response)
    summary = await build_attendee_service(request, session).summary(principal, event_id)
    return AttendeeSummaryResponse.model_validate(asdict(summary))


@router.post(
    "/{event_id:uuid}/attendees/export",
    response_model=AttendeeExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="requestEventAttendeeExport",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def request_event_attendee_export(
    event_id: UUID,
    body: AttendeeExportRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
    idempotency_key: IdempotencyKey,
) -> AttendeeExportResponse:
    _private(response)
    current = datetime.now(UTC)
    runtime: LazySessionFactory = request.app.state.database_runtime
    idempotency = IdempotencyRepository(runtime.resolve())
    acquisition = await IdempotencyCoordinator(idempotency).acquire(
        actor_id=principal.user_id,
        http_method="POST",
        route_fingerprint="/api/v1/events/{event_id}/attendees/export",
        key=idempotency_key,
        request_hash=hash_request_body(await request.body()),
        now=current,
        lease_duration=timedelta(seconds=30),
        expires_at=current + timedelta(hours=24),
        session=session,
    )
    if acquisition.outcome == "replay":
        return AttendeeExportResponse.model_validate(acquisition.response_body)
    if acquisition.claim is None:
        raise RuntimeError("acquired attendee export has no claim")
    export_request_id = generate_uuid7()
    await build_attendee_service(request, session).request_export(
        principal,
        event_id,
        export_request_id,
        state=body.state,
        search=body.search,
        request_id=UUID(request_id_for(request)),
        now=current,
    )
    result = AttendeeExportResponse(request_id=export_request_id, status="queued")
    await idempotency.complete(
        acquisition.claim,
        response_status=status.HTTP_202_ACCEPTED,
        response_body=result.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
        session=session,
    )
    return result


__all__ = ["router"]
