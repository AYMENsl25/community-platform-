from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.config import Settings
from talaqi.events.access_runtime import build_event_access_service
from talaqi.profiles.runtime import build_registration_eligibility_service
from talaqi.registrations.repository import RegistrationRepository
from talaqi.registrations.service import RegistrationCreationService


def build_registration_service(
    request: Request, session: AsyncSession
) -> RegistrationCreationService:
    settings: Settings = request.app.state.settings_factory()
    return RegistrationCreationService(
        RegistrationRepository(session),
        build_event_access_service(request, session),
        build_registration_eligibility_service(session, settings),
    )


__all__ = ["build_registration_service"]
