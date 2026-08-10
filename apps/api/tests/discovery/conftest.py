from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.db.engine import build_async_engine
from talaqi.discovery.fixtures import seed_discovery_fixtures

from apps.api.tests.database_url import reset_test_database_schema, resolve_test_database_url

ROOT = Path(__file__).resolve().parents[4]


def _url() -> SecretStr:
    return resolve_test_database_url(ROOT)


@pytest.fixture(scope="session")
def discovery_database_url() -> Iterator[SecretStr]:
    secret = _url()
    previous = os.environ.get("TEST_DATABASE_URL")
    os.environ["TEST_DATABASE_URL"] = secret.get_secret_value()
    reset_test_database_schema(secret, ROOT)
    try:
        yield secret
    finally:
        if previous is None:
            os.environ.pop("TEST_DATABASE_URL", None)
        else:
            os.environ["TEST_DATABASE_URL"] = previous


@pytest.fixture
def isolated_discovery_database(discovery_database_url: SecretStr) -> Iterator[None]:
    try:
        yield
    finally:
        reset_test_database_schema(discovery_database_url, ROOT)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    discovery_tests = Path(__file__).parent
    for item in items:
        if item.path.is_relative_to(discovery_tests):
            item.add_marker(pytest.mark.usefixtures("isolated_discovery_database"))


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
