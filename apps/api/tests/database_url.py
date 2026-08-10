from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from pathlib import Path

from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import text
from talaqi.db.engine import build_async_engine
from talaqi.db.safety import validate_test_database_url

ENVIRONMENT_VARIABLE = "TEST_DATABASE_URL"
LOCAL_ENV_FILE = ".env.test.local"


def resolve_test_database_url(
    root: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> SecretStr:
    environment = os.environ if environ is None else environ
    value = environment.get(ENVIRONMENT_VARIABLE)

    if value is None:
        env_path = root / LOCAL_ENV_FILE
        if not env_path.is_file():
            raise RuntimeError(
                f"Test database is not configured. Set {ENVIRONMENT_VARIABLE} to a disposable "
                f"test database URL or create the ignored local fallback {env_path}."
            )
        entries = [
            line
            for line in env_path.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith(f"{ENVIRONMENT_VARIABLE}=")
        ]
        if len(entries) != 1:
            raise RuntimeError(
                f"Expected exactly one {ENVIRONMENT_VARIABLE} setting in {env_path}."
            )
        value = entries[0].split("=", maxsplit=1)[1].strip().strip("\"'")

    if not value:
        raise RuntimeError(f"{ENVIRONMENT_VARIABLE} must not be empty.")

    secret = SecretStr(value)
    validate_test_database_url(secret)
    return secret


async def _drop_test_schema(database_url: SecretStr) -> None:
    engine = build_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA IF EXISTS talaqi CASCADE"))
            await connection.execute(text("DROP TABLE IF EXISTS public.alembic_version"))
    finally:
        await engine.dispose()


def reset_test_database_schema(database_url: SecretStr, root: Path) -> None:
    """Recreate the application schema after proving the target is test-only."""
    validate_test_database_url(database_url)
    asyncio.run(_drop_test_schema(database_url))
    command.upgrade(Config(str(root / "alembic.ini")), "head")
