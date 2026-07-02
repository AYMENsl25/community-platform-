from collections.abc import AsyncGenerator
import logging
from time import perf_counter
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import ExecutionContext
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = logging.getLogger("communiti.db")


engine = create_async_engine(
    settings.sqlalchemy_database_url,
    pool_pre_ping=True,
    poolclass=NullPool,
)


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(
    conn: Any,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: ExecutionContext,
    executemany: bool,
) -> None:
    context._communiti_query_start_time = perf_counter()  # type: ignore[attr-defined]


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(
    conn: Any,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: ExecutionContext,
    executemany: bool,
) -> None:
    started_at = getattr(context, "_communiti_query_start_time", None)
    if started_at is None:
        return
    duration_ms = round((perf_counter() - started_at) * 1000, 2)
    if duration_ms < settings.db_slow_query_threshold_ms:
        return
    logger.warning(
        "slow database query",
        extra={
            "duration_ms": duration_ms,
            "statement": " ".join(statement.split())[:500],
        },
    )


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
