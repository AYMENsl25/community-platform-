from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from uuid import UUID

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.db.engine import build_async_engine
from talaqi.db.identifiers import generate_uuid7
from talaqi.db.safety import validate_test_database_url

ROOT = Path(__file__).resolve().parents[4]


def _load_safe_test_database_url() -> SecretStr:
    environment_value = os.environ.get("TEST_DATABASE_URL")
    if environment_value:
        secret = SecretStr(environment_value)
        validate_test_database_url(secret)
        return secret
    entries = [
        line
        for line in (ROOT / ".env.test.local").read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("TEST_DATABASE_URL=")
    ]
    if len(entries) != 1:
        raise RuntimeError("expected exactly one ignored test database setting")
    secret = SecretStr(entries[0].split("=", maxsplit=1)[1].strip().strip("\"'"))
    validate_test_database_url(secret)
    return secret


@pytest.fixture(scope="session")
def platform_test_database_url() -> Iterator[SecretStr]:
    secret = _load_safe_test_database_url()
    previous = os.environ.get("TEST_DATABASE_URL")
    os.environ["TEST_DATABASE_URL"] = secret.get_secret_value()
    try:
        yield secret
    finally:
        if previous is None:
            os.environ.pop("TEST_DATABASE_URL", None)
        else:
            os.environ["TEST_DATABASE_URL"] = previous


@pytest.fixture(scope="session")
def platform_migrated_database(platform_test_database_url: SecretStr) -> None:
    validate_test_database_url(platform_test_database_url)
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")


@pytest_asyncio.fixture
async def platform_database_engine(
    platform_test_database_url: SecretStr, platform_migrated_database: None
) -> AsyncIterator[AsyncEngine]:
    del platform_migrated_database
    engine = build_async_engine(platform_test_database_url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def platform_session_factory(
    platform_database_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(platform_database_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def idempotency_actor(platform_database_engine: AsyncEngine) -> AsyncIterator[UUID]:
    actor_id = generate_uuid7()
    async with platform_database_engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO talaqi.users (
                    id, email, password_hash, terms_version, privacy_version, age_attested_at
                ) VALUES (
                    :id, :email, '$argon2id$test', 'test', 'test', clock_timestamp()
                )
                """
            ),
            {"id": actor_id, "email": f"idempotency-{actor_id}@example.test"},
        )
    try:
        yield actor_id
    finally:
        async with platform_database_engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM talaqi.users WHERE id = :actor_id"), {"actor_id": actor_id}
            )
