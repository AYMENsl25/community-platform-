from __future__ import annotations

import string
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from talaqi.identity.sessions import AccessSessionCodec, AccessToken
from talaqi.platform import ApiError


def test_access_cookie_is_signed_canonical_and_expires_after_900_seconds() -> None:
    codec = AccessSessionCodec("test-session-secret")
    issued_at = datetime(2026, 7, 15, 10, 0, tzinfo=UTC)
    token = AccessToken(
        session_id=UUID("01980b78-2c00-7000-8000-000000000001"),
        user_id=UUID("01980b78-2c00-7000-8000-000000000002"),
        issued_at=issued_at,
    )

    encoded = codec.encode(token)
    decoded = codec.decode(encoded, now=issued_at + timedelta(seconds=899))

    assert decoded == token
    assert encoded.count(".") == 1
    with pytest.raises(ApiError) as expired:
        codec.decode(encoded, now=issued_at + timedelta(seconds=900))
    assert expired.value.code == "invalid_session"


def test_access_cookie_rejects_tampering() -> None:
    codec = AccessSessionCodec("test-session-secret")
    token = AccessToken(
        session_id=UUID("01980b78-2c00-7000-8000-000000000001"),
        user_id=UUID("01980b78-2c00-7000-8000-000000000002"),
        issued_at=datetime.now(UTC),
    )
    encoded = codec.encode(token)
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-_"
    final_index = alphabet.index(encoded[-1])
    noncanonical_alias = f"{encoded[:-1]}{alphabet[final_index + 1]}"
    with pytest.raises(ApiError):
        codec.decode(noncanonical_alias)
