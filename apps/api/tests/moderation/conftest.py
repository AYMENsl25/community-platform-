from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.db.engine import build_async_engine

from apps.api.tests.database_url import reset_test_database_schema, resolve_test_database_url

ROOT = Path(__file__).resolve().parents[4]


def _database_url() -> SecretStr:
    return resolve_test_database_url(ROOT)


@pytest.fixture(scope="session")
def moderation_database_url() -> Iterator[SecretStr]:
    secret = _database_url()
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
def isolated_moderation_database(moderation_database_url: SecretStr) -> Iterator[None]:
    try:
        yield
    finally:
        reset_test_database_schema(moderation_database_url, ROOT)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    moderation_tests = Path(__file__).parent
    for item in items:
        if item.path.is_relative_to(moderation_tests):
            item.add_marker(pytest.mark.usefixtures("isolated_moderation_database"))


@pytest_asyncio.fixture
async def moderation_engine(
    moderation_database_url: SecretStr,
) -> AsyncIterator[AsyncEngine]:
    engine = build_async_engine(moderation_database_url)
    try:
        yield engine
    finally:
        await engine.dispose()
