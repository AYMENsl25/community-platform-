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
from talaqi.regions.repository import RegionRepository
from talaqi.regions.service import RegionPolicyService

ROOT = Path(__file__).resolve().parents[4]


def _load_test_database_url() -> SecretStr:
    value = os.environ.get("TEST_DATABASE_URL")
    if value is None:
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
def region_test_database_url() -> Iterator[SecretStr]:
    secret = _load_test_database_url()
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
def region_migrated_database(region_test_database_url: SecretStr) -> None:
    del region_test_database_url
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")


@pytest_asyncio.fixture
async def region_engine(
    region_test_database_url: SecretStr, region_migrated_database: None
) -> AsyncIterator[AsyncEngine]:
    del region_migrated_database
    engine = build_async_engine(region_test_database_url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def region_session(region_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(region_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        transaction = await session.begin()
        try:
            yield session
        finally:
            if transaction.is_active:
                await transaction.rollback()


@pytest.fixture
def region_service(region_session: AsyncSession) -> RegionPolicyService:
    return RegionPolicyService(RegionRepository(region_session))
