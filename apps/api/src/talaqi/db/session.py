from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def transactional_session[SessionT: AsyncSession](
    factory: Callable[[], SessionT],
) -> AsyncGenerator[SessionT]:
    """Commit on success, roll back on failure, and always close the session."""
    session = factory()
    try:
        yield session
        await session.commit()
    except BaseException:
        await session.rollback()
        raise
    finally:
        await session.close()
