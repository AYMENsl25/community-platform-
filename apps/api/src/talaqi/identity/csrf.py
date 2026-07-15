from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from talaqi.platform import ApiError


def _failed() -> ApiError:
    return ApiError(code="csrf_failed", message_key="errors.csrf_failed", status_code=403)


class CsrfService:
    def __init__(self, secret: str) -> None:
        self._key = secret.encode("utf-8")

    def issue(self) -> str:
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")

    def hash(self, raw: str) -> bytes:
        return hmac.new(
            self._key, b"talaqi:csrf:v2\0" + raw.encode("ascii"), hashlib.sha256
        ).digest()

    def verify(self, cookie: str | None, header: str | None, stored_hash: bytes) -> None:
        if cookie is None or header is None:
            raise _failed()
        try:
            match = hmac.compare_digest(cookie.encode("ascii"), header.encode("ascii"))
            valid = hmac.compare_digest(self.hash(cookie), stored_hash)
        except (UnicodeEncodeError, ValueError):
            raise _failed() from None
        if not match or not valid:
            raise _failed()
