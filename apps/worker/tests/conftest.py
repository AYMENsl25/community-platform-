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

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def worker_database_url() -> Iterator[SecretStr]:
    secret = resolve_test_database_url(ROOT)
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


@pytest.fixture(autouse=True)
def isolated_worker_database(worker_database_url: SecretStr) -> Iterator[None]:
    try:
        yield
    finally:
        reset_test_database_schema(worker_database_url, ROOT)


@pytest_asyncio.fixture
async def worker_engine(worker_database_url: SecretStr) -> AsyncIterator[AsyncEngine]:
    engine = build_async_engine(worker_database_url)
    try:
        yield engine
    finally:
        await engine.dispose()
