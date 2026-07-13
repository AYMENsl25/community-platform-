from __future__ import annotations

from collections.abc import AsyncIterator, Callable

from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from talaqi.config import Settings
from talaqi.db.engine import build_async_engine, build_session_factory

SessionFactory = async_sessionmaker[AsyncSession]
SettingsFactory = Callable[[], Settings]


class LazySessionFactory:
    """Application-owned database runtime that opens no connection during construction."""

    def __init__(
        self,
        settings_factory: SettingsFactory,
        session_factory: SessionFactory | None = None,
    ) -> None:
        self._settings_factory = settings_factory
        self._session_factory = session_factory
        self._engine: AsyncEngine | None = None

    def resolve(self) -> SessionFactory:
        if self._session_factory is None:
            settings = self._settings_factory()
            self._engine = build_async_engine(settings.database_url)
            self._session_factory = build_session_factory(self._engine)
        return self._session_factory

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


def install_runtime(
    application: FastAPI,
    settings_factory: SettingsFactory,
    session_factory: SessionFactory | None = None,
) -> LazySessionFactory:
    runtime = LazySessionFactory(settings_factory, session_factory)
    application.state.database_runtime = runtime
    application.state.session_factory_holder = runtime
    application.router.add_event_handler("shutdown", runtime.close)
    return runtime


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    runtime: LazySessionFactory = request.app.state.database_runtime
    session = runtime.resolve()()
    try:
        async with session.begin():
            yield session
    except BaseException:
        if session.in_transaction():
            await session.rollback()
        raise
    finally:
        await session.close()


__all__ = ["LazySessionFactory", "SessionFactory", "get_db_session", "install_runtime"]
