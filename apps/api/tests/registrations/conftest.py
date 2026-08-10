from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.db.engine import build_async_engine

from apps.api.tests.database_url import resolve_test_database_url

ROOT = Path(__file__).resolve().parents[4]


def _database_url() -> SecretStr:
    return resolve_test_database_url(ROOT)


@pytest.fixture(scope="session")
def registration_database_url() -> Iterator[SecretStr]:
    secret = _database_url()
    previous = os.environ.get("TEST_DATABASE_URL")
    os.environ["TEST_DATABASE_URL"] = secret.get_secret_value()
    try:
        command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
        yield secret
    finally:
        if previous is None:
            os.environ.pop("TEST_DATABASE_URL", None)
        else:
            os.environ["TEST_DATABASE_URL"] = previous


@pytest_asyncio.fixture
async def registration_engine(
    registration_database_url: SecretStr,
) -> AsyncIterator[AsyncEngine]:
    engine = build_async_engine(registration_database_url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def registration_session(
    registration_engine: AsyncEngine,
) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(registration_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        transaction = await session.begin()
        try:
            yield session
        finally:
            if transaction.is_active:
                await transaction.rollback()
