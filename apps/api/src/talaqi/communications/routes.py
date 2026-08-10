from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Request

from talaqi.communications.repository import NotificationRepository
from talaqi.communications.schemas import (
    MarkAllReadResponse,
    NotificationPageResponse,
    NotificationPreferencesRequest,
    NotificationPreferencesResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from talaqi.identity.dependencies import CsrfProtection, CurrentPrincipal, DatabaseSession
from talaqi.platform import ApiError, CursorCodec
from talaqi.platform.errors import ErrorEnvelope

router = APIRouter(prefix="/api/v1/me/notifications", tags=["communications"])
_AUTH_FAILURE: dict[str, Any] = {"model": ErrorEnvelope, "description": "Authentication failed."}
_CSRF_FAILURE: dict[str, Any] = {"model": ErrorEnvelope, "description": "CSRF validation failed."}


def _codec(request: Request) -> CursorCodec:
    secret = request.app.state.settings_factory().session_secret.get_secret_value().encode()
    return CursorCodec(hashlib.sha256(secret + b":notifications").digest())


@router.get("", response_model=NotificationPageResponse, operation_id="listMyNotifications")
async def list_my_notifications(
    request: Request,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=2_048)] = None,
) -> NotificationPageResponse:
    after: tuple[datetime, UUID] | None = None
    if cursor is not None:
        position = _codec(request).decode(cursor)
        if not isinstance(position.ordering, datetime):
            raise ApiError(
                code="invalid_cursor", message_key="errors.invalid_cursor", status_code=400
            )
        after = (position.ordering, position.tie_breaker)
    values = await NotificationRepository(session).list_for_user(
        principal.user_id, limit=limit + 1, after=after
    )
    visible = values[:limit]
    next_cursor = None
    if len(values) > limit:
        last = visible[-1]
        next_cursor = _codec(request).encode(ordering=last.created_at, tie_breaker=last.id)
    return NotificationPageResponse(
        items=[NotificationResponse.model_validate(value) for value in visible],
        next_cursor=next_cursor,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    operation_id="getMyNotificationUnreadCount",
)
async def get_unread_count(
    principal: CurrentPrincipal, session: DatabaseSession
) -> UnreadCountResponse:
    return UnreadCountResponse(
        unread_count=await NotificationRepository(session).unread_count(principal.user_id)
    )


@router.post(
    "/items/{notification_id}/read",
    response_model=NotificationResponse,
    operation_id="markMyNotificationRead",
    responses={401: _AUTH_FAILURE, 403: _CSRF_FAILURE, 404: {"model": ErrorEnvelope}},
)
async def mark_notification_read(
    notification_id: UUID,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> NotificationResponse:
    repository = NotificationRepository(session)
    if not await repository.mark_read(principal.user_id, notification_id, now=datetime.now(UTC)):
        raise ApiError(
            code="notification_not_found",
            message_key="errors.notification_not_found",
            status_code=404,
        )
    notification = await repository.get_for_user(principal.user_id, notification_id)
    if notification is None:
        raise RuntimeError("notification disappeared after mark-read")
    return NotificationResponse.model_validate(notification)


@router.post(
    "/read-all",
    response_model=MarkAllReadResponse,
    operation_id="markAllMyNotificationsRead",
    responses={401: _AUTH_FAILURE, 403: _CSRF_FAILURE},
)
async def mark_all_notifications_read(
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> MarkAllReadResponse:
    count = await NotificationRepository(session).mark_all_read(
        principal.user_id, now=datetime.now(UTC)
    )
    return MarkAllReadResponse(marked_count=count)


@router.get(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    operation_id="getMyNotificationPreferences",
)
async def get_notification_preferences(
    principal: CurrentPrincipal, session: DatabaseSession
) -> NotificationPreferencesResponse:
    preferences = await NotificationRepository(session).preferences(principal.user_id)
    if preferences is None:
        raise ApiError(
            code="profile_required", message_key="errors.profile_required", status_code=409
        )
    return NotificationPreferencesResponse.model_validate(preferences)


@router.patch(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    operation_id="updateMyNotificationPreferences",
    responses={401: _AUTH_FAILURE, 403: _CSRF_FAILURE},
)
async def update_notification_preferences(
    body: NotificationPreferencesRequest,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
) -> NotificationPreferencesResponse:
    preferences = await NotificationRepository(session).update_preferences(
        principal.user_id,
        event_email=body.event_email,
        community_email=body.community_email,
    )
    if preferences is None:
        raise ApiError(
            code="profile_required", message_key="errors.profile_required", status_code=409
        )
    return NotificationPreferencesResponse.model_validate(preferences)


__all__ = ["router"]
