from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

import pytest
from talaqi.db.identifiers import generate_uuid7
from talaqi.events.access_models import EventCancellationTerms
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.profiles.schemas import Capabilities
from talaqi.registrations.models import (
    Registration,
    RegistrationContext,
    RegistrationMutation,
    RegistrationState,
    RegistrationTransition,
    TransitionCommand,
    TransitionResult,
)
from talaqi.registrations.service import (
    PromotionService,
    RegistrationCancellationService,
    RegistrationTransitionError,
    RegistrationTransitionService,
)

NOW = datetime(2026, 8, 2, 12, tzinfo=UTC)
USER_ID = UUID("01900000-0000-7000-8000-000000000401")
EVENT_ID = UUID("01900000-0000-7000-8000-000000000402")
REGISTRATION_ID = UUID("01900000-0000-7000-8000-000000000403")
STATES: tuple[RegistrationState, ...] = (
    "confirmed",
    "cash_pending",
    "waitlisted",
    "cancelled",
    "expired",
)
ALLOWED = {
    ("confirmed", "cancelled"),
    ("cash_pending", "confirmed"),
    ("cash_pending", "cancelled"),
    ("cash_pending", "expired"),
    ("waitlisted", "confirmed"),
    ("waitlisted", "cash_pending"),
    ("waitlisted", "cancelled"),
}


def registration(
    state: RegistrationState, *, method: str = "cash_organizer_confirmed"
) -> Registration:
    return Registration(
        id=REGISTRATION_ID,
        event_id=EVENT_ID,
        user_id=USER_ID,
        method=method,  # type: ignore[arg-type]
        state=state,
        seat_held=state in ("confirmed", "cash_pending"),
        waitlist_sequence=7 if state == "waitlisted" else None,
        cash_expires_at=NOW - timedelta(minutes=1)
        if state in ("cash_pending", "expired")
        else None,
        confirmed_at=NOW - timedelta(days=1) if state == "confirmed" else None,
        cancelled_at=NOW - timedelta(minutes=1) if state == "cancelled" else None,
        expired_at=NOW if state == "expired" else None,
        cancellation_reason="member_cancelled" if state == "cancelled" else None,
        created_at=NOW - timedelta(days=2),
        updated_at=NOW - timedelta(days=1),
    )


def command(
    target: RegistrationState,
    *,
    command_id: UUID | None = None,
    reason_code: str = "state_changed",
    occurred_at: datetime = NOW,
) -> TransitionCommand:
    return TransitionCommand(
        command_id=command_id or generate_uuid7(),
        registration_id=REGISTRATION_ID,
        target_state=target,
        actor_user_id=None,
        actor_kind="system",
        reason_code=reason_code,
        occurred_at=occurred_at,
        request_id=generate_uuid7(),
        cash_expires_at=NOW + timedelta(hours=2) if target == "cash_pending" else None,
    )


class FakeRepository:
    def __init__(
        self,
        current: Registration,
        *,
        event_status: str = "published",
        event_start_at: datetime = NOW + timedelta(days=1),
    ) -> None:
        self.current = current
        self.event_status = event_status
        self.event_start_at = event_start_at
        self.transitions: dict[UUID, RegistrationTransition] = {}
        self.apply_count = 0

    async def get_context(
        self, registration_id: UUID, *, for_update: bool
    ) -> RegistrationContext | None:
        del for_update
        if registration_id != self.current.id:
            return None
        return RegistrationContext(
            registration=self.current,
            event_status=self.event_status,  # type: ignore[arg-type]
            event_start_at=self.event_start_at,
        )

    async def get_transition(self, command_id: UUID) -> RegistrationTransition | None:
        return self.transitions.get(command_id)

    async def apply_transition(
        self,
        current: Registration,
        command: TransitionCommand,
        command_hash: bytes,
        mutation: RegistrationMutation,
    ) -> TransitionResult:
        self.apply_count += 1
        self.current = replace(
            current,
            state=mutation.state,
            seat_held=mutation.seat_held,
            waitlist_sequence=mutation.waitlist_sequence,
            cash_expires_at=mutation.cash_expires_at,
            confirmed_at=mutation.confirmed_at,
            cancelled_at=mutation.cancelled_at,
            expired_at=mutation.expired_at,
            cancellation_reason=mutation.cancellation_reason,
            updated_at=command.occurred_at,
        )
        transition = RegistrationTransition(
            id=generate_uuid7(),
            command_id=command.command_id,
            command_hash=command_hash,
            registration_id=current.id,
            actor_user_id=command.actor_user_id,
            actor_kind=command.actor_kind,
            previous_state=current.state,
            new_state=command.target_state,
            reason_code=command.reason_code,
            request_id=command.request_id,
            occurred_at=command.occurred_at,
            created_at=command.occurred_at,
        )
        self.transitions[command.command_id] = transition
        return TransitionResult(self.current, transition)


class FakePromotionRepository(FakeRepository):
    async def held_seat_count(self, event_id: UUID) -> int:
        assert event_id == EVENT_ID
        return int(self.current.seat_held)

    async def oldest_waitlisted(self, event_id: UUID) -> Registration | None:
        assert event_id == EVENT_ID
        return self.current if self.current.state == "waitlisted" else None


class FakeCancellationEvents:
    def __init__(self, *, start_at: datetime, capacity: int = 1) -> None:
        self.terms = EventCancellationTerms(
            id=EVENT_ID,
            start_at=start_at,
            capacity=capacity,
            method="free",
            cash_expiry_minutes=None,
            cancellation_cutoff_minutes=0,
        )

    async def cancellation_terms(self, event_id: UUID) -> EventCancellationTerms:
        assert event_id == EVENT_ID
        return self.terms


class FakePromotionEligibility:
    async def evaluate_user(self, user_id: UUID) -> Capabilities:
        assert user_id == USER_ID
        return Capabilities(
            create_club=True,
            create_independent_event=True,
            save_event=True,
            register_event=True,
            access_admin=False,
            blockers=(),
        )


class FakeAudit:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def record(self, **values: object) -> None:
        self.actions.append(cast(str, values["action"]))


@pytest.mark.asyncio
@pytest.mark.parametrize(("current", "target"), [(a, b) for a in STATES for b in STATES])
async def test_transition_table_is_exhaustive(
    current: RegistrationState, target: RegistrationState
) -> None:
    repository = FakeRepository(registration(current))
    service = RegistrationTransitionService(repository)
    if (current, target) in ALLOWED:
        result = await service.transition(command(target))
        assert result.registration.state == target
        assert result.transition.previous_state == current
        assert result.transition.new_state == target
        assert result.transition.command_hash != bytes(32)
    else:
        with pytest.raises(RegistrationTransitionError, match="invalid_registration_transition"):
            await service.transition(command(target))


@pytest.mark.asyncio
async def test_exact_command_replay_is_idempotent_and_conflicting_reuse_is_rejected() -> None:
    repository = FakeRepository(registration("confirmed"))
    service = RegistrationTransitionService(repository)
    original = command("cancelled")

    first = await service.transition(original)
    replay = await service.transition(original)

    assert replay == first
    assert repository.apply_count == 1
    with pytest.raises(RegistrationTransitionError, match="transition_idempotency_conflict"):
        await service.transition(replace(original, reason_code="different_reason"))


@pytest.mark.asyncio
@pytest.mark.parametrize("event_status", ["draft", "cancelled", "completed", "suspended"])
async def test_non_published_event_rejects_transition(event_status: str) -> None:
    repository = FakeRepository(registration("confirmed"), event_status=event_status)
    with pytest.raises(RegistrationTransitionError, match="event_not_transitionable"):
        await RegistrationTransitionService(repository).transition(command("cancelled"))


@pytest.mark.asyncio
async def test_transition_at_or_after_event_start_is_rejected() -> None:
    repository = FakeRepository(registration("confirmed"), event_start_at=NOW)
    with pytest.raises(RegistrationTransitionError, match="event_not_transitionable"):
        await RegistrationTransitionService(repository).transition(command("cancelled"))


@pytest.mark.asyncio
async def test_free_registration_cannot_enter_cash_state() -> None:
    repository = FakeRepository(registration("waitlisted", method="free"))
    with pytest.raises(RegistrationTransitionError, match="invalid_registration_method_transition"):
        await RegistrationTransitionService(repository).transition(command("cash_pending"))


@pytest.mark.asyncio
async def test_cash_reservation_cannot_expire_before_its_deadline() -> None:
    current = replace(
        registration("cash_pending"),
        cash_expires_at=NOW + timedelta(minutes=1),
    )
    repository = FakeRepository(current)
    with pytest.raises(RegistrationTransitionError, match="cash_reservation_not_expired"):
        await RegistrationTransitionService(repository).transition(command("expired"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"actor_user_id": USER_ID}, "invalid_transition_actor"),
        ({"reason_code": "Not Safe"}, "invalid_transition_reason"),
        ({"occurred_at": datetime(2026, 8, 2, 12)}, "invalid_transition_time"),
        (
            {"target_state": "cash_pending", "cash_expires_at": NOW},
            "invalid_cash_deadline",
        ),
        (
            {"target_state": "cancelled", "cash_expires_at": NOW + timedelta(hours=1)},
            "unexpected_cash_deadline",
        ),
    ],
)
async def test_command_shape_is_validated_before_repository_mutation(
    changes: dict[str, object], code: str
) -> None:
    repository = FakeRepository(registration("confirmed"))
    value = replace(command("cancelled"), **changes)
    with pytest.raises(RegistrationTransitionError, match=code):
        await RegistrationTransitionService(repository).transition(value)
    assert repository.apply_count == 0


def test_repository_interface_has_no_arbitrary_state_update() -> None:
    from talaqi.registrations.repository import RegistrationRepository

    assert not hasattr(RegistrationRepository, "update")
    assert not hasattr(RegistrationRepository, "set_state")


@pytest.mark.asyncio
async def test_promotion_worker_retry_stops_when_capacity_is_full() -> None:
    repository = FakePromotionRepository(registration("waitlisted", method="free"))
    transitions = RegistrationTransitionService(repository)
    audit = FakeAudit()
    service = PromotionService(
        cast(Any, repository),
        cast(Any, FakeCancellationEvents(start_at=NOW + timedelta(hours=2))),
        cast(Any, FakePromotionEligibility()),
        transitions,
        cast(Any, audit),
    )

    first = await service.promote_next(EVENT_ID, now=NOW, request_id=generate_uuid7())
    replay = await service.promote_next(EVENT_ID, now=NOW, request_id=generate_uuid7())

    assert first is not None
    assert first.state == "confirmed"
    assert replay is None
    assert repository.apply_count == 1
    assert audit.actions == ["registration.promote"]


@pytest.mark.asyncio
async def test_cancellation_is_closed_at_exact_cutoff() -> None:
    service = RegistrationCancellationService(
        cast(Any, object()),
        cast(Any, FakeCancellationEvents(start_at=NOW)),
        cast(Any, object()),
        cast(Any, object()),
        cast(Any, object()),
    )
    principal = AuthPrincipal(
        user_id=USER_ID,
        session_id=generate_uuid7(),
        email_verified=True,
        status="active",
        is_platform_admin=False,
    )

    with pytest.raises(ApiError) as error:
        await service.cancel(
            principal,
            EVENT_ID,
            request_id=generate_uuid7(),
            now=NOW,
        )

    assert error.value.code == "cancellation_closed"
