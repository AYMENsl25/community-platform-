from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Final, Protocol
from uuid import UUID

from talaqi.audit.models import ActorKind
from talaqi.db.identifiers import generate_uuid7, validate_uuid7
from talaqi.events.access_models import EventRegistrationTerms
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.profiles.schemas import Capabilities
from talaqi.registrations.models import (
    Registration,
    RegistrationContext,
    RegistrationCreationResult,
    RegistrationMethod,
    RegistrationMutation,
    RegistrationState,
    RegistrationTransition,
    TransitionCommand,
    TransitionResult,
)

_REASON_CODE: Final = re.compile(r"^[a-z0-9_]{1,80}$")
_REGISTRATION_STATES: Final = frozenset(
    {"confirmed", "cash_pending", "waitlisted", "cancelled", "expired"}
)
_ALLOWED_TRANSITIONS: Final[frozenset[tuple[RegistrationState, RegistrationState]]] = frozenset(
    {
        ("confirmed", "cancelled"),
        ("cash_pending", "confirmed"),
        ("cash_pending", "cancelled"),
        ("cash_pending", "expired"),
        ("waitlisted", "confirmed"),
        ("waitlisted", "cash_pending"),
        ("waitlisted", "cancelled"),
    }
)


class RegistrationTransitionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class RegistrationRepositoryProtocol(Protocol):
    async def get_context(
        self, registration_id: UUID, *, for_update: bool
    ) -> RegistrationContext | None: ...

    async def get_transition(self, command_id: UUID) -> RegistrationTransition | None: ...

    async def apply_transition(
        self,
        current: Registration,
        command: TransitionCommand,
        command_hash: bytes,
        mutation: RegistrationMutation,
    ) -> TransitionResult: ...


class RegistrationCreationRepositoryProtocol(Protocol):
    async def get_active(self, event_id: UUID, user_id: UUID) -> Registration | None: ...

    async def held_seat_count(self, event_id: UUID) -> int: ...

    async def next_waitlist_sequence(self, event_id: UUID) -> int: ...

    async def create_registration(
        self,
        *,
        registration_id: UUID,
        command_id: UUID,
        command_hash: bytes,
        event_id: UUID,
        user_id: UUID,
        method: RegistrationMethod,
        state: RegistrationState,
        seat_held: bool,
        waitlist_sequence: int | None,
        cash_expires_at: datetime | None,
        confirmed_at: datetime | None,
        request_id: UUID,
        occurred_at: datetime,
    ) -> Registration: ...


class RegistrationEligibilityProtocol(Protocol):
    async def evaluate(self, principal: AuthPrincipal) -> Capabilities: ...


class RegistrationEventAccessProtocol(Protocol):
    async def registration_terms(
        self,
        event_id: UUID,
        *,
        private_link_hash: bytes | None,
        now: datetime,
    ) -> EventRegistrationTerms: ...


def is_transition_allowed(current: RegistrationState, target: RegistrationState) -> bool:
    return (current, target) in _ALLOWED_TRANSITIONS


def _instant(value: datetime, *, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RegistrationTransitionError(f"invalid_{field}")
    return value.astimezone(UTC)


def _normalize_command(command: TransitionCommand) -> TransitionCommand:
    try:
        command_id = validate_uuid7(command.command_id)
        registration_id = validate_uuid7(command.registration_id)
    except ValueError:
        raise RegistrationTransitionError("invalid_registration_transition") from None
    if command.target_state not in _REGISTRATION_STATES:
        raise RegistrationTransitionError("invalid_registration_transition")
    if command.actor_kind == "system":
        if command.actor_user_id is not None:
            raise RegistrationTransitionError("invalid_transition_actor")
    elif command.actor_kind in ("member", "organizer", "admin"):
        if command.actor_user_id is None:
            raise RegistrationTransitionError("invalid_transition_actor")
    else:
        raise RegistrationTransitionError("invalid_transition_actor")
    if _REASON_CODE.fullmatch(command.reason_code) is None:
        raise RegistrationTransitionError("invalid_transition_reason")
    occurred_at = _instant(command.occurred_at, field="transition_time")
    cash_expires_at = (
        _instant(command.cash_expires_at, field="cash_deadline")
        if command.cash_expires_at is not None
        else None
    )
    if command.target_state == "cash_pending":
        if cash_expires_at is None or cash_expires_at <= occurred_at:
            raise RegistrationTransitionError("invalid_cash_deadline")
    elif cash_expires_at is not None:
        raise RegistrationTransitionError("unexpected_cash_deadline")
    return replace(
        command,
        command_id=command_id,
        registration_id=registration_id,
        occurred_at=occurred_at,
        cash_expires_at=cash_expires_at,
    )


def _command_hash(command: TransitionCommand) -> bytes:
    payload = {
        "actor_kind": command.actor_kind,
        "actor_user_id": str(command.actor_user_id) if command.actor_user_id is not None else None,
        "cash_expires_at": (
            command.cash_expires_at.isoformat() if command.cash_expires_at is not None else None
        ),
        "occurred_at": command.occurred_at.isoformat(),
        "reason_code": command.reason_code,
        "registration_id": str(command.registration_id),
        "request_id": str(command.request_id) if command.request_id is not None else None,
        "target_state": command.target_state,
    }
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).digest()


def _mutation(current: Registration, command: TransitionCommand) -> RegistrationMutation:
    target = command.target_state
    if target == "confirmed":
        return RegistrationMutation(
            state=target,
            seat_held=True,
            waitlist_sequence=None,
            cash_expires_at=None,
            confirmed_at=command.occurred_at,
            cancelled_at=None,
            expired_at=None,
            cancellation_reason=None,
        )
    if target == "cash_pending":
        return RegistrationMutation(
            state=target,
            seat_held=True,
            waitlist_sequence=None,
            cash_expires_at=command.cash_expires_at,
            confirmed_at=None,
            cancelled_at=None,
            expired_at=None,
            cancellation_reason=None,
        )
    if target == "cancelled":
        return RegistrationMutation(
            state=target,
            seat_held=False,
            waitlist_sequence=None,
            cash_expires_at=None,
            confirmed_at=current.confirmed_at,
            cancelled_at=command.occurred_at,
            expired_at=None,
            cancellation_reason=command.reason_code,
        )
    if target == "expired":
        return RegistrationMutation(
            state=target,
            seat_held=False,
            waitlist_sequence=None,
            cash_expires_at=current.cash_expires_at,
            confirmed_at=None,
            cancelled_at=None,
            expired_at=command.occurred_at,
            cancellation_reason=None,
        )
    raise RegistrationTransitionError("invalid_registration_transition")


class RegistrationCreationService:
    def __init__(
        self,
        repository: RegistrationCreationRepositoryProtocol,
        events: RegistrationEventAccessProtocol,
        eligibility: RegistrationEligibilityProtocol,
    ) -> None:
        self._repository = repository
        self._events = events
        self._eligibility = eligibility

    async def register(
        self,
        principal: AuthPrincipal,
        event_id: UUID,
        *,
        private_link_hash: bytes | None,
        request_id: UUID,
        now: datetime,
    ) -> RegistrationCreationResult:
        current = _instant(now, field="registration_time")
        event = await self._events.registration_terms(
            event_id, private_link_hash=private_link_hash, now=current
        )
        capabilities = await self._eligibility.evaluate(principal)
        if not capabilities.register_event:
            raise ApiError(
                code="registration_not_allowed",
                message_key="errors.registration_not_allowed",
                status_code=403,
            )
        existing = await self._repository.get_active(event.id, principal.user_id)
        if existing is not None:
            return RegistrationCreationResult(registration=existing, created=False)
        if event.start_at <= current:
            raise ApiError(
                code="registration_closed",
                message_key="errors.registration_closed",
                status_code=409,
            )
        registration = await self._create(principal, event, request_id=request_id, now=current)
        return RegistrationCreationResult(registration=registration, created=True)

    async def _create(
        self,
        principal: AuthPrincipal,
        event: EventRegistrationTerms,
        *,
        request_id: UUID,
        now: datetime,
    ) -> Registration:
        held = await self._repository.held_seat_count(event.id)
        seat_available = event.capacity is None or held < event.capacity
        state: RegistrationState
        if not seat_available:
            state = "waitlisted"
        elif event.method == "free":
            state = "confirmed"
        else:
            state = "cash_pending"

        waitlist_sequence = (
            await self._repository.next_waitlist_sequence(event.id)
            if state == "waitlisted"
            else None
        )
        cash_expires_at = None
        if state == "cash_pending":
            if event.cash_expiry_minutes is None:
                raise RuntimeError("published cash event has no expiry policy")
            cash_expires_at = min(
                now + timedelta(minutes=event.cash_expiry_minutes), event.start_at
            )
        registration_id = generate_uuid7()
        command_id = generate_uuid7()
        command_hash = hashlib.sha256(
            (
                f"registration-create-v1:{command_id}:{registration_id}:"
                f"{event.id}:{principal.user_id}:{state}"
            ).encode("ascii")
        ).digest()
        return await self._repository.create_registration(
            registration_id=registration_id,
            command_id=command_id,
            command_hash=command_hash,
            event_id=event.id,
            user_id=principal.user_id,
            method=event.method,
            state=state,
            seat_held=state in ("confirmed", "cash_pending"),
            waitlist_sequence=waitlist_sequence,
            cash_expires_at=cash_expires_at,
            confirmed_at=now if state == "confirmed" else None,
            request_id=request_id,
            occurred_at=now,
        )


class RegistrationTransitionService:
    def __init__(self, repository: RegistrationRepositoryProtocol) -> None:
        self._repository = repository

    async def transition(self, value: TransitionCommand) -> TransitionResult:
        command = _normalize_command(value)
        fingerprint = _command_hash(command)
        replay = await self._replay(command, fingerprint)
        if replay is not None:
            return replay

        context = await self._repository.get_context(command.registration_id, for_update=True)
        if context is None:
            raise RegistrationTransitionError("registration_not_found")

        # A competing request with the same command may have committed while the
        # registration row lock was being acquired. Recheck after the lock.
        replay = await self._replay(command, fingerprint)
        if replay is not None:
            return replay

        current = context.registration
        if context.event_status != "published" or context.event_start_at <= command.occurred_at:
            raise RegistrationTransitionError("event_not_transitionable")
        if not is_transition_allowed(current.state, command.target_state):
            raise RegistrationTransitionError("invalid_registration_transition")
        if current.method == "free" and command.target_state in ("cash_pending", "expired"):
            raise RegistrationTransitionError("invalid_registration_method_transition")
        if command.target_state == "expired" and (
            current.cash_expires_at is None or current.cash_expires_at > command.occurred_at
        ):
            raise RegistrationTransitionError("cash_reservation_not_expired")
        return await self._repository.apply_transition(
            current,
            command,
            fingerprint,
            _mutation(current, command),
        )

    async def _replay(
        self, command: TransitionCommand, fingerprint: bytes
    ) -> TransitionResult | None:
        transition = await self._repository.get_transition(command.command_id)
        if transition is None:
            return None
        if transition.command_hash != fingerprint:
            raise RegistrationTransitionError("transition_idempotency_conflict")
        context = await self._repository.get_context(transition.registration_id, for_update=False)
        if context is None:
            raise RegistrationTransitionError("registration_not_found")
        return TransitionResult(registration=context.registration, transition=transition)


def new_transition_command(
    *,
    registration_id: UUID,
    target_state: RegistrationState,
    actor_user_id: UUID | None,
    actor_kind: ActorKind,
    reason_code: str,
    occurred_at: datetime,
    request_id: UUID | None = None,
    cash_expires_at: datetime | None = None,
) -> TransitionCommand:
    return TransitionCommand(
        command_id=generate_uuid7(),
        registration_id=registration_id,
        target_state=target_state,
        actor_user_id=actor_user_id,
        actor_kind=actor_kind,
        reason_code=reason_code,
        occurred_at=occurred_at,
        request_id=request_id,
        cash_expires_at=cash_expires_at,
    )
