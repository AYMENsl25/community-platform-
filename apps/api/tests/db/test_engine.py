from __future__ import annotations

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from talaqi.db.engine import build_async_engine, build_session_factory


@pytest.mark.asyncio
async def test_engine_and_factory_construction_is_side_effect_free_and_secret_safe() -> None:
    password = "construction-only-sensitive-password"
    engine = build_async_engine(
        SecretStr(f"postgresql+asyncpg://test_user:{password}@127.0.0.1:1/talaqi_test")
    )

    try:
        session_factory = build_session_factory(engine)

        assert engine.echo is False
        assert engine.pool._pre_ping is True  # pyright: ignore[reportPrivateUsage]
        assert password not in str(engine.url)
        assert password not in repr(engine)
        assert session_factory.class_ is AsyncSession
        assert session_factory.kw["expire_on_commit"] is False
    finally:
        await engine.dispose()


def test_invalid_driver_error_does_not_expose_password_or_full_url() -> None:
    password = "supplied-construction-password"
    full_url = f"postgresql://test_user:{password}@127.0.0.1:5433/talaqi_test"

    with pytest.raises(ValueError, match="asyncpg") as error:
        build_async_engine(SecretStr(full_url))

    diagnostic = f"{error.value!s} {error.value!r}"
    assert password not in diagnostic
    assert full_url not in diagnostic


@pytest.mark.asyncio
async def test_connection_failure_does_not_expose_password_or_full_url() -> None:
    password = "supplied-connection-password"
    full_url = f"postgresql+asyncpg://test_user:{password}@127.0.0.1:1/talaqi_test"
    engine = build_async_engine(SecretStr(full_url))

    try:
        try:
            async with engine.connect():
                pytest.fail("the non-listening test port unexpectedly accepted a connection")
        except Exception as error:
            diagnostic = f"{error!s} {error!r} {engine!r}"
            assert password not in diagnostic
            assert full_url not in diagnostic
    finally:
        await engine.dispose()
