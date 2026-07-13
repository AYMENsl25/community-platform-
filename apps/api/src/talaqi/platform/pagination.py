from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from talaqi.db.identifiers import validate_uuid7
from talaqi.platform.errors import ApiError

_BASE64URL = re.compile(r"^[A-Za-z0-9_-]+$")
_MAX_CURSOR_LENGTH = 2048
_MAX_SORT_LENGTH = 512


class CursorParams(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = None


class CursorPage[ItemT](BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[ItemT]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class CursorPosition:
    ordering: datetime | str
    tie_breaker: UUID


class CursorCodec:
    def __init__(self, secret: bytes, *, version: int = 1) -> None:
        if len(secret) < 32:
            raise ValueError("cursor signing secret must contain at least 32 bytes")
        if version < 1:
            raise ValueError("cursor version must be positive")
        self._secret = secret
        self._version = version

    def encode(self, *, ordering: datetime | str, tie_breaker: UUID) -> str:
        identifier = validate_uuid7(tie_breaker)
        if isinstance(ordering, datetime):
            if ordering.tzinfo is None or ordering.utcoffset() is None:
                raise ValueError("cursor datetime must be timezone-aware")
            normalized = ordering.astimezone(UTC).isoformat().replace("+00:00", "Z")
            ordering_type = "datetime"
        elif 0 < len(ordering) <= _MAX_SORT_LENGTH:
            normalized = ordering
            ordering_type = "string"
        else:
            raise ValueError("cursor ordering value is invalid")

        payload = json.dumps(
            {
                "ordering": normalized,
                "ordering_type": ordering_type,
                "tie_breaker": str(identifier),
                "version": self._version,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        signature = hmac.digest(self._secret, payload, hashlib.sha256)
        encoded = f"{_encode_base64url(payload)}.{_encode_base64url(signature)}"
        if len(encoded) > _MAX_CURSOR_LENGTH:
            raise ValueError("encoded cursor exceeds maximum size")
        return encoded

    def decode(self, cursor: str) -> CursorPosition:
        try:
            if len(cursor) > _MAX_CURSOR_LENGTH:
                raise ValueError
            encoded_payload, encoded_signature = cursor.split(".", maxsplit=1)
            if not _BASE64URL.fullmatch(encoded_payload) or not _BASE64URL.fullmatch(
                encoded_signature
            ):
                raise ValueError
            payload = _decode_base64url(encoded_payload)
            signature = _decode_base64url(encoded_signature)
            expected = hmac.digest(self._secret, payload, hashlib.sha256)
            if len(signature) != hashlib.sha256().digest_size or not hmac.compare_digest(
                signature, expected
            ):
                raise ValueError
            raw_value: object = json.loads(payload)
            if not isinstance(raw_value, dict):
                raise ValueError
            raw = cast(dict[str, object], raw_value)
            if set(raw) != {
                "ordering",
                "ordering_type",
                "tie_breaker",
                "version",
            }:
                raise ValueError
            if raw["version"] != self._version:
                raise ValueError
            identifier = validate_uuid7(raw["tie_breaker"])
            ordering_value = raw["ordering"]
            if (
                not isinstance(ordering_value, str)
                or not 0 < len(ordering_value) <= _MAX_SORT_LENGTH
            ):
                raise ValueError
            if raw["ordering_type"] == "datetime":
                if not ordering_value.endswith("Z"):
                    raise ValueError
                ordering: datetime | str = datetime.fromisoformat(
                    ordering_value.removesuffix("Z") + "+00:00"
                )
            elif raw["ordering_type"] == "string":
                ordering = ordering_value
            else:
                raise ValueError
            return CursorPosition(ordering=ordering, tie_breaker=identifier)
        except (
            binascii.Error,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            UnicodeError,
            ValueError,
        ):
            raise ApiError(
                code="invalid_cursor",
                message_key="errors.invalid_cursor",
                status_code=400,
            ) from None


def _encode_base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode_base64url(value: str) -> bytes:
    return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
