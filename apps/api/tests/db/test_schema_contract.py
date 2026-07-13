from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr
from sqlalchemy import text
from talaqi.db.engine import build_async_engine

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.asyncio
async def test_approved_schema_contract_sql_passes(
    test_database_url: SecretStr, migrated_database: None
) -> None:
    del migrated_database
    engine = build_async_engine(test_database_url)
    contract = (ROOT / "database" / "tests" / "schema_contract.sql").read_text(encoding="utf-8")
    try:
        async with engine.connect() as connection:
            raw_connection = await connection.get_raw_connection()
            driver_connection = raw_connection.driver_connection
            assert driver_connection is not None
            status = await driver_connection.execute(contract)  # pyright: ignore[reportAny]
            assert status == "SELECT 1"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_editable_resources_have_positive_integer_revision_contract(
    test_database_url: SecretStr, migrated_database: None
) -> None:
    del migrated_database
    engine = build_async_engine(test_database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    """
                    SELECT table_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'talaqi'
                      AND column_name = 'revision'
                      AND data_type = 'integer'
                    ORDER BY table_name
                    """
                )
            )
            rows = {row.table_name: row for row in result}
            assert set(rows) == {"clubs", "events", "platform_settings", "regional_policies"}
            for row in rows.values():
                assert row.data_type == "integer"
                assert row.is_nullable == "NO"
                assert row.column_default == "1"

            check_names = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT constraint_name
                            FROM information_schema.table_constraints
                            WHERE constraint_schema = 'talaqi'
                              AND constraint_type = 'CHECK'
                            """
                        )
                    )
                ).scalars()
            )
            assert {
                "regional_policies_revision_check",
                "clubs_revision_check",
                "events_revision_check",
                "platform_settings_revision_check",
            }.issubset(check_names)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_suspension_soft_deletion_utc_and_uuid_defaults_are_preserved(
    test_database_url: SecretStr, migrated_database: None
) -> None:
    del migrated_database
    engine = build_async_engine(test_database_url)
    try:
        async with engine.connect() as connection:
            special_columns = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT table_name || '.' || column_name
                            FROM information_schema.columns
                            WHERE table_schema = 'talaqi'
                              AND column_name IN (
                                'suspended_at', 'suspension_reason',
                                'deletion_requested_at', 'anonymized_at'
                              )
                            """
                        )
                    )
                ).scalars()
            )
            assert {
                "users.suspended_at",
                "users.suspension_reason",
                "users.deletion_requested_at",
                "users.anonymized_at",
                "clubs.suspended_at",
                "clubs.suspension_reason",
                "events.suspended_at",
                "events.suspension_reason",
            }.issubset(special_columns)

            non_utc_columns = (
                await connection.execute(
                    text(
                        """
                        SELECT table_name, column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'talaqi'
                          AND column_name LIKE '%\\_at' ESCAPE '\\'
                          AND data_type <> 'timestamp with time zone'
                        """
                    )
                )
            ).all()
            assert non_utc_columns == []

            uuid_id_count = (
                await connection.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM information_schema.columns
                        WHERE table_schema = 'talaqi'
                          AND column_name = 'id'
                          AND data_type = 'uuid'
                        """
                    )
                )
            ).scalar_one()
            invalid_uuid_defaults = (
                await connection.execute(
                    text(
                        """
                        SELECT table_name
                        FROM information_schema.columns
                        WHERE table_schema = 'talaqi'
                          AND column_name = 'id'
                          AND data_type = 'uuid'
                          AND column_default IS DISTINCT FROM 'uuidv7()'
                        """
                    )
                )
            ).all()
            assert uuid_id_count == 25
            assert invalid_uuid_defaults == []
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_enum_index_trigger_version_and_postgresql_18_invariants(
    test_database_url: SecretStr, migrated_database: None
) -> None:
    del migrated_database
    engine = build_async_engine(test_database_url)
    try:
        async with engine.connect() as connection:
            server_version = int(
                (await connection.execute(text("SHOW server_version_num"))).scalar_one()
            )
            assert 180000 <= server_version < 190000

            enum_names = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT t.typname
                            FROM pg_type AS t
                            JOIN pg_namespace AS n ON n.oid = t.typnamespace
                            WHERE n.nspname = 'talaqi' AND t.typtype = 'e'
                            """
                        )
                    )
                ).scalars()
            )
            assert {
                "user_status",
                "club_status",
                "event_status",
                "registration_method",
                "registration_state",
                "moderation_action",
            }.issubset(enum_names)

            index_names = set(
                (
                    await connection.execute(
                        text("SELECT indexname FROM pg_indexes WHERE schemaname = 'talaqi'")
                    )
                ).scalars()
            )
            assert {
                "uq_registrations_active_member_event",
                "uq_club_memberships_single_owner",
                "ix_outbox_claim",
            }.issubset(index_names)

            trigger_names = set(
                (
                    await connection.execute(
                        text("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal")
                    )
                ).scalars()
            )
            assert {
                "registration_transitions_immutable",
                "moderation_case_events_immutable",
                "audit_events_immutable",
            }.issubset(trigger_names)

            revision = (
                await connection.execute(text("SELECT version_num FROM public.alembic_version"))
            ).scalar_one()
            assert revision == "0001_closed_beta_baseline"
    finally:
        await engine.dispose()
