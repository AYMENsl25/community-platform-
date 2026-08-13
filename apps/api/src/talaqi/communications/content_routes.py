from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Request, status

from talaqi.communications.content import PublishedContent
from talaqi.communications.content_runtime import build_organizer_communications_service
from talaqi.communications.content_schemas import (
    ClubAnnouncementRequest,
    EventUpdateRequest,
    PublishedContentPageResponse,
    PublishedContentResponse,
)
from talaqi.identity.dependencies import CsrfProtection, CurrentPrincipal, DatabaseSession

router = APIRouter(tags=["communications"])

IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=16, max_length=200),
]


def _response(item: PublishedContent) -> PublishedContentResponse:
    return PublishedContentResponse(
        id=item.id,
        title=item.title,
        body=item.body,
        audience=item.audience_key,
        published_at=item.published_at,
    )


@router.post(
    "/api/v1/clubs/{club_id}/announcements",
    response_model=PublishedContentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_club_announcement(
    club_id: UUID,
    body: ClubAnnouncementRequest,
    request: Request,
    principal: CurrentPrincipal,
    csrf: CsrfProtection,
    session: DatabaseSession,
    idempotency_key: IdempotencyKey,
) -> PublishedContentResponse:
    del csrf
    item = await build_organizer_communications_service(request, session).create_club(
        principal, club_id, body, idempotency_key
    )
    await session.commit()
    return _response(item)


@router.get(
    "/api/v1/clubs/{club_id}/announcements",
    response_model=PublishedContentPageResponse,
)
async def list_club_announcements(
    club_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> PublishedContentPageResponse:
    items = await build_organizer_communications_service(request, session).list_club(
        principal, club_id
    )
    return PublishedContentPageResponse(items=tuple(_response(item) for item in items))


@router.post(
    "/api/v1/events/{event_id}/updates",
    response_model=PublishedContentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_event_update(
    event_id: UUID,
    body: EventUpdateRequest,
    request: Request,
    principal: CurrentPrincipal,
    csrf: CsrfProtection,
    session: DatabaseSession,
    idempotency_key: IdempotencyKey,
) -> PublishedContentResponse:
    del csrf
    item = await build_organizer_communications_service(request, session).create_event(
        principal, event_id, body, idempotency_key
    )
    await session.commit()
    return _response(item)


@router.get(
    "/api/v1/events/{event_id}/updates",
    response_model=PublishedContentPageResponse,
)
async def list_event_updates(
    event_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> PublishedContentPageResponse:
    items = await build_organizer_communications_service(request, session).list_event(
        principal, event_id
    )
    return PublishedContentPageResponse(items=tuple(_response(item) for item in items))


__all__ = ["router"]
