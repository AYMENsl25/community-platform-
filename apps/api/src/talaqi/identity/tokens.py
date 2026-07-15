from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Literal, cast
from uuid import UUID

from talaqi.platform import ApiError

AuthTokenKind = Literal["email_verification", "password_reset"]
_LIFETIMES = {"email_verification": 86_400, "password_reset": 3_600}


def invalid_recovery_token() -> ApiError:
    return ApiError(
        code="invalid_recovery_token",
        message_key="errors.invalid_recovery_token",
        status_code=401,
    )


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)


class AuthTokenCodec:
    def __init__(self, secret: str) -> None:
        self._key = secret.encode("utf-8")

    def public_token(self, token_id: UUID, kind: AuthTokenKind) -> str:
        authenticator = hmac.new(
            self._key, kind.encode("ascii") + b"\0" + token_id.bytes, hashlib.sha256
        ).digest()
        return f"{token_id}.{_b64(authenticator)}"

    def verify(self, token: str, kind: AuthTokenKind) -> UUID:
        try:
            identifier, supplied_text = token.split(".", maxsplit=1)
            token_id = UUID(identifier)
            supplied = _decode(supplied_text)
            expected = hmac.new(
                self._key, kind.encode("ascii") + b"\0" + token_id.bytes, hashlib.sha256
            ).digest()
            if not hmac.compare_digest(supplied, expected):
                raise ValueError
            return token_id
        except (TypeError, ValueError):
            raise invalid_recovery_token() from None

    def stored_hash(self, token: str, kind: AuthTokenKind) -> bytes:
        del kind
        return hmac.new(
            self._key,
            b"stored\0" + token.encode("ascii"),
            hashlib.sha256,
        ).digest()

    @staticmethod
    def expiry(kind: str, issued_at: datetime) -> datetime:
        try:
            seconds = _LIFETIMES[kind]
        except KeyError:
            raise invalid_recovery_token() from None
        return issued_at + timedelta(seconds=seconds)


def token_kind(value: str) -> AuthTokenKind:
    if value not in _LIFETIMES:
        raise invalid_recovery_token()
    return cast(AuthTokenKind, value)
