from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.identity.sessions import AccessSessionCodec
from talaqi.main import create_app

from .test_routes import PASSWORD, assert_session_cookies_cleared, identity_settings


async def _registered_login(app: FastAPI, engine: AsyncEngine, email: str) -> httpx.Response:
    async with engine.begin() as connection:
        await connection.execute(
            text("DELETE FROM talaqi.users WHERE email=:email"), {"email": email}
        )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": PASSWORD,
                "age_attested": True,
                "terms_version": "2026-07-11",
                "privacy_version": "2026-07-11",
            },
        )
        return await client.post(
            "/api/v1/auth/login", json={"identifier": email, "password": PASSWORD}
        )


def _assert_session_cookies_set(response: httpx.Response, *, secure: bool) -> None:
    expected = {
        "talaqi_access": (900, True),
        "talaqi_refresh": (2_592_000, True),
        "talaqi_csrf": (2_592_000, False),
    }
    cookies = response.headers.get_list("set-cookie")
    assert len(cookies) == 3
    assert {item.split("=", maxsplit=1)[0] for item in cookies} == set(expected)
    for name, (max_age, http_only) in expected.items():
        item = next(value for value in cookies if value.startswith(f"{name}="))
        assert not item.startswith(f'{name}=""')
        assert f"Max-Age={max_age}" in item
        assert "Path=/" in item
        assert "SameSite=lax" in item
        assert ("Secure" in item) is secure
        assert ("HttpOnly" in item) is http_only


@pytest.mark.asyncio
async def test_login_sets_three_cookies_and_refresh_requires_bound_csrf(
    identity_engine: AsyncEngine,
) -> None:
    email = "session-cookie-flow@example.com"
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    settings = identity_settings().model_copy(update={"cookie_secure": True})
    app = create_app(settings, session_factory=factory)
    async with identity_engine.begin() as connection:
        await connection.execute(
            text("DELETE FROM talaqi.users WHERE email=:email"), {"email": email}
        )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://localhost"
    ) as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": PASSWORD,
                "age_attested": True,
                "terms_version": "2026-07-11",
                "privacy_version": "2026-07-11",
            },
        )
        login = await client.post(
            "/api/v1/auth/login", json={"identifier": email, "password": PASSWORD}
        )
        original_values = {
            name: login.cookies[name] for name in ("talaqi_access", "talaqi_refresh", "talaqi_csrf")
        }
        no_csrf = await client.post("/api/v1/auth/refresh")
        csrf = client.cookies.get("talaqi_csrf")
        refreshed = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf or ""})
        sessions = await client.get("/api/v1/auth/sessions")
    assert login.status_code == 200
    _assert_session_cookies_set(login, secure=True)
    assert no_csrf.status_code == 403
    assert refreshed.status_code == 200
    assert all(refreshed.cookies[name] != value for name, value in original_values.items())
    assert sessions.status_code == 200
    assert no_csrf.headers.get_list("set-cookie") == []
    assert sum(item["current"] for item in sessions.json()["sessions"]) == 1
    _assert_session_cookies_set(refreshed, secure=True)
    current = next(item for item in sessions.json()["sessions"] if item["current"])
    assert current["last_used_at"] is not None


@pytest.mark.asyncio
async def test_owned_cross_user_and_all_session_revocation_are_safe(
    identity_engine: AsyncEngine,
) -> None:
    email = "owned-session-revocation@example.com"
    cross_email = "cross-user-session-revocation@example.com"
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(identity_settings(), session_factory=factory)
    first_login = await _registered_login(app, identity_engine, email)
    cross_login = await _registered_login(app, identity_engine, cross_email)
    cross_session_id = (
        AccessSessionCodec("identity-test-session-secret")
        .decode(cross_login.cookies["talaqi_access"])
        .session_id
    )
    async with (
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as first,
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as second,
    ):
        first.cookies.update(first_login.cookies)
        await second.post("/api/v1/auth/login", json={"identifier": email, "password": PASSWORD})
        listing = await first.get("/api/v1/auth/sessions")
        other = next(item for item in listing.json()["sessions"] if not item["current"])
        csrf = first.cookies["talaqi_csrf"]
        revoked = await first.delete(
            f"/api/v1/auth/sessions/{other['id']}", headers={"X-CSRF-Token": csrf}
        )
        cross_denied = await first.delete(
            f"/api/v1/auth/sessions/{cross_session_id}", headers={"X-CSRF-Token": csrf}
        )
        unknown_denied = await first.delete(
            f"/api/v1/auth/sessions/{uuid4()}", headers={"X-CSRF-Token": csrf}
        )
        all_revoked = await first.delete("/api/v1/auth/sessions", headers={"X-CSRF-Token": csrf})
    assert revoked.status_code == 200
    async with identity_engine.connect() as connection:
        cross_revoked_at = (
            await connection.execute(
                text("SELECT revoked_at FROM talaqi.sessions WHERE id=:id"),
                {"id": cross_session_id},
            )
        ).scalar_one()
    assert cross_denied.status_code == unknown_denied.status_code == 404
    assert {
        key: value for key, value in cross_denied.json()["error"].items() if key != "request_id"
    } == {
        key: value for key, value in unknown_denied.json()["error"].items() if key != "request_id"
    }
    assert cross_denied.headers.get_list("set-cookie") == []
    assert unknown_denied.headers.get_list("set-cookie") == []
    assert cross_revoked_at is None
    assert all_revoked.status_code == 200
    assert_session_cookies_cleared(all_revoked, secure=False)


@pytest.mark.asyncio
async def test_current_session_delete_revokes_row_and_clears_all_transport_cookies(
    identity_engine: AsyncEngine,
) -> None:
    email = "delete-current-session@example.com"
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    settings = identity_settings().model_copy(update={"cookie_secure": True})
    app = create_app(settings, session_factory=factory)
    login = await _registered_login(app, identity_engine, email)
    access = login.cookies["talaqi_access"]
    refresh = login.cookies["talaqi_refresh"]
    csrf = login.cookies["talaqi_csrf"]
    cookie = f"talaqi_access={access}; talaqi_refresh={refresh}; talaqi_csrf={csrf}"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://localhost"
    ) as client:
        listing = await client.get("/api/v1/auth/sessions", headers={"cookie": cookie})
        current = next(item for item in listing.json()["sessions"] if item["current"])
        deleted = await client.delete(
            f"/api/v1/auth/sessions/{current['id']}",
            headers={"cookie": cookie, "X-CSRF-Token": csrf},
        )
    async with identity_engine.connect() as connection:
        revoked_at = (
            await connection.execute(
                text("SELECT revoked_at FROM talaqi.sessions WHERE id=:id"),
                {"id": current["id"]},
            )
        ).scalar_one()
    assert deleted.status_code == 200
    assert revoked_at is not None
    assert_session_cookies_cleared(deleted, secure=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["logout", "delete_one", "delete_all"])
async def test_missing_and_mismatched_csrf_never_mutate_sessions(
    identity_engine: AsyncEngine, operation: str
) -> None:
    email = f"csrf-{operation.replace('_', '-')}@example.com"
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(identity_settings(), session_factory=factory)
    first_login = await _registered_login(app, identity_engine, email)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as second_client:
        second_login = await second_client.post(
            "/api/v1/auth/login", json={"identifier": email, "password": PASSWORD}
        )
    access = first_login.cookies["talaqi_access"]
    refresh = first_login.cookies["talaqi_refresh"]
    csrf = first_login.cookies["talaqi_csrf"]
    cookie = f"talaqi_access={access}; talaqi_refresh={refresh}; talaqi_csrf={csrf}"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        listing = await client.get("/api/v1/auth/sessions", headers={"cookie": cookie})
        target = next(item for item in listing.json()["sessions"] if not item["current"])
        if operation == "logout":
            path, method = "/api/v1/auth/logout", client.post
        elif operation == "delete_one":
            path, method = f"/api/v1/auth/sessions/{target['id']}", client.delete
        else:
            path, method = "/api/v1/auth/sessions", client.delete
        missing = await method(path, headers={"cookie": cookie})
        mismatch = await method(
            path, headers={"cookie": cookie, "X-CSRF-Token": "wrong-csrf-value"}
        )
    async with identity_engine.connect() as connection:
        active = (
            await connection.execute(
                text(
                    """SELECT count(*) FROM talaqi.sessions s
                    JOIN talaqi.users u ON u.id=s.user_id
                    WHERE u.email=:email AND s.revoked_at IS NULL"""
                ),
                {"email": email},
            )
        ).scalar_one()
    assert first_login.status_code == second_login.status_code == 200
    assert missing.status_code == mismatch.status_code == 403
    assert active == 2
    assert missing.headers.get_list("set-cookie") == []
    assert mismatch.headers.get_list("set-cookie") == []
