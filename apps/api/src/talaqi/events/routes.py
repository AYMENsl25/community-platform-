from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.audit import AuditRepository, AuditService
from talaqi.clubs.event_access import ClubEventAccessService
from talaqi.clubs.repository import ClubRepository
from talaqi.config import Settings
from talaqi.events.access_runtime import build_event_access_service
from talaqi.events.models import Event, EventPatch, NewEvent
from talaqi.events.repository import EventRepository
from talaqi.events.schemas import (
    EventCreateRequest,
    EventPatchRequest,
    EventRevisionRequest,
    ManagedEventPageResponse,
    ManagedEventResponse,
)
from talaqi.events.service import EventService
from talaqi.identity.dependencies import CsrfProtection, CurrentPrincipal, DatabaseSession
from talaqi.media.repository import MediaRepository
from talaqi.media.runtime import LazyMediaStorage
from talaqi.media.service import MediaService
from talaqi.platform import IdempotencyCoordinator, IdempotencyRepository, hash_request_body
from talaqi.platform.errors import ErrorEnvelope, request_id_for
from talaqi.profiles.eligibility import CreationEligibilityService
from talaqi.profiles.repository import ProfileRepository
from talaqi.regions.repository import RegionRepository
from talaqi.regions.service import RegionPolicyService
from talaqi.runtime import LazySessionFactory
from talaqi.settings.repository import PlatformSettingsRepository
from talaqi.settings.service import PlatformSettingsService

router = APIRouter(prefix="/api/v1/events", tags=["events"])

_AUTH: dict[str, Any] = {"model": ErrorEnvelope, "description": "Authentication required."}
_FORBIDDEN: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Capability, object authorization, or CSRF denied.",
}
_NOT_FOUND: dict[str, Any] = {"model": ErrorEnvelope, "description": "Event not found."}
_CONFLICT: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Revision, lifecycle, or idempotency conflict.",
}
_INVALID: dict[str, Any] = {"model": ErrorEnvelope, "description": "Event input rejected."}

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=16,
        max_length=200,
        description="Stable key for retrying event creation or duplication.",
    ),
]


def _service(request: Request, session: AsyncSession) -> EventService:
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
        feature_flags=PlatformSettingsService(PlatformSettingsRepository(session)),
    )
    storage_runtime: LazyMediaStorage = request.app.state.media_storage_runtime
    media = MediaService(
        MediaRepository(session),
        storage_runtime.resolve(),
        upload_grant_seconds=settings.media_upload_grant_seconds,
        max_image_pixels=settings.media_max_image_pixels,
    )
    return EventService(
        EventRepository(session),
        eligibility,
        regions,
        ClubEventAccessService(ClubRepository(session)),
        media,
        AuditService(AuditRepository(session)),
        PlatformSettingsService(PlatformSettingsRepository(session)),
    )


def _workspace_capabilities(event: Event) -> tuple[str, ...]:
    if event.status == "draft":
        return ("edit", "duplicate", "delete_draft", "preview")
    if event.status == "published":
        return ("edit", "duplicate", "cancel", "complete", "preview")
    if event.status in ("cancelled", "completed"):
        return ("duplicate", "preview")
    return ("preview",)


def _validation_blockers(event: Event) -> tuple[str, ...]:
    required = {
        "description": event.description.strip(),
        "category_slug": event.category_slug,
        "country_code": event.country_code,
        "city_slug": event.city_slug,
        "start_at": event.start_at,
        "end_at": event.end_at,
        "time_zone": event.time_zone,
        "registration_method": event.registration_method,
        "cancellation_cutoff_minutes": event.cancellation_cutoff_minutes,
    }
    blockers = [name for name, value in required.items() if value is None or value == ""]
    if event.start_at is not None and event.end_at is not None and event.end_at <= event.start_at:
        blockers.append("schedule")
    if (event.latitude is None) != (event.longitude is None):
        blockers.append("coordinates")
    return tuple(blockers)


def _response(event: Event) -> ManagedEventResponse:
    return ManagedEventResponse.model_validate(
        {
            **asdict(event),
            "capabilities": _workspace_capabilities(event),
            "validation_blockers": _validation_blockers(event),
        }
    )


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie"


def _new(body: EventCreateRequest) -> NewEvent:
    return NewEvent(**body.model_dump())


def _patch(body: EventPatchRequest) -> EventPatch:
    return EventPatch(
        revision=body.revision,
        changed_fields=frozenset(body.model_fields_set - {"revision"}),
        **body.model_dump(exclude={"revision"}),
    )


@router.get(
    "/managed",
    response_model=ManagedEventPageResponse,
    operation_id="listManagedEvents",
    responses={401: _AUTH},
)
async def list_managed_events(
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> ManagedEventPageResponse:
    _private(response)
    return ManagedEventPageResponse(
        items=[
            _response(event) for event in await _service(request, session).list_managed(principal)
        ]
    )


async def _acquire(
    request: Request,
    session: AsyncSession,
    *,
    actor_id: UUID,
    route_fingerprint: str,
    key: str,
    request_hash_override: bytes | None = None,
):
    current = datetime.now(UTC)
    runtime: LazySessionFactory = request.app.state.database_runtime
    repository = IdempotencyRepository(runtime.resolve())
    acquisition = await IdempotencyCoordinator(repository).acquire(
        actor_id=actor_id,
        http_method="POST",
        route_fingerprint=route_fingerprint,
        key=key,
        request_hash=request_hash_override or hash_request_body(await request.body()),
        now=current,
        lease_duration=timedelta(seconds=30),
        expires_at=current + timedelta(hours=24),
        session=session,
    )
    return repository, acquisition, current


@router.post(
    "",
    response_model=ManagedEventResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createEvent",
    responses={401: _AUTH, 403: _FORBIDDEN, 409: _CONFLICT, 422: _INVALID},
)
async def create_event(
    body: EventCreateRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
    idempotency_key: IdempotencyKey,
) -> ManagedEventResponse:
    _private(response)
    repository, acquisition, current = await _acquire(
        request,
        session,
        actor_id=principal.user_id,
        route_fingerprint="/api/v1/events",
        key=idempotency_key,
    )
    if acquisition.outcome == "replay":
        result = ManagedEventResponse.model_validate(acquisition.response_body)
        await _service(request, session).authorize_replay(principal, result.id)
        return result
    if acquisition.claim is None:
        raise RuntimeError("acquired idempotency operation has no claim")
    result = _response(
        await _service(request, session).create(
            principal,
            _new(body),
            request_id=UUID(request_id_for(request)),
            now=current,
        )
    )
    await repository.complete(
        acquisition.claim,
        response_status=status.HTTP_201_CREATED,
        response_body=result.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
        session=session,
    )
    return result


@router.get(
    "/{event_id:uuid}/managed",
    response_model=ManagedEventResponse,
    operation_id="getManagedEvent",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND},
)
async def get_managed_event(
    event_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> ManagedEventResponse:
    _private(response)
    event = await _service(request, session).get(principal, event_id)
    projection = await build_event_access_service(request, session).managed(principal, event)
    return _response(
        replace(
            event,
            exact_address=projection.exact_address,
            latitude=projection.latitude,
            longitude=projection.longitude,
        )
    )


@router.patch(
    "/{event_id:uuid}",
    response_model=ManagedEventResponse,
    operation_id="updateEvent",
    responses={
        401: _AUTH,
        403: _FORBIDDEN,
        404: _NOT_FOUND,
        409: _CONFLICT,
        422: _INVALID,
    },
)
async def update_event(
    event_id: UUID,
    body: EventPatchRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> ManagedEventResponse:
    _private(response)
    return _response(
        await _service(request, session).update(
            principal,
            event_id,
            _patch(body),
            request_id=UUID(request_id_for(request)),
        )
    )


@router.post(
    "/{event_id:uuid}/cancel",
    response_model=ManagedEventResponse,
    operation_id="cancelEvent",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def cancel_event(
    event_id: UUID,
    body: EventRevisionRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> ManagedEventResponse:
    _private(response)
    return _response(
        await _service(request, session).cancel(
            principal,
            event_id,
            revision=body.revision,
            request_id=UUID(request_id_for(request)),
        )
    )


@router.post(
    "/{event_id:uuid}/complete",
    response_model=ManagedEventResponse,
    operation_id="completeEvent",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def complete_event(
    event_id: UUID,
    body: EventRevisionRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> ManagedEventResponse:
    _private(response)
    return _response(
        await _service(request, session).complete(
            principal,
            event_id,
            revision=body.revision,
            request_id=UUID(request_id_for(request)),
        )
    )


@router.delete(
    "/{event_id:uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteDraftEvent",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def delete_draft_event(
    event_id: UUID,
    body: EventRevisionRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> None:
    _private(response)
    await _service(request, session).delete_draft(
        principal,
        event_id,
        revision=body.revision,
        request_id=UUID(request_id_for(request)),
    )


@router.post(
    "/{event_id:uuid}/duplicate",
    response_model=ManagedEventResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="duplicateEvent",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND, 409: _CONFLICT},
)
async def duplicate_event(
    event_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
    idempotency_key: IdempotencyKey,
) -> ManagedEventResponse:
    _private(response)
    repository, acquisition, current = await _acquire(
        request,
        session,
        actor_id=principal.user_id,
        route_fingerprint="/api/v1/events/{event_id}/duplicate",
        key=idempotency_key,
        request_hash_override=hash_request_body(str(event_id).encode("ascii")),
    )
    if acquisition.outcome == "replay":
        result = ManagedEventResponse.model_validate(acquisition.response_body)
        await _service(request, session).authorize_replay(principal, result.id)
        return result
    if acquisition.claim is None:
        raise RuntimeError("acquired idempotency operation has no claim")
    result = _response(
        await _service(request, session).duplicate(
            principal,
            event_id,
            request_id=UUID(request_id_for(request)),
            now=current,
        )
    )
    await repository.complete(
        acquisition.claim,
        response_status=status.HTTP_201_CREATED,
        response_body=result.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
        session=session,
    )
    return result


__all__ = ["router"]
