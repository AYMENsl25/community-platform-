from __future__ import annotations

import asyncio

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.config import Settings
from talaqi.main import create_app
from talaqi.security import RateLimitDecision, RateLimitPolicy

EMAIL = "identity-route-test@example.com"
PASSWORD = "correct horse battery"  # pragma: allowlist secret


def identity_settings() -> Settings:
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
            "session_secret": "identity-test-session-secret",  # pragma: allowlist secret
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


def assert_session_cookies_cleared(response: httpx.Response, *, secure: bool) -> None:
    http_only = {"talaqi_access": True, "talaqi_refresh": True, "talaqi_csrf": False}
    cookies = response.headers.get_list("set-cookie")
    assert len(cookies) == 3
    assert {item.split("=", maxsplit=1)[0] for item in cookies} == set(http_only)
    for name, expected_http_only in http_only.items():
        item = next(value for value in cookies if value.startswith(f"{name}="))
        assert item.startswith(f'{name}=""')
        assert "expires=" in item.lower()
        assert "Max-Age=0" in item
        assert "Path=/" in item
        assert "SameSite=lax" in item
        assert ("Secure" in item) is secure
        assert ("HttpOnly" in item) is expected_http_only


@pytest.mark.asyncio
async def test_register_login_logout_are_safe_non_enumerating_and_cookie_scoped(
    identity_engine: AsyncEngine,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async with identity_engine.begin() as connection:
        await connection.execute(
            text("DELETE FROM talaqi.users WHERE email = :email"), {"email": EMAIL}
        )
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(identity_settings(), session_factory=factory)
    transport = httpx.ASGITransport(app=app)
    body = {
        "email": f"  {EMAIL.upper()} ",
        "password": PASSWORD,
        "age_attested": True,
        "terms_version": "2026-07-11",
        "privacy_version": "2026-07-11",
    }
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        created = await client.post("/api/v1/auth/register", json=body)
        duplicate = await client.post("/api/v1/auth/register", json=body)
        missing = await client.post(
            "/api/v1/auth/login", json={"identifier": "missing@example.com", "password": PASSWORD}
        )
        wrong = await client.post(
            "/api/v1/auth/login",
            json={
                "identifier": EMAIL,
                "password": "wrong password value",  # pragma: allowlist secret
            },
        )
        login = await client.post(
            "/api/v1/auth/login", json={"identifier": EMAIL, "password": PASSWORD}
        )
        access_cookie = login.cookies["talaqi_access"]
        csrf_cookie = login.cookies["talaqi_csrf"]
        logout = await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_cookie})
        repeated_logout = await client.post(
            "/api/v1/auth/logout", headers={"cookie": f"talaqi_access={access_cookie}"}
        )

    assert created.status_code == duplicate.status_code == 202
    assert created.json() == duplicate.json() == {"accepted": True}
    assert missing.status_code == wrong.status_code == 401
    assert missing.json()["error"]["code"] == wrong.json()["error"]["code"] == "invalid_credentials"
    assert PASSWORD not in repr((created.json(), missing.json(), wrong.json()))
    assert login.json() == {"authenticated": True, "email_verified": False, "status": "active"}
    cookie = login.headers["set-cookie"]
    assert "talaqi_access=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie
    assert "Secure" not in cookie
    assert logout.status_code == 200
    assert logout.json() == {"logged_out": True}
    assert_session_cookies_cleared(logout, secure=False)
    assert repeated_logout.status_code == 401
    assert "set-cookie" not in repeated_logout.headers

    async with identity_engine.connect() as connection:
        count = (
            await connection.execute(
                text("SELECT count(*) FROM talaqi.users WHERE email = :email"), {"email": EMAIL}
            )
        ).scalar_one()
        hashes = (
            await connection.execute(
                text(
                    """
                    SELECT refresh_token_hash, csrf_secret_hash
                    FROM talaqi.sessions s JOIN talaqi.users u ON u.id=s.user_id
                    WHERE u.email=:email
                    """
                ),
                {"email": EMAIL},
            )
        ).all()
    assert count == 1
    assert all(PASSWORD.encode() not in bytes(value) for row in hashes for value in row)
    captured = capsys.readouterr()
    assert PASSWORD not in captured.out
    assert PASSWORD not in captured.err


def test_identity_openapi_is_configuration_and_connection_free() -> None:
    document = create_app().openapi()
    assert set(document["paths"]) >= {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
    }
    assert set(document["paths"]["/api/v1/auth/register"]["post"]["responses"]) == {
        "202",
        "422",
        "429",
    }
    assert set(document["paths"]["/api/v1/auth/login"]["post"]["responses"]) == {
        "200",
        "401",
        "422",
        "429",
    }
    assert set(document["paths"]["/api/v1/auth/logout"]["post"]["responses"]) == {
        "200",
        "401",
        "403",
    }


class AlwaysDenyLimiter:
    async def consume(self, bucket_id: str, policy: RateLimitPolicy) -> RateLimitDecision:
        del bucket_id, policy
        return RateLimitDecision(False, 0, 1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "body"),
    [
        (
            "/api/v1/auth/register",
            {
                "email": "limited@example.com",
                "password": PASSWORD,
                "age_attested": True,
                "terms_version": "2026-07-11",
                "privacy_version": "2026-07-11",
            },
        ),
        ("/api/v1/auth/login", {"identifier": "missing@example.com", "password": PASSWORD}),
    ],
)
async def test_auth_routes_return_safe_429_before_identity_work(
    identity_engine: AsyncEngine,
    path: str,
    body: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def forbidden_work(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("rate limiting must run before password work")

    monkeypatch.setattr("talaqi.identity.passwords.PasswordService.hash", forbidden_work)
    monkeypatch.setattr("talaqi.identity.passwords.PasswordService.verify", forbidden_work)
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(
        identity_settings(), session_factory=factory, auth_rate_limiter=AlwaysDenyLimiter()
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        response = await client.post(path, json=body)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"


@pytest.mark.asyncio
async def test_logout_requires_an_authenticated_access_cookie(identity_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    transport = httpx.ASGITransport(app=create_app(identity_settings(), session_factory=factory))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "body", "cookie"),
    [
        ("/api/v1/auth/verification/request", {"email": "limited@example.com"}, None),
        ("/api/v1/auth/password-reset/request", {"email": "limited@example.com"}, None),
        ("/api/v1/auth/verification/confirm", {"token": "A" * 40}, None),
        (
            "/api/v1/auth/password-reset/confirm",
            {"token": "A" * 40, "new_password": PASSWORD},
            None,
        ),
        ("/api/v1/auth/refresh", None, "talaqi_refresh=" + "A" * 43),
    ],
)
async def test_recovery_and_refresh_limits_run_before_token_or_database_work(
    identity_engine: AsyncEngine,
    path: str,
    body: dict[str, object] | None,
    cookie: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def forbidden_work(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("rate limiting must run before token/session work")

    monkeypatch.setattr(
        "talaqi.identity.repository.IdentityRepository.find_user_by_email", forbidden_work
    )
    monkeypatch.setattr(
        "talaqi.identity.repository.IdentityRepository.lock_auth_token", forbidden_work
    )
    monkeypatch.setattr(
        "talaqi.identity.repository.IdentityRepository.find_refresh_session_for_update",
        forbidden_work,
    )
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(
        identity_settings(), session_factory=factory, auth_rate_limiter=AlwaysDenyLimiter()
    )
    headers = {"cookie": cookie} if cookie else None
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        response = await client.post(path, json=body, headers=headers)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"


@pytest.mark.asyncio
async def test_normalized_duplicate_registration_race_creates_one_account(
    identity_engine: AsyncEngine,
) -> None:
    email = "identity-race-test@example.com"
    async with identity_engine.begin() as connection:
        await connection.execute(
            text("DELETE FROM talaqi.users WHERE email = :email"), {"email": email}
        )
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    transport = httpx.ASGITransport(app=create_app(identity_settings(), session_factory=factory))
    bodies = [
        {
            "email": email.upper() if index == 0 else f" {email} ",
            "password": "correct horse battery",  # pragma: allowlist secret
            "age_attested": True,
            "terms_version": "2026-07-11",
            "privacy_version": "2026-07-11",
        }
        for index in range(2)
    ]
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        responses = await asyncio.gather(
            *(client.post("/api/v1/auth/register", json=body) for body in bodies)
        )
    assert [response.status_code for response in responses] == [202, 202]
    async with identity_engine.connect() as connection:
        count = (
            await connection.execute(
                text("SELECT count(*) FROM talaqi.users WHERE email = :email"), {"email": email}
            )
        ).scalar_one()
    assert count == 1
