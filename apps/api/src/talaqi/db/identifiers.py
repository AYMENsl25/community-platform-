from __future__ import annotations

import secrets
import time
from uuid import UUID

_MAX_UUID7_MILLISECONDS = (1 << 48) - 1
_UUID7_VERSION = 0b0111
_RFC_4122_VARIANT = 0b10


def generate_uuid7() -> UUID:
    """Generate an opaque RFC 9562 UUIDv7 application identifier."""
    milliseconds = time.time_ns() // 1_000_000
    if not 0 <= milliseconds <= _MAX_UUID7_MILLISECONDS:
        raise RuntimeError("system time is outside the UUIDv7 timestamp range")

    value = milliseconds << 80
    value |= _UUID7_VERSION << 76
    value |= secrets.randbits(12) << 64
    value |= _RFC_4122_VARIANT << 62
    value |= secrets.randbits(62)
    return UUID(int=value)


def validate_uuid7(value: object) -> UUID:
    """Return a UUIDv7 or reject invalid/non-v7 identifiers."""
    try:
        identifier = value if isinstance(value, UUID) else UUID(str(value))
    except (AttributeError, TypeError, ValueError):
        raise ValueError("identifier must be a UUIDv7 value") from None
    if identifier.version != _UUID7_VERSION:
        raise ValueError("identifier must be a UUIDv7 value")
    return identifier
