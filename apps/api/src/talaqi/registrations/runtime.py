from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.audit import AuditRepository, AuditService
from talaqi.config import Settings
from talaqi.events.access_runtime import build_event_access_service
from talaqi.profiles.runtime import build_registration_eligibility_service
from talaqi.registrations.repository import RegistrationRepository
from talaqi.registrations.service import (
    PromotionService,
    RegistrationCancellationService,
    RegistrationCreationService,
    RegistrationTransitionService,
)


def build_registration_service(
    request: Request, session: AsyncSession
) -> RegistrationCreationService:
    settings: Settings = request.app.state.settings_factory()
    return RegistrationCreationService(
        RegistrationRepository(session),
        build_event_access_service(request, session),
        build_registration_eligibility_service(session, settings),
    )


def build_cancellation_service(
    request: Request, session: AsyncSession
) -> RegistrationCancellationService:
    settings: Settings = request.app.state.settings_factory()
    repository = RegistrationRepository(session)
    events = build_event_access_service(request, session)
    eligibility = build_registration_eligibility_service(session, settings)
    transitions = RegistrationTransitionService(repository)
    audit = AuditService(AuditRepository(session))
    promotion = PromotionService(repository, events, eligibility, transitions, audit)
    return RegistrationCancellationService(
        repository,
        events,
        transitions,
        promotion,
        audit,
    )


__all__ = ["build_cancellation_service", "build_registration_service"]
