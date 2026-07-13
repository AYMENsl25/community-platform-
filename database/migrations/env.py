from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from pydantic import SecretStr
from sqlalchemy import Connection
from sqlalchemy.engine import make_url
from talaqi.db.engine import build_async_engine
from talaqi.db.metadata import metadata
from talaqi.db.safety import validate_test_database_url

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


def _test_database_url() -> SecretStr:
    database_url = SecretStr(os.environ.get("TEST_DATABASE_URL", ""))
    validate_test_database_url(database_url)
    return database_url


def run_migrations_offline() -> None:
    secret_url = _test_database_url()
    dialect_only_url = make_url(secret_url.get_secret_value()).set(
        username=None,
        password=None,
        host="localhost",
        port=None,
        database="offline",
    )
    context.configure(
        url=dialect_only_url.render_as_string(hide_password=True),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _run_online_migrations() -> None:
    engine = build_async_engine(_test_database_url())
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_run_migrations)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_online_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
