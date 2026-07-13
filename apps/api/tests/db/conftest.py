from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from talaqi.db.engine import build_async_engine
from talaqi.db.safety import validate_test_database_url

ROOT = Path(__file__).resolve().parents[4]


def _load_ignored_test_database_url() -> SecretStr:
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
    value = entries[0].split("=", maxsplit=1)[1].strip().strip("\"'")
    secret = SecretStr(value)
    validate_test_database_url(secret)
    return secret


@pytest.fixture(scope="session")
def test_database_url() -> Iterator[SecretStr]:
    secret = _load_ignored_test_database_url()
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
def migrated_database(test_database_url: SecretStr) -> None:
    validate_test_database_url(test_database_url)
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")


@pytest_asyncio.fixture
async def database_engine(
    test_database_url: SecretStr, migrated_database: None
) -> AsyncIterator[AsyncEngine]:
    del migrated_database
    engine = build_async_engine(test_database_url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def transaction_connection(
    database_engine: AsyncEngine,
) -> AsyncIterator[AsyncConnection]:
    async with database_engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            if transaction.is_active:
                await transaction.rollback()


@pytest_asyncio.fixture
async def db_session(transaction_connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(
        bind=transaction_connection,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    async with session_factory() as session:
        yield session
