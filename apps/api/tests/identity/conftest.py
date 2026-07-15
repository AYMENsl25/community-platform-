from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.db.engine import build_async_engine
from talaqi.db.safety import validate_test_database_url

ROOT = Path(__file__).resolve().parents[4]


def _database_url() -> SecretStr:
    value = os.environ.get("TEST_DATABASE_URL")
    if value is None:
        entries = [
            line
            for line in (ROOT / ".env.test.local").read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("TEST_DATABASE_URL=")
        ]
        value = entries[0].split("=", maxsplit=1)[1].strip().strip("\"'")
    secret = SecretStr(value)
    validate_test_database_url(secret)
    return secret


@pytest.fixture(scope="session")
def identity_database_url() -> Iterator[SecretStr]:
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
async def identity_engine(identity_database_url: SecretStr) -> AsyncIterator[AsyncEngine]:
    engine = build_async_engine(identity_database_url)
    try:
        yield engine
    finally:
        await engine.dispose()
