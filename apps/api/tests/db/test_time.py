from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from talaqi.db.time import as_utc, utc_now


def test_utc_now_returns_an_aware_utc_instant() -> None:
    instant = utc_now()

    assert instant.tzinfo is UTC
    assert instant.utcoffset() == timedelta(0)


def test_as_utc_normalizes_an_aware_datetime() -> None:
    source = datetime(2026, 7, 13, 15, 30, tzinfo=timezone(timedelta(hours=3)))

    normalized = as_utc(source)

    assert normalized == datetime(2026, 7, 13, 12, 30, tzinfo=UTC)
    assert normalized.tzinfo is UTC


def test_as_utc_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        as_utc(datetime(2026, 7, 13, 12, 30))
