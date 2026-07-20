from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import cast

from talaqi.db.identifiers import validate_uuid7
from talaqi.discovery.models import (
    ClubPosition,
    DiscoveryFilters,
    DiscoveryKind,
    DiscoveryPosition,
    SearchPosition,
)
from talaqi.platform import ApiError


class DiscoveryCursorCodec:
    def __init__(self, secret: bytes) -> None:
        if len(secret) < 32:
            raise ValueError("cursor signing secret must contain at least 32 bytes")
        self._secret = secret

    def encode(self, filters: DiscoveryFilters, position: DiscoveryPosition) -> str:
        identifier = validate_uuid7(position.id)
        if position.start_at.tzinfo is None or position.start_at.utcoffset() is None:
            raise ValueError("cursor timestamp must be timezone-aware")
        return self._encode(
            "events",
            filters,
            {
                "featured_score": position.featured_score,
                "id": str(identifier),
                "start_at": position.start_at.astimezone(UTC).isoformat(),
            },
        )

    def decode(self, cursor: str, filters: DiscoveryFilters) -> DiscoveryPosition:
        position = self._decode(cursor, "events", filters)
        try:
            start_at = datetime.fromisoformat(cast(str, position["start_at"]))
            if start_at.tzinfo is None:
                raise ValueError
            return DiscoveryPosition(
                featured_score=int(cast(int, position["featured_score"])),
                start_at=start_at,
                id=validate_uuid7(position["id"]),
            )
        except (ValueError, TypeError, KeyError):
            raise _invalid_cursor() from None

    def encode_club(self, filters: DiscoveryFilters, position: ClubPosition) -> str:
        return self._encode(
            "clubs",
            filters,
            {"id": str(validate_uuid7(position.id)), "name_key": position.name_key},
        )

    def decode_club(self, cursor: str, filters: DiscoveryFilters) -> ClubPosition:
        position = self._decode(cursor, "clubs", filters)
        try:
            name_key = position["name_key"]
            if not isinstance(name_key, str) or not 0 < len(name_key) <= 160:
                raise ValueError
            return ClubPosition(name_key=name_key, id=validate_uuid7(position["id"]))
        except (ValueError, TypeError, KeyError):
            raise _invalid_cursor() from None

    def encode_search(self, filters: DiscoveryFilters, position: SearchPosition) -> str:
        return self._encode(
            "search",
            filters,
            {
                "id": str(validate_uuid7(position.id)),
                "kind": position.kind,
                "title_key": position.title_key,
            },
        )

    def decode_search(self, cursor: str, filters: DiscoveryFilters) -> SearchPosition:
        position = self._decode(cursor, "search", filters)
        try:
            title_key = position["title_key"]
            kind = position["kind"]
            if (
                not isinstance(title_key, str)
                or not 0 < len(title_key) <= 160
                or kind not in {"event", "club"}
            ):
                raise ValueError
            return SearchPosition(
                title_key=title_key,
                kind=cast(DiscoveryKind, kind),
                id=validate_uuid7(position["id"]),
            )
        except (ValueError, TypeError, KeyError):
            raise _invalid_cursor() from None

    def _encode(self, scope: str, filters: DiscoveryFilters, position: dict[str, object]) -> str:
        payload = json.dumps(
            {
                "filters": filters.fingerprint_values(),
                "position": position,
                "scope": scope,
                "version": 1,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        signature = hmac.digest(self._secret, payload, hashlib.sha256)
        return f"{_b64(payload)}.{_b64(signature)}"

    def _decode(self, cursor: str, scope: str, filters: DiscoveryFilters) -> dict[str, object]:
        try:
            if len(cursor) > 2048:
                raise ValueError
            encoded_payload, encoded_signature = cursor.split(".", 1)
            payload = _unb64(encoded_payload)
            signature = _unb64(encoded_signature)
            if not hmac.compare_digest(
                signature, hmac.digest(self._secret, payload, hashlib.sha256)
            ):
                raise ValueError
            raw_value: object = json.loads(payload)
            if not isinstance(raw_value, dict):
                raise ValueError
            raw = cast(dict[str, object], raw_value)
            if (
                raw.get("version") != 1
                or raw.get("scope") != scope
                or raw.get("filters") != filters.fingerprint_values()
                or not isinstance(raw.get("position"), dict)
            ):
                raise ValueError
            return cast(dict[str, object], raw["position"])
        except (ValueError, TypeError, KeyError, json.JSONDecodeError, binascii.Error):
            raise _invalid_cursor() from None


def _invalid_cursor() -> ApiError:
    return ApiError(code="invalid_cursor", message_key="errors.invalid_cursor", status_code=400)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)


__all__ = ["DiscoveryCursorCodec"]
