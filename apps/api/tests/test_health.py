from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import httpx
import pytest
from talaqi.config import Settings
from talaqi.health import ReadinessRegistry
from talaqi.main import create_app


def settings() -> Settings:
    return Settings.model_validate(
        {
            "environment": "test",
            "api_public_url": "http://localhost:8000",
            "web_public_url": "http://localhost:3000",
            "allowed_origins": ["http://localhost:3000"],
            "allowed_hosts": ["localhost"],
            "session_secret": "test-secret",
            "cookie_secure": False,
            "admin_mfa_required": False,
            "database_url": "postgresql://user:password@localhost/db",
            "s3_endpoint": "http://localhost:9000",
            "s3_bucket": "test",
            "s3_access_key": "access",
            "s3_secret_key": "secret",
            "smtp_host": "localhost",
            "smtp_port": 1025,
            "log_level": "INFO",
        }
    )


async def request(registry: ReadinessRegistry, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=create_app(settings(), registry))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        return await client.get(path)


async def request_app(app: object, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)  # pyright: ignore[reportArgumentType]
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        return await client.get(path)


@pytest.mark.asyncio
async def test_liveness_has_exact_contract() -> None:
    response = await request(ReadinessRegistry(), "/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_returns_ready_when_all_probes_pass() -> None:
    registry = ReadinessRegistry()
    registry.register("configuration", lambda: asyncio.sleep(0, result=True))

    response = await request(registry, "/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"configuration": "ok"}}


@pytest.mark.asyncio
async def test_default_readiness_includes_configuration_and_injected_database_probe() -> None:
    app = create_app(
        settings(),
        database_probe=lambda: asyncio.sleep(0, result=True),
        storage_probe=lambda: asyncio.sleep(0, result=True),
    )

    response = await request_app(app, "/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {
            "configuration": "ok",
            "database": "ok",
            "object_storage": "ok",
        },
    }


@pytest.mark.asyncio
async def test_default_database_readiness_fails_closed_without_internal_details() -> None:
    async def failing_database_probe() -> bool:
        raise RuntimeError("internal database diagnostic")

    app = create_app(
        settings(),
        database_probe=failing_database_probe,
        storage_probe=lambda: asyncio.sleep(0, result=False),
    )

    response = await request_app(app, "/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"configuration": "ok", "database": "failed", "object_storage": "failed"},
    }
    assert "internal" not in response.text
    assert "diagnostic" not in response.text


@pytest.mark.parametrize(
    "name",
    [
        "",
        "UPPERCASE",
        "has-hyphen",
        "has whitespace",
        "https://internal.example.com",
        "database:password",
        "a" * 65,
    ],
)
def test_readiness_rejects_unsafe_or_unstable_check_names(name: str) -> None:
    registry = ReadinessRegistry()

    with pytest.raises(ValueError, match="identifier"):
        registry.register(name, lambda: asyncio.sleep(0, result=True))


def test_readiness_accepts_stable_check_name_boundary() -> None:
    registry = ReadinessRegistry()

    registry.register("a" + "0" * 63, lambda: asyncio.sleep(0, result=True))


@pytest.mark.asyncio
async def test_readiness_isolates_false_exception_and_timeout_probes() -> None:
    async def raises_secret() -> bool:
        raise RuntimeError("postgresql://user:secret@internal/db")

    async def times_out() -> bool:
        await asyncio.sleep(1)
        return True

    probes: dict[str, Callable[[], Awaitable[bool]]] = {
        "passing": lambda: asyncio.sleep(0, result=True),
        "false": lambda: asyncio.sleep(0, result=False),
        "exception": raises_secret,
        "timeout": times_out,
    }
    registry = ReadinessRegistry(timeout_seconds=0.01)
    for name, probe in probes.items():
        registry.register(name, probe)

    response = await request(registry, "/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {
            "passing": "ok",
            "false": "failed",
            "exception": "failed",
            "timeout": "failed",
        },
    }
    assert "secret" not in response.text
    assert "internal" not in response.text


@pytest.mark.asyncio
async def test_readiness_propagates_cancellation() -> None:
    async def cancelled() -> bool:
        raise asyncio.CancelledError

    registry = ReadinessRegistry()
    registry.register("cancelled", cancelled)

    with pytest.raises(asyncio.CancelledError):
        await registry.check()


@pytest.mark.asyncio
async def test_no_product_or_api_v1_route_exists() -> None:
    app = create_app(settings(), ReadinessRegistry())
    paths = {path for route in app.routes if (path := getattr(route, "path", None)) is not None}

    assert not any(path.startswith("/api/v1") for path in paths)
    assert paths.intersection({"/events", "/clubs", "/profiles"}) == set()
