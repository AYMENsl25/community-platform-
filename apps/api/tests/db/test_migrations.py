from __future__ import annotations

import asyncio
import os
import runpy
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import SecretStr
from sqlalchemy import text
from talaqi.db.engine import build_async_engine

ROOT = Path(__file__).resolve().parents[4]
REQUIRED_TABLES = {
    "schema_revisions",
    "users",
    "profiles",
    "sessions",
    "auth_tokens",
    "countries",
    "cities",
    "categories",
    "regional_policies",
    "media_assets",
    "clubs",
    "club_memberships",
    "club_join_requests",
    "events",
    "event_invite_tokens",
    "saved_events",
    "registrations",
    "registration_transitions",
    "announcements",
    "event_updates",
    "notifications",
    "notification_deliveries",
    "outbox_events",
    "moderation_cases",
    "moderation_case_events",
    "audit_events",
    "idempotency_keys",
    "platform_settings",
    "user_mfa_factors",
}


def test_alembic_has_exactly_one_immutable_baseline_head() -> None:
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))

    assert scripts.get_heads() == ["0001_closed_beta_baseline"]


def test_baseline_checksum_is_stable_across_platform_line_endings() -> None:
    revision_path = ROOT / "database" / "migrations" / "versions" / "0001_closed_beta_baseline.py"
    namespace = runpy.run_path(str(revision_path))
    canonical_payload = cast(Callable[[bytes], bytes], namespace["_canonical_payload"])
    lf_payload = b"first\nsecond\n"
    crlf_payload = b"first\r\nsecond\r\n"

    assert canonical_payload(lf_payload) == canonical_payload(crlf_payload)


def test_alembic_rejects_non_test_target_without_exposing_the_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    password = "supplied-non-test-password"
    unsafe_url = f"postgresql+asyncpg://talaqi:{password}@127.0.0.1:5432/TALAQI"
    monkeypatch.setenv("TEST_DATABASE_URL", unsafe_url)

    with pytest.raises(ValueError, match="explicit local test database") as error:
        command.current(Config(str(ROOT / "alembic.ini")))

    diagnostic = f"{error.value!s} {error.value!r}"
    assert password not in diagnostic
    assert unsafe_url not in diagnostic
    assert os.environ["TEST_DATABASE_URL"] == unsafe_url


def test_offline_upgrade_emits_baseline_without_connection_details(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    password = "supplied-offline-password"
    offline_url = f"postgresql+asyncpg://test_user:{password}@127.0.0.1:5433/offline_test"
    monkeypatch.setenv("TEST_DATABASE_URL", offline_url)

    command.upgrade(Config(str(ROOT / "alembic.ini")), "head", sql=True)

    captured = capsys.readouterr()
    output = f"{captured.out}\n{captured.err}"
    assert "CREATE SCHEMA talaqi" in output
    assert "CREATE FUNCTION set_updated_at" in output
    assert password not in output
    assert offline_url not in output


async def _reset_safe_test_schema(database_url: SecretStr) -> None:
    engine = build_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA IF EXISTS talaqi CASCADE"))
            await connection.execute(text("DROP TABLE IF EXISTS public.alembic_version"))
    finally:
        await engine.dispose()


async def _schema_state(database_url: SecretStr) -> tuple[set[str], str | None]:
    engine = build_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            table_names = set(
                (
                    await connection.execute(
                        text("SELECT tablename FROM pg_tables WHERE schemaname = 'talaqi'")
                    )
                ).scalars()
            )
            revision = (
                await connection.execute(text("SELECT version_num FROM public.alembic_version"))
            ).scalar_one_or_none()
            return table_names, revision
    finally:
        await engine.dispose()


async def _base_state(database_url: SecretStr) -> tuple[bool, int]:
    engine = build_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            schema_exists = (
                await connection.execute(text("SELECT to_regnamespace('talaqi') IS NOT NULL"))
            ).scalar_one()
            revision_count = (
                await connection.execute(text("SELECT count(*) FROM public.alembic_version"))
            ).scalar_one()
            return schema_exists, revision_count
    finally:
        await engine.dispose()


async def _server_uuid_version(database_url: SecretStr) -> int | None:
    engine = build_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            identifier = (await connection.execute(text("SELECT uuidv7()"))).scalar_one()
            return identifier.version
    finally:
        await engine.dispose()


def test_clean_upgrade_downgrade_and_reupgrade_against_postgresql_18(
    test_database_url: SecretStr,
) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    asyncio.run(_reset_safe_test_schema(test_database_url))

    command.upgrade(config, "head")
    table_names, revision = asyncio.run(_schema_state(test_database_url))
    assert table_names == REQUIRED_TABLES
    assert revision == "0001_closed_beta_baseline"
    assert asyncio.run(_server_uuid_version(test_database_url)) == 7

    command.downgrade(config, "base")
    schema_exists, revision_count = asyncio.run(_base_state(test_database_url))
    assert schema_exists is False
    assert revision_count == 0

    command.upgrade(config, "head")
    table_names, revision = asyncio.run(_schema_state(test_database_url))
    assert table_names == REQUIRED_TABLES
    assert revision == "0001_closed_beta_baseline"
