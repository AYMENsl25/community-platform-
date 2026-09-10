from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.clubs.event_access import ClubEventAccessService
from talaqi.clubs.repository import ClubRepository
from talaqi.communications.content import OrganizerContentRepository
from talaqi.communications.content_service import OrganizerCommunicationsService
from talaqi.events.access_runtime import build_event_access_service
from talaqi.settings.repository import PlatformSettingsRepository
from talaqi.settings.service import PlatformSettingsService


def build_organizer_communications_service(
    request: Request, session: AsyncSession
) -> OrganizerCommunicationsService:
    return OrganizerCommunicationsService(
        OrganizerContentRepository(session),
        ClubEventAccessService(ClubRepository(session)),
        build_event_access_service(request, session),
        PlatformSettingsService(PlatformSettingsRepository(session)),
    )


__all__ = ["build_organizer_communications_service"]
