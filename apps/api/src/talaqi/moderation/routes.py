from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.audit import AuditEvent, AuditRepository, AuditService
from talaqi.config import Settings
from talaqi.identity.dependencies import CsrfProtection, CurrentPrincipal, DatabaseSession
from talaqi.moderation.models import (
    CaseStatus,
    ModerationAction,
    ModerationCase,
    ModerationCaseEvent,
    ModerationTarget,
    Priority,
    TargetType,
)
from talaqi.moderation.repository import ModerationRepository
from talaqi.moderation.schemas import (
    ActionRequest,
    ActionResponse,
    AuditPageResponse,
    AuditResponse,
    CaseDetailResponse,
    CaseEventResponse,
    CasePageResponse,
    CaseResponse,
    TargetPageResponse,
    TargetResponse,
)
from talaqi.moderation.service import ModerationService, capabilities, emergency_notice
from talaqi.platform import (
    ApiError,
    CursorCodec,
    IdempotencyCoordinator,
    IdempotencyRepository,
    hash_request_body,
)
from talaqi.platform.errors import ErrorEnvelope, request_id_for
from talaqi.runtime import LazySessionFactory

router = APIRouter(prefix="/api/v1/admin", tags=["moderation"])

_AUTH: dict[str, Any] = {"model": ErrorEnvelope, "description": "Authentication required."}
_FORBIDDEN: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Platform-admin access, MFA, or CSRF denied.",
}
_NOT_FOUND: dict[str, Any] = {"model": ErrorEnvelope, "description": "Case or target not found."}
_CONFLICT: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Moderation transition conflicted.",
}

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=16,
        max_length=200,
        description="Stable key for retrying a moderation action.",
    ),
]


def _service(session: AsyncSession) -> ModerationService:
    return ModerationService(ModerationRepository(session), AuditService(AuditRepository(session)))


def _codec(request: Request) -> CursorCodec:
    settings: Settings = request.app.state.settings_factory()
    secret = hashlib.sha256(settings.session_secret.get_secret_value().encode()).digest()
    return CursorCodec(secret)


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie"


def _case_cursor_ordering(value: ModerationCase) -> str:
    created_at = value.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return f"{value.priority}|{created_at}"


def _case_cursor_position(request: Request, cursor: str) -> tuple[Priority, datetime, UUID]:
    try:
        position = _codec(request).decode(cursor)
        if not isinstance(position.ordering, str):
            raise ValueError
        raw_priority, raw_created_at = position.ordering.split("|", maxsplit=1)
        if raw_priority not in {"standard", "high", "emergency"}:
            raise ValueError
        if not raw_created_at.endswith("Z"):
            raise ValueError
        created_at = datetime.fromisoformat(raw_created_at.removesuffix("Z") + "+00:00")
        return cast(Priority, raw_priority), created_at, position.tie_breaker
    except (TypeError, ValueError):
        raise ApiError(
            code="invalid_cursor",
            message_key="errors.invalid_cursor",
            status_code=400,
        ) from None


def _target(value: ModerationTarget) -> TargetResponse:
    return TargetResponse(
        type=value.type,
        id=value.id,
        label=value.label,
        secondary_label=value.secondary_label,
        status=value.status,
    )


def _case(
    value: ModerationCase,
    target: ModerationTarget,
    actions: tuple[ModerationAction, ...],
) -> CaseResponse:
    return CaseResponse(
        id=value.id,
        category=value.category,
        status=value.status,
        priority=value.priority,
        assigned_admin_user_id=value.assigned_admin_user_id,
        resolution_reason=value.resolution_reason,
        acknowledged_at=value.acknowledged_at,
        resolved_at=value.resolved_at,
        created_at=value.created_at,
        updated_at=value.updated_at,
        emergency_notice=emergency_notice(value),
        target=_target(target),
        available_actions=list(actions),
    )


def _event(value: ModerationCaseEvent) -> CaseEventResponse:
    return CaseEventResponse(
        id=value.id,
        actor_user_id=value.actor_user_id,
        action=value.action,
        from_status=value.from_status,
        to_status=value.to_status,
        reason=value.reason,
        created_at=value.created_at,
    )


def _audit(value: AuditEvent) -> AuditResponse:
    return AuditResponse(
        id=value.id,
        actor_user_id=value.actor_user_id,
        actor_kind=value.actor_kind,
        action=value.action,
        target_type=value.target_type,
        target_id=value.target_id,
        reason=value.reason,
        safe_before=dict(value.safe_before) if value.safe_before is not None else None,
        safe_after=dict(value.safe_after) if value.safe_after is not None else None,
        request_id=value.request_id,
        created_at=value.created_at,
    )


@router.get(
    "/moderation/cases",
    response_model=CasePageResponse,
    operation_id="listModerationCases",
    responses={401: _AUTH, 403: _FORBIDDEN},
)
async def list_cases(
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    status: Annotated[CaseStatus | None, Query()] = None,
    priority: Annotated[Priority | None, Query()] = None,
    target_type: Annotated[TargetType | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=2_048)] = None,
) -> CasePageResponse:
    _private(response)
    after_priority = None
    after_created_at = None
    after_id = None
    if cursor is not None:
        after_priority, after_created_at, after_id = _case_cursor_position(request, cursor)
    views = await _service(session).list_cases(
        principal,
        status=status,
        priority=priority,
        target_type=target_type,
        limit=limit + 1,
        after_priority=after_priority,
        after_created_at=after_created_at,
        after_id=after_id,
    )
    visible = views[:limit]
    next_cursor = None
    if len(views) > limit and visible:
        last = visible[-1][0]
        next_cursor = _codec(request).encode(
            ordering=_case_cursor_ordering(last), tie_breaker=last.id
        )
    return CasePageResponse(
        items=[_case(case, target, actions) for case, target, actions in visible],
        next_cursor=next_cursor,
    )


@router.get(
    "/moderation/cases/{case_id:uuid}",
    response_model=CaseDetailResponse,
    operation_id="getModerationCase",
    responses={401: _AUTH, 403: _FORBIDDEN, 404: _NOT_FOUND},
)
async def get_case(
    case_id: UUID,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> CaseDetailResponse:
    _private(response)
    case, target, events, actions = await _service(session).get_detail(principal, case_id)
    return CaseDetailResponse(
        case=_case(case, target, actions), events=[_event(item) for item in events]
    )


@router.get(
    "/moderation/targets",
    response_model=TargetPageResponse,
    operation_id="searchModerationTargets",
    responses={401: _AUTH, 403: _FORBIDDEN},
)
async def search_targets(
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    target_type: Annotated[TargetType, Query()],
    query: Annotated[str, Query(min_length=2, max_length=120)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> TargetPageResponse:
    _private(response)
    values = await _service(session).search_targets(principal, target_type, query, limit=limit)
    return TargetPageResponse(items=[_target(item) for item in values], next_cursor=None)


@router.get(
    "/audit-events",
    response_model=AuditPageResponse,
    operation_id="listAdminAuditEvents",
    responses={401: _AUTH, 403: _FORBIDDEN},
)
async def list_audit_events(
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    target_type: Annotated[str | None, Query(pattern=r"^[a-z0-9_]+$")] = None,
    target_id: Annotated[UUID | None, Query()] = None,
    actor_user_id: Annotated[UUID | None, Query()] = None,
    action: Annotated[str | None, Query(pattern=r"^[a-z0-9_.]+$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=2_048)] = None,
) -> AuditPageResponse:
    _private(response)
    after_created_at = None
    after_id = None
    if cursor is not None:
        position = _codec(request).decode(cursor)
        if not isinstance(position.ordering, datetime):
            raise ValueError("audit cursor must contain a timestamp")
        after_created_at, after_id = position.ordering, position.tie_breaker
    values = await _service(session).list_audit_events(
        principal,
        target_type=target_type,
        target_id=target_id,
        actor_user_id=actor_user_id,
        action=action,
        limit=limit + 1,
        after_created_at=after_created_at,
        after_id=after_id,
    )
    visible = values[:limit]
    next_cursor = None
    if len(values) > limit and visible:
        last = visible[-1]
        next_cursor = _codec(request).encode(ordering=last.created_at, tie_breaker=last.id)
    return AuditPageResponse(items=[_audit(item) for item in visible], next_cursor=next_cursor)


@router.post(
    "/moderation/cases/{case_id:uuid}/actions",
    response_model=ActionResponse,
    operation_id="performModerationAction",
    responses={
        401: _AUTH,
        403: _FORBIDDEN,
        404: _NOT_FOUND,
        409: _CONFLICT,
    },
)
async def perform_action(
    case_id: UUID,
    body: ActionRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
    idempotency_key: IdempotencyKey,
) -> ActionResponse:
    _private(response)
    current = datetime.now(UTC)
    runtime: LazySessionFactory = request.app.state.database_runtime
    idempotency = IdempotencyRepository(runtime.resolve())
    acquisition = await IdempotencyCoordinator(idempotency).acquire(
        actor_id=principal.user_id,
        http_method="POST",
        route_fingerprint=f"/api/v1/admin/moderation/cases/{case_id}/actions",
        key=idempotency_key,
        request_hash=hash_request_body(await request.body()),
        now=current,
        lease_duration=timedelta(seconds=30),
        expires_at=current + timedelta(hours=24),
        session=session,
    )
    if acquisition.outcome == "replay":
        return ActionResponse.model_validate(acquisition.response_body)
    if acquisition.claim is None:
        raise RuntimeError("acquired moderation idempotency operation has no claim")
    case, target, events = await _service(session).act(
        principal,
        case_id,
        body.action,
        reason=body.reason,
        request_id=UUID(request_id_for(request)),
        now=current,
    )
    result = ActionResponse(
        action=body.action,
        case=_case(case, target, capabilities(target)),
        events=[_event(item) for item in events],
    )
    await idempotency.complete(
        acquisition.claim,
        response_status=200,
        response_body=result.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
        session=session,
    )
    return result


__all__ = ["router"]
