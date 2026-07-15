from __future__ import annotations

import asyncio

import pytest
from talaqi.identity.passwords import (
    PasswordPolicy,
    PasswordService,
    normalize_email,
    normalize_login_identifier,
    normalize_username,
)
from talaqi.platform import ApiError


@pytest.fixture
def policy() -> PasswordPolicy:
    return PasswordPolicy.from_package_resource()


@pytest.mark.parametrize("password", ["abcdefghijkl", "x" * 128, "pässwörd安全安全"])
def test_password_policy_accepts_boundaries_and_preserves_unicode(
    policy: PasswordPolicy, password: str
) -> None:
    assert policy.validate(password) == password


@pytest.mark.parametrize("password", ["short", " " * 12, "x" * 129, "password123456"])
def test_password_policy_rejects_invalid_or_breached_values(
    policy: PasswordPolicy, password: str
) -> None:
    with pytest.raises(ApiError) as error:
        policy.validate(password)
    assert error.value.code == "invalid_credentials_input"


@pytest.mark.asyncio
async def test_password_service_uses_argon2id_and_mismatch_is_false(policy: PasswordPolicy) -> None:
    service = PasswordService(policy)
    encoded = await service.hash("correct horse battery")

    assert encoded.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert await service.verify(encoded, "wrong-password-value") is False
    assert await service.verify(encoded, "correct horse battery") is True


@pytest.mark.asyncio
async def test_password_work_propagates_cancellation(
    policy: PasswordPolicy, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    async def blocked_to_thread(*args: object) -> object:
        del args
        started.set()
        await release.wait()
        return "unused"

    monkeypatch.setattr(asyncio, "to_thread", blocked_to_thread)
    task = asyncio.create_task(PasswordService(policy).hash("correct horse battery"))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def test_identifier_normalization() -> None:
    assert normalize_email("  USER@Example.COM ") == "user@example.com"
    assert normalize_username(" Member_25 ") == "member_25"
    with pytest.raises(ApiError):
        normalize_username("not-an-allowed-name")


def test_login_identifier_normalizes_unicode_email_and_username_or_hides_invalid() -> None:
    assert normalize_login_identifier(" USER@bücher.de ") == "user@xn--bcher-kva.de"
    assert normalize_login_identifier(" MEMBER_25 ") == "member_25"
    assert normalize_login_identifier("malformed identifier") is None
    assert normalize_login_identifier("broken@@example.com") is None
