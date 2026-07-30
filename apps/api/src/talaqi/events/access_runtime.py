from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.audit import AuditRepository, AuditService
from talaqi.clubs.event_access import ClubEventAccessService
from talaqi.clubs.repository import ClubRepository
from talaqi.config import Settings
from talaqi.events.access_repository import EventAccessRepository
from talaqi.events.access_service import EventAccessService
from talaqi.events.access_tokens import PrivateLinkTokenCodec
from talaqi.events.repository import EventRepository


def build_event_access_service(
    request: Request,
    session: AsyncSession,
) -> EventAccessService:
    settings: Settings = request.app.state.settings_factory()
    return EventAccessService(
        EventAccessRepository(session),
        EventRepository(session),
        ClubEventAccessService(ClubRepository(session)),
        AuditService(AuditRepository(session)),
        PrivateLinkTokenCodec(settings.session_secret.get_secret_value().encode("utf-8")),
    )


__all__ = ["build_event_access_service"]
