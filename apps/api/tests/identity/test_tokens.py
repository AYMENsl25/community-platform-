from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from talaqi.identity.tokens import AuthTokenCodec
from talaqi.platform import ApiError


def test_verification_token_is_reconstructable_and_domain_separated() -> None:
    codec = AuthTokenCodec("test-session-secret")
    token_id = UUID("01980b78-2c00-7000-8000-000000000031")
    token = codec.public_token(token_id, "email_verification")

    assert codec.public_token(token_id, "email_verification") == token
    assert codec.verify(token, "email_verification") == token_id
    assert codec.stored_hash(token, "email_verification") == codec.stored_hash(
        token, "password_reset"
    )
    assert b"test-session-secret" not in codec.stored_hash(token, "email_verification")


def test_stored_hash_uses_exact_kind_independent_contract() -> None:
    secret = "test-session-secret"  # pragma: allowlist secret
    codec = AuthTokenCodec(secret)
    token = codec.public_token(UUID("01980b78-2c00-7000-8000-000000000031"), "email_verification")
    expected = hmac.new(
        secret.encode(), b"stored\0" + token.encode("ascii"), hashlib.sha256
    ).digest()
    assert codec.stored_hash(token, "email_verification") == expected
    assert codec.stored_hash(token, "password_reset") == expected


def test_token_rejects_tampering_and_wrong_kind() -> None:
    codec = AuthTokenCodec("test-session-secret")
    token = codec.public_token(UUID("01980b78-2c00-7000-8000-000000000031"), "password_reset")
    with pytest.raises(ApiError) as wrong_kind:
        codec.verify(token, "email_verification")
    assert wrong_kind.value.code == "invalid_recovery_token"
    with pytest.raises(ApiError):
        codec.verify(token[:-1] + ("A" if token[-1] != "A" else "B"), "password_reset")


@pytest.mark.parametrize(
    ("kind", "lifetime"), [("email_verification", 86_400), ("password_reset", 3_600)]
)
def test_recovery_lifetimes_are_exact(kind: str, lifetime: int) -> None:
    issued = datetime(2026, 7, 15, tzinfo=UTC)
    assert AuthTokenCodec.expiry(kind, issued) == issued + timedelta(seconds=lifetime)
