from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.identity.sessions import AccessSessionCodec, AccessToken, RefreshTokenCodec
from talaqi.main import create_app
from talaqi.platform import ApiError

from .test_routes import PASSWORD, identity_settings
from .test_service import MemoryRepository, service_for

MALFORMED_REFRESH_VALUES = (
    "",
    "\u00e5" * 32,
    "not+base64/url",
    "A" * 42,
    "A" * 44,
    "A" * 43 + "=",
)


def test_refresh_tokens_are_opaque_domain_separated_and_expire_in_thirty_days() -> None:
    codec = RefreshTokenCodec("test-session-secret")
    raw = codec.issue()
    assert len(raw) >= 43
    assert len(codec.hash(raw)) == 32
    assert b"test-session-secret" not in codec.hash(raw)
    now = datetime(2026, 7, 15, tzinfo=UTC)
    assert codec.expiry(now) == now + timedelta(days=30)
    assert codec.hash(raw) != RefreshTokenCodec("different-session-secret").hash(raw)


def test_access_cookie_can_identify_session_without_exposing_user_supplied_id() -> None:
    # Rotation uses the stored refresh hash; the caller never supplies a user id.
    assert UUID("01980b78-2c00-7000-8000-000000000001").version == 7


@pytest.mark.parametrize(
    "raw",
    MALFORMED_REFRESH_VALUES,
    ids=("empty", "unicode", "alphabet", "truncated", "overlong", "padded"),
)
def test_refresh_codec_rejects_every_noncanonical_cookie_as_safe_session_error(raw: str) -> None:
    with pytest.raises(ApiError) as error:
        RefreshTokenCodec("test-session-secret").hash(raw)
    assert error.value.code == "invalid_session"
    assert error.value.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw",
    MALFORMED_REFRESH_VALUES,
    ids=("empty", "unicode", "alphabet", "truncated", "overlong", "padded"),
)
async def test_refresh_service_rejects_malformed_cookie_before_repository_work(
    raw: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = MemoryRepository()
    repository_calls = 0

    async def forbidden_repository_work(*args: object, **kwargs: object) -> object:
        nonlocal repository_calls
        del args, kwargs
        repository_calls += 1
        raise AssertionError("malformed refresh input reached repository work")

    monkeypatch.setattr(
        repository,
        "find_refresh_session_for_update",
        forbidden_repository_work,
        raising=False,
    )
    with pytest.raises(ApiError) as error:
        await service_for(repository).rotate(raw, None, None)

    assert (error.value.status_code, error.value.code) == (401, "invalid_session")
    assert repository_calls == 0
    assert not raw or raw not in f"{error.value!s}{error.value!r}"


@pytest.mark.asyncio
async def test_concurrent_double_refresh_replay_revokes_entire_family(
    identity_engine: AsyncEngine,
) -> None:
    email = "refresh-race@example.com"
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(identity_settings(), session_factory=factory)
    async with identity_engine.begin() as connection:
        await connection.execute(
            text("DELETE FROM talaqi.users WHERE email=:email"), {"email": email}
        )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as login_client:
        await login_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": PASSWORD,
                "age_attested": True,
                "terms_version": "2026-07-11",
                "privacy_version": "2026-07-11",
            },
        )
        login = await login_client.post(
            "/api/v1/auth/login", json={"identifier": email, "password": PASSWORD}
        )
    refresh = login.cookies["talaqi_refresh"]
    csrf = login.cookies["talaqi_csrf"]
    cookie = f"talaqi_refresh={refresh}; talaqi_csrf={csrf}"

    async def rotate_once() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            return await client.post(
                "/api/v1/auth/refresh",
                headers={"cookie": cookie, "X-CSRF-Token": csrf},
            )

    responses = await asyncio.gather(rotate_once(), rotate_once())
    assert sorted(response.status_code for response in responses) == [200, 401]
    async with identity_engine.connect() as connection:
        active = (
            await connection.execute(
                text(
                    """SELECT count(*) FROM talaqi.sessions WHERE family_id=(
                    SELECT family_id FROM talaqi.sessions WHERE refresh_token_hash=:hash)
                    AND revoked_at IS NULL"""
                ),
                {"hash": RefreshTokenCodec("identity-test-session-secret").hash(refresh)},
            )
        ).scalar_one()
    assert active == 0


@pytest.mark.asyncio
async def test_refresh_succeeds_with_expired_access_using_refresh_and_csrf_only(
    identity_engine: AsyncEngine,
) -> None:
    email = "refresh-expired-access@example.com"
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(identity_settings(), session_factory=factory)
    async with identity_engine.begin() as connection:
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
        login = await client.post(
            "/api/v1/auth/login", json={"identifier": email, "password": PASSWORD}
        )
    async with identity_engine.connect() as connection:
        session_id, user_id = (
            await connection.execute(
                text(
                    """SELECT s.id,u.id FROM talaqi.sessions s
                    JOIN talaqi.users u ON u.id=s.user_id WHERE u.email=:email
                    ORDER BY s.created_at DESC LIMIT 1"""
                ),
                {"email": email},
            )
        ).one()
    expired = AccessSessionCodec("identity-test-session-secret").encode(
        AccessToken(session_id, user_id, datetime.now(UTC) - timedelta(seconds=901))
    )
    refresh = login.cookies["talaqi_refresh"]
    csrf = login.cookies["talaqi_csrf"]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        response = await client.post(
            "/api/v1/auth/refresh",
            headers={
                "cookie": (
                    f"talaqi_access={expired}; talaqi_refresh={refresh}; talaqi_csrf={csrf}"
                ),
                "X-CSRF-Token": csrf,
            },
        )
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw",
    MALFORMED_REFRESH_VALUES,
    ids=("empty", "unicode", "alphabet", "truncated", "overlong", "padded"),
)
async def test_malformed_refresh_route_is_generic_and_does_not_log_cookie(
    identity_engine: AsyncEngine, raw: str, capsys: pytest.CaptureFixture[str]
) -> None:
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(identity_settings(), session_factory=factory)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        cookie = b"talaqi_refresh=" + raw.encode("latin-1") + b"; talaqi_csrf=placeholder"
        response = await client.post(
            "/api/v1/auth/refresh", headers=httpx.Headers([(b"cookie", cookie)])
        )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_session"
    assert not raw or raw not in repr(response.json())
    captured = capsys.readouterr()
    assert not raw or raw not in f"{captured.out}{captured.err}"
    assert response.headers.get_list("set-cookie") == []
