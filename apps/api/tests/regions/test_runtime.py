from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import cast

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from talaqi.config import Settings
from talaqi.health import ReadinessRegistry
from talaqi.main import create_app
from talaqi.regions.routes import DatabaseSession
from talaqi.runtime import LazySessionFactory, SessionFactory


def _settings() -> Settings:
    database_url = (
        "postgresql+asyncpg://unused:unused@localhost:5432/unused_test"  # pragma: allowlist secret
    )
    return Settings.model_validate(
        {
            "environment": "test",
            "api_public_url": "http://localhost:8000",
            "web_public_url": "http://localhost:3000",
            "allowed_origins": ["http://localhost:3000"],
            "allowed_hosts": ["localhost"],
            "session_secret": "test-secret",  # pragma: allowlist secret
            "cookie_secure": False,
            "admin_mfa_required": False,
            "database_url": database_url,
            "s3_endpoint": "http://localhost:9000",
            "s3_bucket": "test",
            "s3_access_key": "access",
            "s3_secret_key": "secret",  # pragma: allowlist secret
            "smtp_host": "localhost",
            "smtp_port": 1025,
            "log_level": "DEBUG",
        }
    )


class FakeTransaction(AbstractAsyncContextManager[None]):
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> None:
        self._session.active = True

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        del exc_value, traceback
        self._session.active = False
        if exc_type is not None:
            self._session.events.append("rollback")
            return False
        self._session.events.append("commit")
        if self._session.fail_commit:
            raise RuntimeError("database commit failed")
        return False


class FakeSession:
    def __init__(self, events: list[str], *, fail_commit: bool = False) -> None:
        self.events = events
        self.fail_commit = fail_commit
        self.active = False

    def begin(self) -> FakeTransaction:
        return FakeTransaction(self)

    def in_transaction(self) -> bool:
        return self.active

    async def rollback(self) -> None:
        self.active = False
        self.events.append("rollback")

    async def close(self) -> None:
        self.events.append("close")


class FakeSessionFactory:
    def __init__(self, events: list[str], *, fail_commit: bool = False) -> None:
        self._events = events
        self._fail_commit = fail_commit

    def __call__(self) -> FakeSession:
        return FakeSession(self._events, fail_commit=self._fail_commit)


def _monitored_app(app: ASGIApp, events: list[str]) -> ASGIApp:
    async def monitored(scope: Scope, receive: Receive, send: Send) -> None:
        async def tracking_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                events.append("response")
            await send(message)

        await app(scope, receive, tracking_send)

    return monitored


async def _request_with_session(
    *, fail_commit: bool = False, fail_endpoint: bool = False
) -> tuple[httpx.Response, list[str]]:
    events: list[str] = []
    injected = cast(SessionFactory, FakeSessionFactory(events, fail_commit=fail_commit))
    app = create_app(_settings(), ReadinessRegistry(), session_factory=injected)

    @app.get("/__runtime-test")
    async def runtime_test(  # pyright: ignore[reportUnusedFunction]
        session: DatabaseSession,
    ) -> dict[str, bool]:
        del session
        if fail_endpoint:
            raise RuntimeError("endpoint failed")
        return {"ok": True}

    transport = httpx.ASGITransport(app=_monitored_app(app, events))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.get("/__runtime-test")
    return response, events


@pytest.mark.asyncio
async def test_success_commits_and_closes_before_response_transmission() -> None:
    response, events = await _request_with_session()

    assert response.status_code == 200
    assert events == ["commit", "close", "response"]


@pytest.mark.asyncio
async def test_commit_failure_is_a_secured_generic_500_and_closes() -> None:
    response, events = await _request_with_session(fail_commit=True)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "database" not in response.text
    assert events == ["commit", "close", "response"]


@pytest.mark.asyncio
async def test_endpoint_exception_rolls_back_and_closes_before_response() -> None:
    response, events = await _request_with_session(fail_endpoint=True)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "endpoint" not in response.text
    assert events == ["rollback", "close", "response"]


@pytest.mark.asyncio
async def test_injected_factory_is_not_disposed() -> None:
    settings_resolved = False

    def settings_factory() -> Settings:
        nonlocal settings_resolved
        settings_resolved = True
        return _settings()

    runtime = LazySessionFactory(
        settings_factory,
        cast(SessionFactory, FakeSessionFactory([])),
    )

    await runtime.close()

    assert settings_resolved is False
    assert isinstance(runtime.resolve()(), FakeSession)


class FakeEngine:
    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


@pytest.mark.asyncio
async def test_owned_engine_is_disposed_and_reset_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engines: list[FakeEngine] = []

    def build_engine(database_url: object) -> AsyncEngine:
        del database_url
        engine = FakeEngine()
        engines.append(engine)
        return cast(AsyncEngine, engine)

    def build_factory(engine: AsyncEngine) -> SessionFactory:
        del engine
        return cast(SessionFactory, FakeSessionFactory([]))

    monkeypatch.setattr("talaqi.runtime.build_async_engine", build_engine)
    monkeypatch.setattr("talaqi.runtime.build_session_factory", build_factory)
    runtime = LazySessionFactory(_settings)

    first = runtime.resolve()
    await runtime.close()
    second = runtime.resolve()

    assert first is not second
    assert [engine.disposed for engine in engines] == [True, False]
