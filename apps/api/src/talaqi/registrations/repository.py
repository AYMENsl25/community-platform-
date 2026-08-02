from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.db.identifiers import generate_uuid7
from talaqi.registrations.models import (
    Registration,
    RegistrationContext,
    RegistrationEventStatus,
    RegistrationMethod,
    RegistrationMutation,
    RegistrationState,
    RegistrationTransition,
    TransitionCommand,
    TransitionResult,
)
from talaqi.registrations.service import RegistrationTransitionError

_REGISTRATION_FIELDS = """
registration.id, registration.event_id, registration.user_id,
registration.method::text AS method, registration.state::text AS state,
registration.seat_held, registration.waitlist_sequence,
registration.cash_expires_at, registration.confirmed_at,
registration.cancelled_at, registration.expired_at,
registration.cancellation_reason, registration.created_at,
registration.updated_at
"""

_TRANSITION_FIELDS = """
id, command_id, command_hash, registration_id, actor_user_id,
actor_kind, previous_state::text AS previous_state,
new_state::text AS new_state, reason_code, request_id,
occurred_at, created_at
"""


def _registration(row: Mapping[str, object]) -> Registration:
    return Registration(
        id=cast(UUID, row["id"]),
        event_id=cast(UUID, row["event_id"]),
        user_id=cast(UUID, row["user_id"]),
        method=cast(RegistrationMethod, row["method"]),
        state=cast(RegistrationState, row["state"]),
        seat_held=cast(bool, row["seat_held"]),
        waitlist_sequence=cast(int | None, row["waitlist_sequence"]),
        cash_expires_at=cast(datetime | None, row["cash_expires_at"]),
        confirmed_at=cast(datetime | None, row["confirmed_at"]),
        cancelled_at=cast(datetime | None, row["cancelled_at"]),
        expired_at=cast(datetime | None, row["expired_at"]),
        cancellation_reason=cast(str | None, row["cancellation_reason"]),
        created_at=cast(datetime, row["created_at"]),
        updated_at=cast(datetime, row["updated_at"]),
    )


def _transition(row: Mapping[str, object]) -> RegistrationTransition:
    return RegistrationTransition(
        id=cast(UUID, row["id"]),
        command_id=cast(UUID, row["command_id"]),
        command_hash=cast(bytes, row["command_hash"]),
        registration_id=cast(UUID, row["registration_id"]),
        actor_user_id=cast(UUID | None, row["actor_user_id"]),
        actor_kind=cast(str, row["actor_kind"]),  # type: ignore[arg-type]
        previous_state=cast(RegistrationState | None, row["previous_state"]),
        new_state=cast(RegistrationState, row["new_state"]),
        reason_code=cast(str, row["reason_code"]),
        request_id=cast(UUID | None, row["request_id"]),
        occurred_at=cast(datetime, row["occurred_at"]),
        created_at=cast(datetime, row["created_at"]),
    )


class RegistrationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_context(
        self, registration_id: UUID, *, for_update: bool
    ) -> RegistrationContext | None:
        lock = "FOR UPDATE OF event, registration" if for_update else ""
        row = (
            (
                await self._session.execute(
                    text(
                        f"""
                        SELECT {_REGISTRATION_FIELDS},
                               event.status::text AS event_status,
                               event.start_at AS event_start_at
                        FROM talaqi.registrations AS registration
                        JOIN talaqi.events AS event ON event.id = registration.event_id
                        WHERE registration.id = :registration_id
                        {lock}
                        """  # noqa: S608 -- fixed internal lock clause; bound identifier
                    ),
                    {"registration_id": registration_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        values = cast(Mapping[str, object], row)
        return RegistrationContext(
            registration=_registration(values),
            event_status=cast(RegistrationEventStatus, values["event_status"]),
            event_start_at=cast(datetime, values["event_start_at"]),
        )

    async def get_transition(self, command_id: UUID) -> RegistrationTransition | None:
        row = (
            (
                await self._session.execute(
                    text(
                        f"""
                        SELECT {_TRANSITION_FIELDS}
                        FROM talaqi.registration_transitions
                        WHERE command_id = :command_id
                        """  # noqa: S608 -- fixed selected fields; bound identifier
                    ),
                    {"command_id": command_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        return _transition(cast(Mapping[str, object], row)) if row is not None else None

    async def apply_transition(
        self,
        current: Registration,
        command: TransitionCommand,
        command_hash: bytes,
        mutation: RegistrationMutation,
    ) -> TransitionResult:
        row = (
            (
                await self._session.execute(
                    text(
                        f"""
                        UPDATE talaqi.registrations AS registration
                        SET state = CAST(:state AS talaqi.registration_state),
                            seat_held = :seat_held,
                            waitlist_sequence = :waitlist_sequence,
                            cash_expires_at = :cash_expires_at,
                            confirmed_at = :confirmed_at,
                            cancelled_at = :cancelled_at,
                            expired_at = :expired_at,
                            cancellation_reason = :cancellation_reason
                        WHERE id = :registration_id
                          AND state = CAST(:expected_state AS talaqi.registration_state)
                        RETURNING {_REGISTRATION_FIELDS}
                        """  # noqa: S608 -- fixed selected fields; bound values
                    ),
                    {
                        "registration_id": current.id,
                        "expected_state": current.state,
                        "state": mutation.state,
                        "seat_held": mutation.seat_held,
                        "waitlist_sequence": mutation.waitlist_sequence,
                        "cash_expires_at": mutation.cash_expires_at,
                        "confirmed_at": mutation.confirmed_at,
                        "cancelled_at": mutation.cancelled_at,
                        "expired_at": mutation.expired_at,
                        "cancellation_reason": mutation.cancellation_reason,
                    },
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise RegistrationTransitionError("registration_state_changed")

        transition_id = generate_uuid7()
        transition_row = (
            (
                await self._session.execute(
                    text(
                        f"""
                        INSERT INTO talaqi.registration_transitions (
                            id, command_id, command_hash, registration_id,
                            actor_user_id, actor_kind, previous_state, new_state,
                            reason_code, request_id, occurred_at
                        ) VALUES (
                            :id, :command_id, :command_hash, :registration_id,
                            :actor_user_id, :actor_kind,
                            CAST(:previous_state AS talaqi.registration_state),
                            CAST(:new_state AS talaqi.registration_state),
                            :reason_code, :request_id, :occurred_at
                        )
                        RETURNING {_TRANSITION_FIELDS}
                        """  # noqa: S608 -- fixed selected fields; bound values
                    ),
                    {
                        "id": transition_id,
                        "command_id": command.command_id,
                        "command_hash": command_hash,
                        "registration_id": current.id,
                        "actor_user_id": command.actor_user_id,
                        "actor_kind": command.actor_kind,
                        "previous_state": current.state,
                        "new_state": mutation.state,
                        "reason_code": command.reason_code,
                        "request_id": command.request_id,
                        "occurred_at": command.occurred_at,
                    },
                )
            )
            .mappings()
            .one()
        )
        return TransitionResult(
            registration=_registration(cast(Mapping[str, object], row)),
            transition=_transition(cast(Mapping[str, object], transition_row)),
        )
