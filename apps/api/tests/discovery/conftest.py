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
from talaqi.db.safety import validate_test_database_url
from talaqi.discovery.fixtures import seed_discovery_fixtures

ROOT = Path(__file__).resolve().parents[4]


def _url() -> SecretStr:
    value = os.environ.get("TEST_DATABASE_URL")
    if value is None:
        entry = next(
            line
            for line in (ROOT / ".env.test.local").read_text(encoding="utf-8").splitlines()
            if line.startswith("TEST_DATABASE_URL=")
        )
        value = entry.split("=", 1)[1].strip().strip("\"'")
    secret = SecretStr(value)
    validate_test_database_url(secret)
    return secret


@pytest.fixture(scope="session")
def discovery_database_url() -> Iterator[SecretStr]:
    secret = _url()
    previous = os.environ.get("TEST_DATABASE_URL")
    os.environ["TEST_DATABASE_URL"] = secret.get_secret_value()
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    try:
        yield secret
    finally:
        if previous is None:
            os.environ.pop("TEST_DATABASE_URL", None)
        else:
            os.environ["TEST_DATABASE_URL"] = previous


@pytest_asyncio.fixture
async def discovery_engine(discovery_database_url: SecretStr) -> AsyncIterator[AsyncEngine]:
    engine = build_async_engine(discovery_database_url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def discovery_session(discovery_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(discovery_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session, session.begin():
        await seed_discovery_fixtures(session)
        yield session
        await session.rollback()
