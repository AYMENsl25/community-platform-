from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.db.identifiers import generate_uuid7

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.asyncio
async def test_registration_state_machine_schema_is_strict(
    registration_engine: AsyncEngine,
) -> None:
    async with registration_engine.connect() as connection:
        columns = {
            row["column_name"]: row["is_nullable"]
            for row in (
                await connection.execute(
                    text(
                        """
                        SELECT column_name, is_nullable
                        FROM information_schema.columns
                        WHERE table_schema = 'talaqi'
                          AND table_name = 'registration_transitions'
                          AND column_name IN ('command_id', 'command_hash', 'occurred_at')
                        """
                    )
                )
            ).mappings()
        }
        constraints = set(
            (
                await connection.execute(
                    text(
                        """
                        SELECT conname
                        FROM pg_constraint
                        WHERE connamespace = 'talaqi'::regnamespace
                          AND conrelid IN (
                              'talaqi.registrations'::regclass,
                              'talaqi.registration_transitions'::regclass
                          )
                        """
                    )
                )
            ).scalars()
        )
        indexes = set(
            (
                await connection.execute(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE schemaname = 'talaqi' "
                        "AND tablename IN ('registrations', 'registration_transitions')"
                    )
                )
            ).scalars()
        )
    assert columns == {
        "command_hash": "NO",
        "command_id": "NO",
        "occurred_at": "NO",
    }
    assert {
        "ck_registration_transitions_actor_shape",
        "ck_registration_transitions_command_hash",
        "ck_registration_transitions_reason_length",
        "ck_registrations_seat_state",
        "ck_registrations_waitlist_sequence_positive",
        "uq_registration_transitions_command_id",
    }.issubset(constraints)
    assert "uq_registrations_active_member_event" in indexes


@pytest.mark.asyncio
async def test_registration_migration_round_trip(registration_engine: AsyncEngine) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    try:
        await asyncio.to_thread(command.downgrade, config, "0008_event_publishing")
        async with registration_engine.connect() as connection:
            revision = (
                await connection.execute(text("SELECT version_num FROM public.alembic_version"))
            ).scalar_one()
            command_column = (
                await connection.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM information_schema.columns
                        WHERE table_schema = 'talaqi'
                          AND table_name = 'registration_transitions'
                          AND column_name = 'command_id'
                        """
                    )
                )
            ).scalar_one()
        assert revision == "0008_event_publishing"
        assert command_column == 0

        transition_id = generate_uuid7()
        user_id = generate_uuid7()
        event_id = generate_uuid7()
        registration_id = generate_uuid7()
        now = datetime(2026, 8, 2, 12, tzinfo=UTC)
        async with registration_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    INSERT INTO talaqi.users (
                        id, email, password_hash, terms_version,
                        privacy_version, age_attested_at
                    ) VALUES (
                        :user_id, :email, '$argon2id$test',
                        '2026-07-11', '2026-07-11', :now
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "email": f"migration-{user_id}@example.test",
                    "now": now,
                },
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO talaqi.events (
                        id, ownership_type, owner_user_id, title
                    ) VALUES (
                        :event_id, 'independent', :user_id, 'Migration history fixture'
                    )
                    """
                ),
                {"event_id": event_id, "user_id": user_id},
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO talaqi.registrations (
                        id, event_id, user_id, method, state,
                        seat_held, confirmed_at
                    ) VALUES (
                        :registration_id, :event_id, :user_id,
                        'free', 'confirmed', true, :now
                    )
                    """
                ),
                {
                    "registration_id": registration_id,
                    "event_id": event_id,
                    "user_id": user_id,
                    "now": now,
                },
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO talaqi.registration_transitions (
                        id, registration_id, actor_user_id, actor_kind,
                        previous_state, new_state, reason_code, created_at
                    ) VALUES (
                        :transition_id, :registration_id, :user_id, 'member',
                        NULL, 'confirmed', 'registration_created', :now
                    )
                    """
                ),
                {
                    "transition_id": transition_id,
                    "registration_id": registration_id,
                    "user_id": user_id,
                    "now": now,
                },
            )
    finally:
        await asyncio.to_thread(command.upgrade, config, "head")

    async with registration_engine.connect() as connection:
        row = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT version_num, transition.id, transition.command_id,
                               transition.command_hash, transition.occurred_at,
                               transition.created_at
                        FROM public.alembic_version
                        CROSS JOIN talaqi.registration_transitions AS transition
                        WHERE transition.id = :transition_id
                        """
                    ),
                    {"transition_id": transition_id},
                )
            )
            .mappings()
            .one()
        )
    assert row["version_num"] == "0012_communications"
    assert row["id"] == transition_id
    assert row["command_id"] is not None
    assert row["command_hash"] == bytes(32)
    assert row["occurred_at"] >= row["created_at"]
