from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final
from uuid import UUID

from talaqi.platform import ApiError

ACCESS_COOKIE_NAME: Final = "talaqi_access"
ACCESS_LIFETIME_SECONDS: Final = 900


def _invalid_session() -> ApiError:
    return ApiError(code="invalid_session", message_key="errors.invalid_session", status_code=401)


def _b64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64_decode(value: str) -> bytes:
    return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)


@dataclass(frozen=True, slots=True)
class AccessToken:
    session_id: UUID
    user_id: UUID
    issued_at: datetime


class AccessSessionCodec:
    def __init__(self, secret: str) -> None:
        self._key = secret.encode("utf-8")

    def encode(self, token: AccessToken) -> str:
        issued = int(token.issued_at.timestamp())
        payload = json.dumps(
            {
                "exp": issued + ACCESS_LIFETIME_SECONDS,
                "iat": issued,
                "sid": str(token.session_id),
                "uid": str(token.user_id),
                "v": 1,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        encoded = _b64_encode(payload)
        signature = hmac.new(self._key, encoded.encode("ascii"), hashlib.sha256).digest()
        return f"{encoded}.{_b64_encode(signature)}"

    def decode(self, encoded: str, *, now: datetime | None = None) -> AccessToken:
        try:
            payload_part, signature_part = encoded.split(".", maxsplit=1)
            supplied = _b64_decode(signature_part)
            expected = hmac.new(self._key, payload_part.encode("ascii"), hashlib.sha256).digest()
            if not hmac.compare_digest(supplied, expected):
                raise ValueError
            payload = json.loads(_b64_decode(payload_part))
            if set(payload) != {"exp", "iat", "sid", "uid", "v"} or payload["v"] != 1:
                raise ValueError
            current = int((now or datetime.now(UTC)).timestamp())
            if (
                not isinstance(payload["iat"], int)
                or payload["exp"] != payload["iat"] + 900
                or current >= payload["exp"]
            ):
                raise ValueError
            return AccessToken(
                session_id=UUID(payload["sid"]),
                user_id=UUID(payload["uid"]),
                issued_at=datetime.fromtimestamp(payload["iat"], tz=UTC),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise _invalid_session() from None
