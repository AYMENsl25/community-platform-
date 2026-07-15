from __future__ import annotations

import asyncio
import hmac
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session
from talaqi.identity.dependencies import DatabaseSession
from talaqi.identity.sessions import AccessSessionCodec, AccessToken, RefreshTokenCodec
from talaqi.identity.tokens import AuthTokenCodec
from talaqi.main import create_app
from talaqi.platform import ApiError

from .test_routes import EMAIL, PASSWORD, assert_session_cookies_cleared, identity_settings

REPLACEMENT_PASSWORD = "replacement horse battery"  # pragma: allowlist secret


async def _issue_verification_token(
    app: FastAPI, engine: AsyncEngine, email: str
) -> tuple[UUID, str, bytes]:
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
        await client.post("/api/v1/auth/verification/request", json={"email": email})
    async with engine.connect() as connection:
        row = (
            await connection.execute(
                text(
                    """SELECT t.id,t.token_hash FROM talaqi.auth_tokens t
                    JOIN talaqi.users u ON u.id=t.user_id
                    WHERE u.email=:email AND t.kind='email_verification'
                    ORDER BY t.created_at DESC LIMIT 1"""
                ),
                {"email": email},
            )
        ).one()
    token_id, stored = row
    public = AuthTokenCodec("identity-test-session-secret").public_token(
        token_id, "email_verification"
    )
    return token_id, public, stored


async def _issue_password_reset_with_session(
    app: FastAPI, engine: AsyncEngine, email: str
) -> tuple[UUID, str, httpx.Response, UUID, UUID]:
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
        login = await client.post(
            "/api/v1/auth/login", json={"identifier": email, "password": PASSWORD}
        )
        await client.post("/api/v1/auth/password-reset/request", json={"email": email})
    async with engine.connect() as connection:
        token_id, session_id, user_id = (
            await connection.execute(
                text(
                    """SELECT t.id,s.id,u.id FROM talaqi.auth_tokens t
                    JOIN talaqi.users u ON u.id=t.user_id
                    JOIN talaqi.sessions s ON s.user_id=u.id
                    WHERE u.email=:email AND t.kind='password_reset'
                    ORDER BY t.created_at DESC,s.created_at DESC LIMIT 1"""
                ),
                {"email": email},
            )
        ).one()
    public = AuthTokenCodec("identity-test-session-secret").public_token(token_id, "password_reset")
    return token_id, public, login, session_id, user_id


@pytest.mark.asyncio
async def test_recovery_requests_are_non_enumerating_and_write_safe_outbox(
    identity_engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(identity_settings(), session_factory=factory)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        missing = await client.post(
            "/api/v1/auth/verification/request", json={"email": "absent@example.com"}
        )
        present = await client.post("/api/v1/auth/password-reset/request", json={"email": EMAIL})
    assert missing.status_code == present.status_code == 202
    assert missing.json() == present.json() == {"accepted": True}
    async with identity_engine.connect() as connection:
        payloads = (
            (
                await connection.execute(
                    text(
                        "SELECT payload::text FROM talaqi.outbox_events "
                        "WHERE event_type LIKE 'identity.%_requested' ORDER BY created_at DESC"
                    )
                )
            )
            .scalars()
            .all()
        )
    decoded = [json.loads(payload) for payload in payloads]
    assert all(
        set(payload) == {"user_id", "auth_token_id", "locale_hint", "template"}
        and PASSWORD not in repr(payload)
        and all("." not in str(value) for value in payload.values())
        for payload in decoded
    )


def test_recovery_and_session_openapi_contracts_exist() -> None:
    paths = create_app().openapi()["paths"]
    assert set(paths) >= {
        "/api/v1/auth/verification/request",
        "/api/v1/auth/verification/confirm",
        "/api/v1/auth/password-reset/request",
        "/api/v1/auth/password-reset/confirm",
        "/api/v1/auth/refresh",
        "/api/v1/auth/sessions",
        "/api/v1/auth/sessions/{session_id}",
    }


@pytest.mark.asyncio
async def test_concurrent_verification_token_consumption_is_single_use(
    identity_engine: AsyncEngine,
) -> None:
    email = "verification-race@example.com"
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
        await client.post("/api/v1/auth/verification/request", json={"email": email})
    async with identity_engine.connect() as connection:
        token_id = (
            await connection.execute(
                text(
                    """SELECT t.id FROM talaqi.auth_tokens t
                    JOIN talaqi.users u ON u.id=t.user_id
                    WHERE u.email=:email AND t.kind='email_verification'
                    ORDER BY t.created_at DESC LIMIT 1"""
                ),
                {"email": email},
            )
        ).scalar_one()
    public = AuthTokenCodec("identity-test-session-secret").public_token(
        token_id, "email_verification"
    )

    async def confirm() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            return await client.post("/api/v1/auth/verification/confirm", json={"token": public})

    responses = await asyncio.gather(confirm(), confirm())
    assert sorted(response.status_code for response in responses) == [200, 401]


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["expired", "used", "wrong_kind", "tampered_hash"])
async def test_persisted_recovery_state_is_checked_after_uuid_row_lock(
    identity_engine: AsyncEngine, state: str
) -> None:
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(identity_settings(), session_factory=factory)
    token_id, public, _stored = await _issue_verification_token(
        app, identity_engine, f"recovery-{state}@example.com"
    )
    async with identity_engine.begin() as connection:
        if state == "expired":
            await connection.execute(
                text(
                    "UPDATE talaqi.auth_tokens SET "
                    "expires_at=clock_timestamp()-interval '1 second' "
                    "WHERE id=:id"
                ),
                {"id": token_id},
            )
        elif state == "used":
            await connection.execute(
                text("UPDATE talaqi.auth_tokens SET used_at=clock_timestamp() WHERE id=:id"),
                {"id": token_id},
            )
        elif state == "wrong_kind":
            await connection.execute(
                text("UPDATE talaqi.auth_tokens SET kind='password_reset' WHERE id=:id"),
                {"id": token_id},
            )
        else:
            await connection.execute(
                text("UPDATE talaqi.auth_tokens SET token_hash=:hash WHERE id=:id"),
                {"id": token_id, "hash": b"\x00" * 32},
            )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        response = await client.post("/api/v1/auth/verification/confirm", json={"token": public})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_recovery_token"


@pytest.mark.asyncio
async def test_persisted_recovery_hash_uses_python_constant_time_compare(
    identity_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(identity_settings(), session_factory=factory)
    _token_id, public, stored = await _issue_verification_token(
        app, identity_engine, "recovery-compare-digest@example.com"
    )
    calls: list[tuple[object, object]] = []
    original = hmac.compare_digest

    def spy(left: object, right: object) -> bool:
        calls.append((left, right))
        return original(left, right)  # type: ignore[arg-type]

    monkeypatch.setattr(hmac, "compare_digest", spy)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        response = await client.post("/api/v1/auth/verification/confirm", json={"token": public})
    expected = AuthTokenCodec("identity-test-session-secret").stored_hash(
        public, "email_verification"
    )
    assert response.status_code == 200
    assert any(left == stored and right == expected for left, right in calls)


@pytest.mark.asyncio
async def test_request_cancellation_rolls_back_identity_mutation_without_late_commit(
    identity_engine: AsyncEngine,
) -> None:
    email = "cancelled-request-rollback@example.com"
    async with identity_engine.begin() as connection:
        await connection.execute(
            text("DELETE FROM talaqi.users WHERE email=:email"), {"email": email}
        )
    events: list[str] = []

    def after_commit(_session: Session) -> None:
        events.append("commit")

    def after_rollback(_session: Session) -> None:
        events.append("rollback")

    event.listen(Session, "after_commit", after_commit)
    event.listen(Session, "after_rollback", after_rollback)
    try:
        factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
        app = create_app(identity_settings(), session_factory=factory)

        async def cancel_after_mutation(session: DatabaseSession) -> None:
            await session.execute(
                text(
                    """INSERT INTO talaqi.users (
                    email,password_hash,terms_version,privacy_version,age_attested_at
                    ) VALUES (:email,:password_hash,'2026-07-11','2026-07-11',clock_timestamp())"""
                ),
                {
                    "email": email,
                    "password_hash": (
                        "$argon2id$v=19$m=65536,t=3,p=4$Lpm/Lp7Pi4/BGiV5tCGoQg$"
                        "yBSqOu3Mu/QL0TgL8EngAUcK6oI8W0ln7GNcBBaYHnE"  # pragma: allowlist secret
                    ),
                },
            )
            raise asyncio.CancelledError

        app.post("/__identity-cancel-after-mutation")(cancel_after_mutation)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            with pytest.raises(asyncio.CancelledError):
                await client.post("/__identity-cancel-after-mutation")
    finally:
        event.remove(Session, "after_commit", after_commit)
        event.remove(Session, "after_rollback", after_rollback)

    async with identity_engine.connect() as connection:
        persisted = (
            await connection.execute(
                text("SELECT count(*) FROM talaqi.users WHERE email=:email"), {"email": email}
            )
        ).scalar_one()
    assert events == ["rollback"]
    assert "commit" not in events
    assert persisted == 0


@pytest.mark.asyncio
async def test_password_reset_changes_password_revokes_sessions_and_clears_cookies(
    identity_engine: AsyncEngine,
) -> None:
    email = "password-reset-flow@example.com"
    new_password = "new correct horse battery"  # pragma: allowlist secret
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
        await client.post("/api/v1/auth/password-reset/request", json={"email": email})
    async with identity_engine.connect() as connection:
        token_id = (
            await connection.execute(
                text(
                    """SELECT t.id FROM talaqi.auth_tokens t
                    JOIN talaqi.users u ON u.id=t.user_id
                    WHERE u.email=:email AND t.kind='password_reset'
                    ORDER BY t.created_at DESC LIMIT 1"""
                ),
                {"email": email},
            )
        ).scalar_one()
    public = AuthTokenCodec("identity-test-session-secret").public_token(token_id, "password_reset")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as clean_client:
        reset = await clean_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": public, "new_password": new_password},
        )
        old_login = await clean_client.post(
            "/api/v1/auth/login", json={"identifier": email, "password": PASSWORD}
        )
        new_login = await clean_client.post(
            "/api/v1/auth/login", json={"identifier": email, "password": new_password}
        )
    assert reset.status_code == 200
    assert_session_cookies_cleared(reset, secure=False)
    assert old_login.status_code == 401
    assert new_login.status_code == 200
    async with identity_engine.connect() as connection:
        revoked_old = (
            await connection.execute(
                text(
                    """SELECT count(*) FROM talaqi.sessions s
                    JOIN talaqi.users u ON u.id=s.user_id
                    WHERE u.email=:email AND s.revoke_reason='password_reset'"""
                ),
                {"email": email},
            )
        ).scalar_one()
    assert login.status_code == 200
    assert revoked_old >= 1


@pytest.mark.asyncio
@pytest.mark.parametrize("access_state", ["malformed", "expired", "revoked", "nonexistent"])
async def test_invalid_optional_access_cookie_does_not_block_password_reset(
    identity_engine: AsyncEngine, access_state: str
) -> None:
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(identity_settings(), session_factory=factory)
    token_id, public, login, session_id, user_id = await _issue_password_reset_with_session(
        app, identity_engine, f"reset-{access_state}@example.com"
    )
    async with identity_engine.connect() as connection:
        old_password_hash = (
            await connection.execute(
                text("SELECT password_hash FROM talaqi.users WHERE id=:id"), {"id": user_id}
            )
        ).scalar_one()
    now = datetime.now(UTC)
    codec = AccessSessionCodec("identity-test-session-secret")
    if access_state == "malformed":
        access = "malformed-cookie"
    elif access_state == "expired":
        access = codec.encode(AccessToken(session_id, user_id, now - timedelta(seconds=901)))
    elif access_state == "nonexistent":
        access = codec.encode(AccessToken(uuid4(), user_id, now))
    else:
        access = login.cookies["talaqi_access"]
        async with identity_engine.begin() as connection:
            await connection.execute(
                text(
                    """UPDATE talaqi.sessions SET revoked_at=clock_timestamp(),
                    revoke_reason='test_revoked' WHERE id=:id"""
                ),
                {"id": session_id},
            )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": public,
                "new_password": REPLACEMENT_PASSWORD,
            },
            headers={"cookie": f"talaqi_access={access}"},
        )
    assert response.status_code == 200
    async with identity_engine.connect() as connection:
        used_at, new_password_hash, total_sessions, active_sessions = (
            await connection.execute(
                text(
                    """SELECT t.used_at,u.password_hash,
                    count(s.id),count(s.id) FILTER (WHERE s.revoked_at IS NULL)
                    FROM talaqi.auth_tokens t JOIN talaqi.users u ON u.id=t.user_id
                    LEFT JOIN talaqi.sessions s ON s.user_id=u.id
                    WHERE t.id=:token_id GROUP BY t.used_at,u.password_hash"""
                ),
                {"token_id": token_id},
            )
        ).one()
    assert_session_cookies_cleared(response, secure=False)
    assert used_at is not None
    assert new_password_hash != old_password_hash
    assert total_sessions >= 1
    assert active_sessions == 0


@pytest.mark.asyncio
async def test_valid_optional_access_requires_csrf_before_reset_token_consumption(
    identity_engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(identity_settings(), session_factory=factory)
    token_id, public, login, _session_id, user_id = await _issue_password_reset_with_session(
        app, identity_engine, "reset-valid-access@example.com"
    )
    async with identity_engine.connect() as connection:
        password_before = (
            await connection.execute(
                text("SELECT password_hash FROM talaqi.users WHERE id=:id"), {"id": user_id}
            )
        ).scalar_one()
    access = login.cookies["talaqi_access"]
    csrf = login.cookies["talaqi_csrf"]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        missing = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": public, "new_password": REPLACEMENT_PASSWORD},
            headers={"cookie": f"talaqi_access={access}"},
        )
        mismatch = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": public, "new_password": REPLACEMENT_PASSWORD},
            headers={
                "cookie": f"talaqi_access={access}; talaqi_csrf={csrf}",
                "X-CSRF-Token": "wrong-csrf-value",
            },
        )
    async with identity_engine.connect() as connection:
        used_after_denial, password_after_denial = (
            await connection.execute(
                text(
                    """SELECT t.used_at,u.password_hash FROM talaqi.auth_tokens t
                    JOIN talaqi.users u ON u.id=t.user_id WHERE t.id=:id"""
                ),
                {"id": token_id},
            )
        ).one()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        allowed = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": public, "new_password": REPLACEMENT_PASSWORD},
            headers={
                "cookie": f"talaqi_access={access}; talaqi_csrf={csrf}",
                "X-CSRF-Token": csrf,
            },
        )
    assert missing.status_code == mismatch.status_code == 403
    assert missing.headers.get_list("set-cookie") == []
    assert mismatch.headers.get_list("set-cookie") == []
    assert used_after_denial is None
    assert password_after_denial == password_before
    assert allowed.status_code == 200
    assert_session_cookies_cleared(allowed, secure=False)


@pytest.mark.asyncio
async def test_raw_authentication_material_is_absent_from_storage_logs_contracts_and_errors(
    identity_engine: AsyncEngine, capsys: pytest.CaptureFixture[str]
) -> None:
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(identity_settings(), session_factory=factory)
    _verification_id, verification, _stored = await _issue_verification_token(
        app, identity_engine, "secrecy-verification@example.com"
    )
    _reset_id, reset, login, _session_id, _user_id = await _issue_password_reset_with_session(
        app, identity_engine, "secrecy-password-reset@example.com"
    )
    raw_values: set[str] = {
        verification,
        reset,
        login.cookies["talaqi_access"],
        login.cookies["talaqi_refresh"],
        login.cookies["talaqi_csrf"],
    }
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as public_client:
        verification_request = await public_client.post(
            "/api/v1/auth/verification/request", json={"email": "absent-secrecy@example.com"}
        )
        reset_request = await public_client.post(
            "/api/v1/auth/password-reset/request", json={"email": "absent-secrecy@example.com"}
        )
        verification_confirm = await public_client.post(
            "/api/v1/auth/verification/confirm", json={"token": verification}
        )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as session_client:
        session_client.cookies.update(login.cookies)
        refresh = await session_client.post(
            "/api/v1/auth/refresh",
            headers={"X-CSRF-Token": login.cookies["talaqi_csrf"]},
        )
        raw_values.update(refresh.cookies.values())
        login_again = await session_client.post(
            "/api/v1/auth/login",
            json={"identifier": "secrecy-password-reset@example.com", "password": PASSWORD},
        )
        raw_values.update(login_again.cookies.values())
        sessions = await session_client.get("/api/v1/auth/sessions")
        target = next(item for item in sessions.json()["sessions"] if not item["current"])
        csrf = session_client.cookies["talaqi_csrf"]
        delete_one = await session_client.delete(
            f"/api/v1/auth/sessions/{target['id']}", headers={"X-CSRF-Token": csrf}
        )
        delete_all = await session_client.delete(
            "/api/v1/auth/sessions", headers={"X-CSRF-Token": csrf}
        )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as clean_client:
        reset_confirm = await clean_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": reset, "new_password": REPLACEMENT_PASSWORD},
        )
        invalid = await clean_client.post(
            "/api/v1/auth/verification/confirm", json={"token": verification + "x"}
        )
    successful = (
        verification_request,
        verification_confirm,
        reset_request,
        reset_confirm,
        refresh,
        sessions,
        delete_one,
        delete_all,
    )
    assert [response.status_code for response in successful] == [
        202,
        200,
        202,
        200,
        200,
        200,
        200,
        200,
    ]
    async with identity_engine.connect() as connection:
        persisted = (
            await connection.execute(
                text(
                    """SELECT encode(t.token_hash,'hex'),o.payload::text,
                    encode(s.refresh_token_hash,'hex'),encode(s.csrf_secret_hash,'hex')
                    FROM talaqi.auth_tokens t
                    JOIN talaqi.users u ON u.id=t.user_id
                    LEFT JOIN talaqi.outbox_events o ON o.aggregate_id=u.id
                    LEFT JOIN talaqi.sessions s ON s.user_id=u.id
                    WHERE u.email IN (
                      'secrecy-verification@example.com','secrecy-password-reset@example.com'
                    )"""
                )
            )
        ).all()
    with pytest.raises(ApiError) as recovery_error:
        AuthTokenCodec("identity-test-session-secret").verify(
            verification + "x", "email_verification"
        )
    with pytest.raises(ApiError) as refresh_error:
        RefreshTokenCodec("identity-test-session-secret").hash(
            login.cookies["talaqi_refresh"] + "="
        )
    with pytest.raises(ApiError) as access_error:
        AccessSessionCodec("identity-test-session-secret").decode(
            login.cookies["talaqi_access"] + "x"
        )
    exception_text = repr(
        (
            str(recovery_error.value),
            repr(recovery_error.value),
            str(refresh_error.value),
            repr(refresh_error.value),
            str(access_error.value),
            repr(access_error.value),
        )
    )
    exposed = repr(
        (persisted, [response.json() for response in successful], invalid.json(), app.openapi())
    )
    exposed += exception_text
    captured = capsys.readouterr()
    exposed += captured.out + captured.err
    assert invalid.status_code == 401
    assert all(raw not in exposed for raw in raw_values)
