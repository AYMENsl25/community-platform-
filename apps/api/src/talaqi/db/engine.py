from __future__ import annotations

from pydantic import SecretStr
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_INVALID_DATABASE_URL = "database URL must use the PostgreSQL asyncpg driver"


def build_async_engine(database_url: str | SecretStr) -> AsyncEngine:
    """Construct an asyncpg engine without opening a database connection."""
    raw_url = (
        database_url.get_secret_value() if isinstance(database_url, SecretStr) else database_url
    )
    try:
        url = make_url(raw_url)
    except ArgumentError:
        raise ValueError(_INVALID_DATABASE_URL) from None
    if url.drivername != "postgresql+asyncpg":
        raise ValueError(_INVALID_DATABASE_URL)
    return create_async_engine(url, echo=False, pool_pre_ping=True)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
