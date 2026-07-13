from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI, Response
from talaqi.config import Environment
from talaqi.db.identifiers import validate_uuid7
from talaqi.security.http import install_http_security

from .helpers import security_settings

EXPECTED = {
    "content-security-policy": (
        "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
    ),
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
}


def boundary_app(environment: Environment = Environment.TEST) -> tuple[FastAPI, list[int]]:
    app = FastAPI()
    resolutions: list[int] = []

    def resolve():  # type: ignore[no-untyped-def]
        resolutions.append(1)
        return security_settings(environment)

    install_http_security(app, resolve)
    install_http_security(app, resolve)

    @app.get("/ok")
    async def ok(response: Response) -> dict[str, bool]:  # pyright: ignore[reportUnusedFunction]
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Strict-Transport-Security"] = "max-age=1"
        response.headers["Access-Control-Allow-Origin"] = "*"
        return {"ok": True}

    @app.get("/cancel")
    async def cancel() -> None:  # pyright: ignore[reportUnusedFunction]
        raise asyncio.CancelledError

    return app, resolutions


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    app, _ = boundary_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as value:
        yield value


@pytest.mark.asyncio
async def test_settings_are_lazy_cached_and_installer_is_idempotent() -> None:
    app, resolutions = boundary_app()
    app.openapi()
    app.build_middleware_stack()
    assert resolutions == []

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        assert (await client.get("/ok")).status_code == 200
        assert (await client.get("/missing")).status_code == 404
    assert resolutions == [1]


@pytest.mark.asyncio
@pytest.mark.parametrize("environment", list(Environment))
async def test_exact_headers_and_production_only_hsts(environment: Environment) -> None:
    app, _ = boundary_app(environment)
    host = (
        "api.example.test:9443"
        if environment in {Environment.STAGING, Environment.PRODUCTION}
        else "localhost:8123"
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=f"http://{host}"
    ) as client:
        response = await client.get("/ok")
    for name, value in EXPECTED.items():
        assert response.headers[name] == value
    assert response.headers["x-frame-options"] == "DENY"
    if environment is Environment.PRODUCTION:
        assert (
            response.headers["strict-transport-security"] == "max-age=63072000; includeSubDomains"
        )
    else:
        assert "strict-transport-security" not in response.headers


@pytest.mark.asyncio
async def test_host_is_checked_before_cors_and_is_case_and_port_normalized(
    client: httpx.AsyncClient,
) -> None:
    allowed = await client.options(
        "/ok",
        headers={
            "Host": "LOCALHOST:9999",
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, X-CSRF-Token",
        },
    )
    assert allowed.status_code == 200
    validate_uuid7(allowed.headers["x-request-id"])
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert allowed.headers["access-control-allow-credentials"] == "true"
    assert (
        allowed.headers["access-control-allow-methods"]
        == "GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS"
    )
    assert (
        allowed.headers["access-control-allow-headers"]
        == "Accept, Content-Type, Idempotency-Key, X-CSRF-Token"
    )

    rejected = await client.options(
        "/ok",
        headers={
            "Host": "evil.example",
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers
    assert rejected.headers["x-frame-options"] == "DENY"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "host",
    ["attacker@localhost", "user:pass@localhost", "localhost:notaport"],
)
async def test_host_rejects_userinfo_and_malformed_authorities(
    client: httpx.AsyncClient, host: str
) -> None:
    response = await client.get("/ok", headers={"Host": host})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"
    validate_uuid7(response.headers["x-request-id"])
    for name, value in EXPECTED.items():
        assert response.headers[name] == value


@pytest.mark.asyncio
async def test_cors_simple_and_preflight_deny_are_explicit(client: httpx.AsyncClient) -> None:
    allowed = await client.get("/ok", headers={"Origin": "http://localhost:3000"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert allowed.headers["access-control-expose-headers"] == "X-Request-ID"
    assert allowed.headers["access-control-allow-credentials"] == "true"

    disallowed = await client.get("/ok", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in disallowed.headers
    assert "*" not in "\n".join(disallowed.headers.values())

    denied = await client.options(
        "/ok",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "TRACE",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


@pytest.mark.asyncio
async def test_cancellation_propagates_without_conversion(client: httpx.AsyncClient) -> None:
    with pytest.raises(asyncio.CancelledError):
        await client.get("/cancel")
