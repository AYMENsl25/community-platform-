from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from talaqi.db.identifiers import generate_uuid7
from talaqi.registrations import RegistrationRepository, RegistrationTransitionService
from talaqi.registrations.models import TransitionCommand

NOW = datetime(2026, 8, 2, 12, tzinfo=UTC)


async def _seed_cash_pending(session: AsyncSession) -> tuple[UUID, UUID]:
    user_id = generate_uuid7()
    event_id = generate_uuid7()
    registration_id = generate_uuid7()
    await session.execute(
        text(
            """
            INSERT INTO talaqi.users (
                id, email, password_hash, terms_version, privacy_version, age_attested_at
            ) VALUES (
                :user_id, :email, '$argon2id$test', '2026-07-11', '2026-07-11', :now
            )
            """
        ),
        {"user_id": user_id, "email": f"registration-{user_id}@example.test", "now": NOW},
    )
    await session.execute(
        text(
            """
            INSERT INTO talaqi.events (
                id, ownership_type, owner_user_id, title, description,
                category_id, country_id, city_id, start_at, end_at, time_zone,
                capacity, status, registration_method, cash_expiry_minutes,
                cancellation_cutoff_minutes, published_at
            )
            SELECT :event_id, 'independent', :user_id, 'Registration state event',
                   'A complete event used by registration repository tests.',
                   category.id, country.id, city.id, :start_at, :end_at,
                   city.time_zone, 10, 'published', 'cash_organizer_confirmed',
                   120, 60, :now
            FROM talaqi.categories AS category
            CROSS JOIN talaqi.countries AS country
            JOIN talaqi.cities AS city ON city.country_id = country.id
            WHERE category.slug = 'sports' AND country.code = 'TR'
              AND city.slug = 'istanbul'
            """
        ),
        {
            "event_id": event_id,
            "user_id": user_id,
            "start_at": NOW + timedelta(days=1),
            "end_at": NOW + timedelta(days=1, hours=2),
            "now": NOW,
        },
    )
    await session.execute(
        text(
            """
            INSERT INTO talaqi.registrations (
                id, event_id, user_id, method, state, seat_held, cash_expires_at
            ) VALUES (
                :registration_id, :event_id, :user_id,
                'cash_organizer_confirmed', 'cash_pending', true, :cash_expires_at
            )
            """
        ),
        {
            "registration_id": registration_id,
            "event_id": event_id,
            "user_id": user_id,
            "cash_expires_at": NOW - timedelta(minutes=1),
        },
    )
    return registration_id, user_id


def _expire_command(registration_id: UUID) -> TransitionCommand:
    return TransitionCommand(
        command_id=generate_uuid7(),
        registration_id=registration_id,
        target_state="expired",
        actor_user_id=None,
        actor_kind="system",
        reason_code="cash_deadline_elapsed",
        occurred_at=NOW,
        request_id=generate_uuid7(),
    )


@pytest.mark.asyncio
async def test_transition_updates_state_and_appends_complete_history_atomically(
    registration_session: AsyncSession,
) -> None:
    registration_id, _ = await _seed_cash_pending(registration_session)
    service = RegistrationTransitionService(RegistrationRepository(registration_session))

    result = await service.transition(_expire_command(registration_id))

    stored = (
        (
            await registration_session.execute(
                text(
                    """
                    SELECT registration.state::text, registration.seat_held,
                           registration.cash_expires_at, registration.expired_at,
                           transition.command_id, transition.command_hash,
                           transition.previous_state::text, transition.new_state::text,
                           transition.actor_kind, transition.reason_code,
                           transition.request_id, transition.occurred_at
                    FROM talaqi.registrations AS registration
                    JOIN talaqi.registration_transitions AS transition
                      ON transition.registration_id = registration.id
                    WHERE registration.id = :registration_id
                    """
                ),
                {"registration_id": registration_id},
            )
        )
        .mappings()
        .one()
    )
    assert result.registration.state == "expired"
    assert stored["state"] == "expired"
    assert stored["seat_held"] is False
    assert stored["cash_expires_at"] <= stored["expired_at"]
    assert stored["command_id"] == result.transition.command_id
    assert len(stored["command_hash"]) == 32
    assert stored["previous_state"] == "cash_pending"
    assert stored["new_state"] == "expired"
    assert stored["actor_kind"] == "system"
    assert stored["reason_code"] == "cash_deadline_elapsed"
    assert stored["request_id"] == result.transition.request_id
    assert stored["occurred_at"] == NOW


@pytest.mark.asyncio
async def test_persisted_command_replay_writes_one_history_row(
    registration_session: AsyncSession,
) -> None:
    registration_id, _ = await _seed_cash_pending(registration_session)
    service = RegistrationTransitionService(RegistrationRepository(registration_session))
    value = _expire_command(registration_id)

    first = await service.transition(value)
    replay = await service.transition(value)

    count = (
        await registration_session.execute(
            text(
                "SELECT count(*) FROM talaqi.registration_transitions "
                "WHERE command_id = :command_id"
            ),
            {"command_id": value.command_id},
        )
    ).scalar_one()
    assert replay == first
    assert count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE talaqi.registration_transitions SET reason_code = 'tampered' "
        "WHERE id = :transition_id",
        "DELETE FROM talaqi.registration_transitions WHERE id = :transition_id",
    ],
)
async def test_transition_history_remains_database_immutable(
    registration_session: AsyncSession,
    statement: str,
) -> None:
    registration_id, _ = await _seed_cash_pending(registration_session)
    result = await RegistrationTransitionService(
        RegistrationRepository(registration_session)
    ).transition(_expire_command(registration_id))

    savepoint = await registration_session.begin_nested()
    with pytest.raises(DBAPIError, match="append-only"):
        await registration_session.execute(text(statement), {"transition_id": result.transition.id})
    await savepoint.rollback()


@pytest.mark.asyncio
async def test_database_rejects_second_active_registration_for_member_event(
    registration_session: AsyncSession,
) -> None:
    registration_id, user_id = await _seed_cash_pending(registration_session)
    event_id = (
        await registration_session.execute(
            text("SELECT event_id FROM talaqi.registrations WHERE id = :id"),
            {"id": registration_id},
        )
    ).scalar_one()

    savepoint = await registration_session.begin_nested()
    with pytest.raises(DBAPIError, match="uq_registrations_active_member_event"):
        await registration_session.execute(
            text(
                """
                INSERT INTO talaqi.registrations (
                    id, event_id, user_id, method, state, seat_held,
                    waitlist_sequence
                ) VALUES (
                    :id, :event_id, :user_id, 'cash_organizer_confirmed',
                    'waitlisted', false, 2
                )
                """
            ),
            {
                "id": generate_uuid7(),
                "event_id": event_id,
                "user_id": user_id,
            },
        )
    await savepoint.rollback()
