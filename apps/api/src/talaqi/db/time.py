from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current instant as an aware UTC datetime."""
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Normalize an aware datetime to UTC; naive values are a contract error."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("persistence datetimes must be timezone-aware")
    return value.astimezone(UTC)
