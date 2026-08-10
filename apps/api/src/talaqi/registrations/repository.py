from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.db.identifiers import generate_uuid7
from talaqi.registrations.models import (
    Attendee,
    AttendeeSummary,
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

    async def get_active(
        self, event_id: UUID, user_id: UUID, *, for_update: bool = False
    ) -> Registration | None:
        lock = "FOR UPDATE" if for_update else ""
        row = (
            (
                await self._session.execute(
                    text(
                        f"""
                        SELECT {_REGISTRATION_FIELDS}
                        FROM talaqi.registrations AS registration
                        WHERE registration.event_id = :event_id
                          AND registration.user_id = :user_id
                          AND registration.state IN ('confirmed', 'cash_pending', 'waitlisted')
                        {lock}
                        """  # noqa: S608 -- fixed fields; bound identifiers
                    ),
                    {"event_id": event_id, "user_id": user_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        return _registration(cast(Mapping[str, object], row)) if row is not None else None

    async def oldest_waitlisted(self, event_id: UUID) -> Registration | None:
        row = (
            (
                await self._session.execute(
                    text(
                        f"""
                        SELECT {_REGISTRATION_FIELDS}
                        FROM talaqi.registrations AS registration
                        WHERE registration.event_id = :event_id
                          AND registration.state = 'waitlisted'
                        ORDER BY registration.waitlist_sequence, registration.id
                        FOR UPDATE
                        LIMIT 1
                        """  # noqa: S608 -- fixed fields; bound identifier
                    ),
                    {"event_id": event_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        return _registration(cast(Mapping[str, object], row)) if row is not None else None

    async def get_for_event(
        self,
        event_id: UUID,
        registration_id: UUID,
        *,
        for_update: bool,
    ) -> Registration | None:
        lock = "FOR UPDATE" if for_update else ""
        row = (
            (
                await self._session.execute(
                    text(
                        f"""
                        SELECT {_REGISTRATION_FIELDS}
                        FROM talaqi.registrations AS registration
                        WHERE registration.event_id = :event_id
                          AND registration.id = :registration_id
                        {lock}
                        """  # noqa: S608 -- fixed fields; bound identifiers
                    ),
                    {"event_id": event_id, "registration_id": registration_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        return _registration(cast(Mapping[str, object], row)) if row is not None else None

    async def list_attendees(
        self,
        event_id: UUID,
        *,
        state: RegistrationState | None,
        search: str | None,
        limit: int,
        after_created_at: datetime | None,
        after_id: UUID | None,
    ) -> list[Attendee]:
        rows = (
            (
                await self._session.execute(
                    text(
                        f"""
                        SELECT {_REGISTRATION_FIELDS}, profile.username, profile.display_name
                        FROM talaqi.registrations AS registration
                        JOIN talaqi.profiles AS profile ON profile.user_id = registration.user_id
                        WHERE registration.event_id = :event_id
                          AND (
                              CAST(:state AS text) IS NULL
                              OR registration.state = CAST(:state AS talaqi.registration_state)
                          )
                          AND (
                              CAST(:search AS text) IS NULL
                              OR lower(profile.username) LIKE :search ESCAPE '\\'
                              OR lower(profile.display_name) LIKE :search ESCAPE '\\'
                          )
                          AND (
                              CAST(:after_created_at AS timestamptz) IS NULL
                              OR (registration.created_at, registration.id)
                                 < (CAST(:after_created_at AS timestamptz), CAST(:after_id AS uuid))
                          )
                        ORDER BY registration.created_at DESC, registration.id DESC
                        LIMIT :limit
                        """  # noqa: S608 -- fixed fields; bound filter values
                    ),
                    {
                        "event_id": event_id,
                        "state": state,
                        "search": (
                            "%"
                            + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                            + "%"
                            if search is not None
                            else None
                        ),
                        "after_created_at": after_created_at,
                        "after_id": after_id,
                        "limit": limit,
                    },
                )
            )
            .mappings()
            .all()
        )
        return [
            Attendee(
                registration=_registration(cast(Mapping[str, object], row)),
                username=cast(str, row["username"]),
                display_name=cast(str, row["display_name"]),
            )
            for row in rows
        ]

    async def enqueue_attendee_export(
        self,
        event_id: UUID,
        request_id: UUID,
        *,
        state: RegistrationState | None,
        search: str | None,
        requested_at: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO talaqi.outbox_events (
                    id, aggregate_type, aggregate_id, event_type,
                    payload, deduplication_key, available_at
                ) VALUES (
                    :id, 'event', :event_id, 'attendees.export_requested',
                    jsonb_build_object(
                        'request_id', CAST(:request_id AS uuid),
                        'event_id', CAST(:event_id AS uuid),
                        'state', CAST(:state AS text),
                        'search', CAST(:search AS text)
                    ),
                    :deduplication_key, :requested_at
                )
                """
            ),
            {
                "id": generate_uuid7(),
                "event_id": event_id,
                "request_id": request_id,
                "state": state,
                "search": search,
                "deduplication_key": f"attendees.export:{request_id}",
                "requested_at": requested_at,
            },
        )

    async def attendee_summary(self, event_id: UUID) -> AttendeeSummary:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                    SELECT count(*) FILTER (WHERE seat_held)::integer AS held,
                           count(*) FILTER (WHERE state = 'confirmed')::integer AS confirmed,
                           count(*) FILTER (WHERE state = 'cash_pending')::integer AS cash_pending,
                           count(*) FILTER (WHERE state = 'waitlisted')::integer AS waitlisted,
                           count(*) FILTER (WHERE state = 'cancelled')::integer AS cancelled,
                           count(*) FILTER (WHERE state = 'expired')::integer AS expired
                    FROM talaqi.registrations
                    WHERE event_id = :event_id
                    """
                    ),
                    {"event_id": event_id},
                )
            )
            .mappings()
            .one()
        )
        return AttendeeSummary(
            held=cast(int, row["held"]),
            confirmed=cast(int, row["confirmed"]),
            cash_pending=cast(int, row["cash_pending"]),
            waitlisted=cast(int, row["waitlisted"]),
            cancelled=cast(int, row["cancelled"]),
            expired=cast(int, row["expired"]),
        )

    async def held_seat_count(self, event_id: UUID) -> int:
        count = await self._session.execute(
            text(
                """
                SELECT count(*) FROM talaqi.registrations
                WHERE event_id = :event_id AND seat_held
                """
            ),
            {"event_id": event_id},
        )
        return cast(int, count.scalar_one())

    async def next_waitlist_sequence(self, event_id: UUID) -> int:
        sequence = await self._session.execute(
            text(
                """
                SELECT coalesce(max(waitlist_sequence), 0) + 1
                FROM talaqi.registrations
                WHERE event_id = :event_id AND state = 'waitlisted'
                """
            ),
            {"event_id": event_id},
        )
        return cast(int, sequence.scalar_one())

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
    ) -> Registration:
        result = await self._session.execute(
            text(
                f"""
                INSERT INTO talaqi.registrations AS registration (
                    id, event_id, user_id, method, state, seat_held,
                    waitlist_sequence, cash_expires_at, confirmed_at
                ) VALUES (
                    :id, :event_id, :user_id,
                    CAST(:method AS talaqi.registration_method),
                    CAST(:state AS talaqi.registration_state), :seat_held,
                    :waitlist_sequence, :cash_expires_at, :confirmed_at
                )
                RETURNING {_REGISTRATION_FIELDS}
                """  # noqa: S608 -- fixed fields; bound values
            ),
            {
                "id": registration_id,
                "event_id": event_id,
                "user_id": user_id,
                "method": method,
                "state": state,
                "seat_held": seat_held,
                "waitlist_sequence": waitlist_sequence,
                "cash_expires_at": cash_expires_at,
                "confirmed_at": confirmed_at,
            },
        )
        row = result.mappings().one()
        await self._append_creation_records(
            registration_id=registration_id,
            command_id=command_id,
            command_hash=command_hash,
            event_id=event_id,
            user_id=user_id,
            state=state,
            request_id=request_id,
            occurred_at=occurred_at,
        )
        if state == "cash_pending" and cash_expires_at is not None:
            await self._enqueue_cash_expiry(
                registration_id=registration_id,
                event_id=event_id,
                available_at=cash_expires_at,
            )
        return _registration(cast(Mapping[str, object], row))

    async def _enqueue_cash_expiry(
        self,
        *,
        registration_id: UUID,
        event_id: UUID,
        available_at: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO talaqi.outbox_events (
                    id, aggregate_type, aggregate_id, event_type,
                    payload, deduplication_key, available_at
                ) VALUES (
                    :id, 'registration', :registration_id, 'registration.cash_expiry_due',
                    jsonb_build_object(
                        'registration_id', CAST(:registration_id AS uuid),
                        'event_id', CAST(:event_id AS uuid)
                    ),
                    :deduplication_key, :available_at
                )
                ON CONFLICT (deduplication_key) DO NOTHING
                """
            ),
            {
                "id": generate_uuid7(),
                "registration_id": registration_id,
                "event_id": event_id,
                "deduplication_key": f"registration.cash_expiry:{registration_id}",
                "available_at": available_at,
            },
        )

    async def _append_creation_records(
        self,
        *,
        registration_id: UUID,
        command_id: UUID,
        command_hash: bytes,
        event_id: UUID,
        user_id: UUID,
        state: RegistrationState,
        request_id: UUID,
        occurred_at: datetime,
    ) -> None:
        reason_code = "member_waitlisted" if state == "waitlisted" else "member_registered"
        await self._session.execute(
            text(
                """
                INSERT INTO talaqi.registration_transitions (
                    id, command_id, command_hash, registration_id,
                    actor_user_id, actor_kind, previous_state, new_state,
                    reason_code, request_id, occurred_at
                ) VALUES (
                    :id, :command_id, :command_hash, :registration_id,
                    :user_id, 'member', NULL,
                    CAST(:state AS talaqi.registration_state),
                    :reason_code, :request_id, :occurred_at
                )
                """
            ),
            {
                "id": generate_uuid7(),
                "command_id": command_id,
                "command_hash": command_hash,
                "registration_id": registration_id,
                "user_id": user_id,
                "state": state,
                "reason_code": reason_code,
                "request_id": request_id,
                "occurred_at": occurred_at,
            },
        )
        await self._session.execute(
            text(
                """
                INSERT INTO talaqi.outbox_events (
                    id, aggregate_type, aggregate_id, event_type,
                    payload, deduplication_key, available_at
                ) VALUES (
                    :id, 'registration', CAST(:registration_id AS uuid), :event_type,
                    jsonb_build_object(
                        'registration_id', CAST(:registration_id AS uuid),
                        'event_id', CAST(:event_id AS uuid),
                        'user_id', CAST(:user_id AS uuid),
                        'state', CAST(:state AS text)
                    ),
                    :deduplication_key, :occurred_at
                )
                """
            ),
            {
                "id": generate_uuid7(),
                "registration_id": registration_id,
                "event_id": event_id,
                "user_id": user_id,
                "state": state,
                "event_type": f"registration.{state}",
                "deduplication_key": f"registration.created:{registration_id}",
                "occurred_at": occurred_at,
            },
        )

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
        await self._session.execute(
            text(
                """
                INSERT INTO talaqi.outbox_events (
                    id, aggregate_type, aggregate_id, event_type,
                    payload, deduplication_key, available_at
                ) VALUES (
                    :id, 'registration', CAST(:registration_id AS uuid), :event_type,
                    jsonb_build_object(
                        'registration_id', CAST(:registration_id AS uuid),
                        'event_id', CAST(:event_id AS uuid),
                        'user_id', CAST(:user_id AS uuid),
                        'previous_state', CAST(:previous_state AS text),
                        'state', CAST(:state AS text),
                        'reason_code', CAST(:reason_code AS text)
                    ),
                    :deduplication_key, :occurred_at
                )
                """
            ),
            {
                "id": generate_uuid7(),
                "registration_id": current.id,
                "event_id": current.event_id,
                "user_id": current.user_id,
                "previous_state": current.state,
                "state": mutation.state,
                "reason_code": command.reason_code,
                "event_type": f"registration.{mutation.state}",
                "deduplication_key": f"registration.transition:{command.command_id}",
                "occurred_at": command.occurred_at,
            },
        )
        if mutation.state == "cash_pending" and mutation.cash_expires_at is not None:
            await self._enqueue_cash_expiry(
                registration_id=current.id,
                event_id=current.event_id,
                available_at=mutation.cash_expires_at,
            )
        return TransitionResult(
            registration=_registration(cast(Mapping[str, object], row)),
            transition=_transition(cast(Mapping[str, object], transition_row)),
        )
