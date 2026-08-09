from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from talaqi.audit.models import ActorKind

RegistrationMethod = Literal["free", "cash_organizer_confirmed"]
RegistrationState = Literal["confirmed", "cash_pending", "waitlisted", "cancelled", "expired"]
RegistrationEventStatus = Literal["draft", "published", "cancelled", "completed", "suspended"]


@dataclass(frozen=True, slots=True)
class Registration:
    id: UUID
    event_id: UUID
    user_id: UUID
    method: RegistrationMethod
    state: RegistrationState
    seat_held: bool
    waitlist_sequence: int | None
    cash_expires_at: datetime | None
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    expired_at: datetime | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RegistrationContext:
    registration: Registration
    event_status: RegistrationEventStatus
    event_start_at: datetime


@dataclass(frozen=True, slots=True)
class RegistrationCreationResult:
    registration: Registration
    created: bool


@dataclass(frozen=True, slots=True)
class Attendee:
    registration: Registration
    username: str
    display_name: str


@dataclass(frozen=True, slots=True)
class RegistrationMutation:
    state: RegistrationState
    seat_held: bool
    waitlist_sequence: int | None
    cash_expires_at: datetime | None
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    expired_at: datetime | None
    cancellation_reason: str | None


@dataclass(frozen=True, slots=True)
class TransitionCommand:
    command_id: UUID
    registration_id: UUID
    target_state: RegistrationState
    actor_user_id: UUID | None
    actor_kind: ActorKind
    reason_code: str
    occurred_at: datetime
    request_id: UUID | None = None
    cash_expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RegistrationTransition:
    id: UUID
    command_id: UUID
    command_hash: bytes
    registration_id: UUID
    actor_user_id: UUID | None
    actor_kind: ActorKind
    previous_state: RegistrationState | None
    new_state: RegistrationState
    reason_code: str
    request_id: UUID | None
    occurred_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class TransitionResult:
    registration: Registration
    transition: RegistrationTransition
