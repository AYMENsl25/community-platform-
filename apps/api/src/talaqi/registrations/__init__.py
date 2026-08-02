"""Registration state and transition services."""

from talaqi.registrations.models import (
    Registration,
    RegistrationContext,
    RegistrationMethod,
    RegistrationState,
    RegistrationTransition,
    TransitionCommand,
    TransitionResult,
)
from talaqi.registrations.repository import RegistrationRepository
from talaqi.registrations.service import RegistrationTransitionError, RegistrationTransitionService

__all__ = [
    "Registration",
    "RegistrationContext",
    "RegistrationMethod",
    "RegistrationRepository",
    "RegistrationState",
    "RegistrationTransition",
    "RegistrationTransitionError",
    "RegistrationTransitionService",
    "TransitionCommand",
    "TransitionResult",
]
