from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.db.session import transactional_session

_TABLE = "talaqi.persistence_session_contract"


class TrackingAsyncSession(AsyncSession):
    close_called: bool = False

    async def close(self) -> None:
        self.close_called = True
        await super().close()


async def _prepare_table(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(f"CREATE TABLE IF NOT EXISTS {_TABLE} (value integer NOT NULL)")
        )
        await connection.execute(text(f"TRUNCATE TABLE {_TABLE}"))


async def _drop_table(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(text(f"DROP TABLE IF EXISTS {_TABLE}"))


async def _row_count(engine: AsyncEngine) -> int:
    async with engine.connect() as connection:
        return (await connection.execute(text(f"SELECT count(*) FROM {_TABLE}"))).scalar_one()


async def _insert_then_fail(
    factory: async_sessionmaker[TrackingAsyncSession],
    tracked_sessions: list[TrackingAsyncSession],
) -> None:
    async with transactional_session(factory) as session:
        tracked_sessions.append(session)
        await session.execute(text(f"INSERT INTO {_TABLE} (value) VALUES (2)"))
        raise RuntimeError("expected failure")


@pytest.mark.asyncio
async def test_transactional_session_commits_on_success_and_always_closes(
    database_engine: AsyncEngine,
) -> None:
    await _prepare_table(database_engine)
    factory = async_sessionmaker(
        database_engine,
        class_=TrackingAsyncSession,
        expire_on_commit=False,
    )
    tracked_session: TrackingAsyncSession | None = None
    try:
        async with transactional_session(factory) as session:
            tracked_session = session
            await session.execute(text(f"INSERT INTO {_TABLE} (value) VALUES (1)"))

        assert await _row_count(database_engine) == 1
        assert tracked_session.close_called is True
    finally:
        await _drop_table(database_engine)


@pytest.mark.asyncio
async def test_transactional_session_rolls_back_and_reraises_on_failure(
    database_engine: AsyncEngine,
) -> None:
    await _prepare_table(database_engine)
    factory = async_sessionmaker(
        database_engine,
        class_=TrackingAsyncSession,
        expire_on_commit=False,
    )
    tracked_sessions: list[TrackingAsyncSession] = []
    try:
        with pytest.raises(RuntimeError, match="expected failure"):
            await _insert_then_fail(factory, tracked_sessions)

        assert await _row_count(database_engine) == 0
        assert tracked_sessions[0].close_called is True
    finally:
        await _drop_table(database_engine)


@pytest.mark.asyncio
async def test_nested_transaction_fixture_allows_commit_inside_outer_rollback(
    db_session: AsyncSession,
) -> None:
    await db_session.execute(text(f"CREATE TABLE {_TABLE} (value integer NOT NULL)"))
    await db_session.commit()
    await db_session.execute(text(f"INSERT INTO {_TABLE} (value) VALUES (3)"))
    await db_session.commit()

    count = (await db_session.execute(text(f"SELECT count(*) FROM {_TABLE}"))).scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test_outer_rollback_fixture_isolates_the_previous_test(
    database_engine: AsyncEngine,
) -> None:
    async with database_engine.connect() as connection:
        table_exists = (
            await connection.execute(text(f"SELECT to_regclass('{_TABLE}') IS NOT NULL"))
        ).scalar_one()

    assert table_exists is False
