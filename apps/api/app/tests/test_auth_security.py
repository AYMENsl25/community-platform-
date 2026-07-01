import pytest
from fastapi import HTTPException

from app.core.security import (
    extract_bearer_token,
    extract_clerk_identity,
    validate_authorized_party,
)


def test_extract_bearer_token_accepts_authorization_header() -> None:
    assert extract_bearer_token("Bearer abc.def.ghi") == "abc.def.ghi"


def test_extract_bearer_token_rejects_wrong_scheme() -> None:
    assert extract_bearer_token("Basic abc") is None
    assert extract_bearer_token(None) is None


def test_extract_clerk_identity_uses_supported_claims() -> None:
    identity = extract_clerk_identity(
        {
            "sub": "user_123",
            "email": "member@example.com",
            "name": "COMMUNITI Member",
            "image_url": "https://example.com/avatar.png",
        }
    )

    assert identity.clerk_user_id == "user_123"
    assert identity.email == "member@example.com"
    assert identity.display_name == "COMMUNITI Member"
    assert identity.avatar_url == "https://example.com/avatar.png"


def test_extract_clerk_identity_uses_local_fallback_without_email_claim() -> None:
    identity = extract_clerk_identity({"sub": "user_123"})

    assert identity.clerk_user_id == "user_123"
    assert identity.email == "user_123@clerk.local"
    assert identity.display_name == "user_123"


def test_extract_clerk_identity_requires_subject() -> None:
    with pytest.raises(HTTPException) as exc_info:
        extract_clerk_identity({"email": "member@example.com"})

    assert exc_info.value.status_code == 401


def test_validate_authorized_party_rejects_unknown_origin() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_authorized_party(
            {"azp": "https://evil.example"}, ["https://app.example"]
        )

    assert exc_info.value.status_code == 401
