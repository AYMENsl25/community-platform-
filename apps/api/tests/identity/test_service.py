from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from talaqi.identity.models import LoginState, NewSession, NewUser, SessionRecord, UserRecord
from talaqi.identity.passwords import PasswordPolicy, PasswordService
from talaqi.identity.service import AuthRequest, AuthService
from talaqi.identity.sessions import AccessSessionCodec, AccessToken
from talaqi.platform import ApiError

USER_ID = UUID("01980b78-2c00-7000-8000-000000000001")


class MemoryRepository:
    def __init__(self, user: UserRecord | None = None) -> None:
        self.user = user
        self.sessions: dict[UUID, SessionRecord] = {}
        self.failed = 0
        self.lookups: list[str] = []

    async def create_user(self, registration: NewUser) -> UserRecord:
        if self.user is not None:
            return self.user
        self.user = UserRecord(
            id=USER_ID,
            email=registration.email,
            password_hash=registration.password_hash,
            status="active",
            email_verified_at=None,
            failed_login_count=0,
            locked_until=None,
            is_platform_admin=False,
        )
        return self.user

    async def find_for_login(self, identifier: str) -> UserRecord | None:
        self.lookups.append(identifier)
        if self.user and identifier in {self.user.email, "member_25"}:
            return self.user
        return None

    async def record_failed_login(self, user_id: UUID, now: datetime) -> LoginState:
        assert user_id == USER_ID
        if self.user and self.user.locked_until is not None and self.user.locked_until <= now:
            self.failed = 1
        else:
            self.failed += 1
        locked = now + timedelta(minutes=15) if self.failed >= 5 else None
        if self.user:
            self.user = replace(self.user, failed_login_count=self.failed, locked_until=locked)
        return LoginState(failed_login_count=self.failed, locked_until=locked)

    async def clear_failed_login(self, user_id: UUID) -> None:
        assert user_id == USER_ID
        self.failed = 0
        if self.user:
            self.user = replace(self.user, failed_login_count=0, locked_until=None)

    async def create_session(self, session: NewSession) -> SessionRecord:
        record = SessionRecord(**asdict(session), revoked_at=None)
        self.sessions[record.id] = record
        return record

    async def find_active_session(
        self, session_id: UUID, now: datetime
    ) -> tuple[SessionRecord, UserRecord] | None:
        session = self.sessions.get(session_id)
        if session is None or self.user is None or session.expires_at <= now or session.revoked_at:
            return None
        return session, self.user

    async def revoke_session(self, session_id: UUID, reason: str, now: datetime) -> None:
        record = self.sessions.get(session_id)
        if record:
            self.sessions[session_id] = replace(record, revoked_at=now)


def service_for(repository: MemoryRepository) -> AuthService:
    return AuthService(
        repository,
        PasswordService(PasswordPolicy.from_package_resource()),
        AccessSessionCodec("test-session-secret"),
        current_terms_version="2026-07-11",
        current_privacy_version="2026-07-11",
    )


@pytest.mark.asyncio
async def test_registration_normalizes_email_and_duplicate_has_same_result() -> None:
    repository = MemoryRepository()
    service = service_for(repository)
    first = await service.register(
        email=" USER@Example.COM ",
        password="correct horse battery",  # pragma: allowlist secret
        age_attested=True,
        terms_version="2026-07-11",
        privacy_version="2026-07-11",
    )
    duplicate = await service.register(
        email="user@example.com",
        password="another safe password",  # pragma: allowlist secret
        age_attested=True,
        terms_version="2026-07-11",
        privacy_version="2026-07-11",
    )
    assert first == duplicate
    assert repository.user is not None
    assert repository.user.email == "user@example.com"


@pytest.mark.asyncio
async def test_login_accepts_username_and_unverified_principal() -> None:
    repository = MemoryRepository()
    service = service_for(repository)
    await service.register(
        email="user@example.com",
        password="correct horse battery",  # pragma: allowlist secret
        age_attested=True,
        terms_version="2026-07-11",
        privacy_version="2026-07-11",
    )
    result = await service.login("MEMBER_25", "correct horse battery", now=datetime.now(UTC))
    assert result.principal.email_verified is False
    assert result.principal.status == "active"
    assert result.credentials.refresh_token != result.credentials.csrf_secret
    stored = repository.sessions[result.principal.session_id]
    assert stored.refresh_token_hash == result.credentials.refresh_token_hash()
    assert stored.csrf_secret_hash == result.credentials.csrf_secret_hash()


@pytest.mark.asyncio
async def test_missing_wrong_suspended_and_locked_are_generic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = MemoryRepository()
    service = service_for(repository)
    verify_calls = 0
    original = service.passwords.verify

    async def count_verify(encoded: str, supplied: str) -> bool:
        nonlocal verify_calls
        verify_calls += 1
        return await original(encoded, supplied)

    monkeypatch.setattr(service.passwords, "verify", count_verify)
    with pytest.raises(ApiError) as missing:
        await service.login("missing@example.com", "wrong password value", now=datetime.now(UTC))
    assert missing.value.code == "invalid_credentials"
    assert verify_calls == 1

    await service.register(
        email="user@example.com",
        password="correct horse battery",  # pragma: allowlist secret
        age_attested=True,
        terms_version="2026-07-11",
        privacy_version="2026-07-11",
    )
    assert repository.user
    for _ in range(5):
        with pytest.raises(ApiError) as wrong:
            await service.login("user@example.com", "wrong password value", now=datetime.now(UTC))
        assert wrong.value.code == "invalid_credentials"
    assert repository.user.locked_until is not None

    repository.user = replace(repository.user, status="suspended", locked_until=None)
    with pytest.raises(ApiError) as suspended:
        await service.login("user@example.com", "correct horse battery", now=datetime.now(UTC))
    assert suspended.value.code == "invalid_credentials"


@pytest.mark.asyncio
async def test_malformed_login_uses_dummy_verify_without_repository_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = MemoryRepository()
    service = service_for(repository)
    calls = 0
    original = service.passwords.verify

    async def counted(encoded: str, supplied: str) -> bool:
        nonlocal calls
        calls += 1
        return await original(encoded, supplied)

    monkeypatch.setattr(service.passwords, "verify", counted)
    with pytest.raises(ApiError) as error:
        await service.login("broken@@example.com", "wrong password value", now=datetime.now(UTC))
    assert error.value.code == "invalid_credentials"
    assert calls == 1
    assert repository.lookups == []


@pytest.mark.asyncio
async def test_unicode_and_punycode_email_resolve_the_same_account() -> None:
    repository = MemoryRepository()
    service = service_for(repository)
    await service.register(
        email="USER@bücher.de",
        password="correct horse battery",  # pragma: allowlist secret
        age_attested=True,
        terms_version="2026-07-11",
        privacy_version="2026-07-11",
    )
    assert repository.user is not None
    assert repository.user.email == "user@xn--bcher-kva.de"
    result = await service.login(
        "user@xn--bcher-kva.de", "correct horse battery", now=datetime.now(UTC)
    )
    assert result.principal.user_id == USER_ID


@pytest.mark.asyncio
async def test_require_user_rejects_a_request_without_access_cookie() -> None:
    service = service_for(MemoryRepository())
    with pytest.raises(ApiError) as error:
        await service.require_user(cast(AuthRequest, SimpleNamespace(cookies={})))
    assert error.value.code == "authentication_required"


@pytest.mark.asyncio
async def test_logout_requires_matching_active_persisted_session_and_user() -> None:
    repository = MemoryRepository()
    service = service_for(repository)
    await service.register(
        email="logout@example.com",
        password="correct horse battery",  # pragma: allowlist secret
        age_attested=True,
        terms_version="2026-07-11",
        privacy_version="2026-07-11",
    )
    now = datetime.now(UTC)
    login = await service.login("logout@example.com", "correct horse battery", now=now)
    session_id = login.principal.session_id
    await service.logout(login.access_cookie, now=now)
    assert repository.sessions[session_id].revoked_at == now
    with pytest.raises(ApiError) as revoked:
        await service.logout(login.access_cookie, now=now)
    assert revoked.value.code == "invalid_credentials"

    expired = service.codec.encode(
        AccessToken(
            UUID("01980b78-2c00-7000-8000-000000000098"), USER_ID, now - timedelta(seconds=901)
        )
    )
    with pytest.raises(ApiError) as expired_error:
        await service.logout(expired, now=now)
    assert expired_error.value.code == "invalid_credentials"

    nonexistent = service.codec.encode(
        AccessToken(UUID("01980b78-2c00-7000-8000-000000000099"), USER_ID, now)
    )
    with pytest.raises(ApiError) as missing:
        await service.logout(nonexistent, now=now)
    assert missing.value.code == "invalid_credentials"


@pytest.mark.asyncio
async def test_logout_rejects_user_mismatch_and_suspended_user_without_revocation() -> None:
    repository = MemoryRepository()
    service = service_for(repository)
    await service.register(
        email="logout@example.com",
        password="correct horse battery",  # pragma: allowlist secret
        age_attested=True,
        terms_version="2026-07-11",
        privacy_version="2026-07-11",
    )
    now = datetime.now(UTC)
    login = await service.login("logout@example.com", "correct horse battery", now=now)
    mismatch = service.codec.encode(
        AccessToken(login.principal.session_id, UUID("01980b78-2c00-7000-8000-000000000099"), now)
    )
    with pytest.raises(ApiError):
        await service.logout(mismatch, now=now)
    assert repository.sessions[login.principal.session_id].revoked_at is None

    assert repository.user is not None
    repository.user = replace(repository.user, status="suspended")
    with pytest.raises(ApiError):
        await service.logout(login.access_cookie, now=now)
    assert repository.sessions[login.principal.session_id].revoked_at is None
    repository.user = replace(repository.user, status="deleted")
    with pytest.raises(ApiError):
        await service.logout(login.access_cookie, now=now)
    assert repository.sessions[login.principal.session_id].revoked_at is None


@pytest.mark.asyncio
async def test_locked_login_does_not_count_until_exact_expiry_boundary() -> None:
    repository = MemoryRepository()
    service = service_for(repository)
    await service.register(
        email="locked@example.com",
        password="correct horse battery",  # pragma: allowlist secret
        age_attested=True,
        terms_version="2026-07-11",
        privacy_version="2026-07-11",
    )
    now = datetime.now(UTC)
    assert repository.user is not None
    repository.failed = 5
    repository.user = replace(
        repository.user,
        failed_login_count=5,
        locked_until=now,
    )
    with pytest.raises(ApiError):
        await service.login(
            "locked@example.com", "wrong password value", now=now - timedelta(microseconds=1)
        )
    assert repository.failed == 5
    with pytest.raises(ApiError):
        await service.login("locked@example.com", "wrong password value", now=now)
    assert repository.failed == 1
    assert repository.user.locked_until is None
