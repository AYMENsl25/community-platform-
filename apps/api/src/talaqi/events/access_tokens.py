from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_TOKEN_BYTES = 32
_HASH_DOMAIN = b"talaqi:event-private-link:v1\x00"


class PrivateLinkTokenCodec:
    def __init__(self, secret: bytes) -> None:
        if len(secret) < 16:
            raise ValueError("private-link hashing secret must contain at least 16 bytes")
        self._secret = secret

    def issue(self) -> str:
        return (
            base64.urlsafe_b64encode(secrets.token_bytes(_TOKEN_BYTES)).decode("ascii").rstrip("=")
        )

    def digest(self, raw_token: str) -> bytes:
        encoded = raw_token.encode("ascii")
        return hmac.new(self._secret, _HASH_DOMAIN + encoded, hashlib.sha256).digest()

    @staticmethod
    def rate_limit_subject(raw_token: str) -> str:
        prefix = raw_token[:12].encode("ascii", errors="ignore")
        return hashlib.sha256(b"talaqi:event-private-link:prefix:v1\x00" + prefix).hexdigest()


__all__ = ["PrivateLinkTokenCodec"]
