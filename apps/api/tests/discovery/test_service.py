from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from talaqi.discovery.models import (
    ClubPosition,
    DiscoveryFilters,
    DiscoveryPosition,
    SearchPosition,
)
from talaqi.discovery.service import DiscoveryCursorCodec
from talaqi.platform import ApiError

SECRET = b"d" * 32
EVENT_ID = UUID("01960000-0000-7000-8000-000000000001")


def test_discovery_cursor_round_trips_bound_position() -> None:
    filters = DiscoveryFilters(country="TR", city="istanbul", category="sports")
    codec = DiscoveryCursorCodec(SECRET)
    position = DiscoveryPosition(
        featured_score=10,
        start_at=datetime(2030, 1, 1, tzinfo=UTC),
        id=EVENT_ID,
    )

    cursor = codec.encode(filters, position)

    assert codec.decode(cursor, filters) == position


def test_discovery_cursor_rejects_filter_mismatch_and_tampering() -> None:
    codec = DiscoveryCursorCodec(SECRET)
    filters = DiscoveryFilters(country="TR")
    cursor = codec.encode(
        filters,
        DiscoveryPosition(
            featured_score=0,
            start_at=datetime(2030, 1, 1, tzinfo=UTC),
            id=EVENT_ID,
        ),
    )

    with pytest.raises(ApiError, match="invalid_cursor"):
        codec.decode(cursor, DiscoveryFilters(country="DZ"))
    with pytest.raises(ApiError, match="invalid_cursor"):
        codec.decode(cursor[:-1] + ("A" if cursor[-1] != "A" else "B"), filters)


def test_filters_normalize_search_and_codes() -> None:
    filters = DiscoveryFilters(country=" tr ", city=" Istanbul ", search="  CAFÉ   Run ")

    assert filters.country == "TR"
    assert filters.city == "istanbul"
    assert filters.search == "café run"


def test_club_and_search_cursors_bind_scope_filters_and_kind() -> None:
    codec = DiscoveryCursorCodec(SECRET)
    filters = DiscoveryFilters(country="TR", search="community")
    club = ClubPosition(name_key="istanbul community club", id=EVENT_ID)
    search = SearchPosition(title_key="istanbul community club", kind="club", id=EVENT_ID)

    club_cursor = codec.encode_club(filters, club)
    search_cursor = codec.encode_search(filters, search)

    assert codec.decode_club(club_cursor, filters) == club
    assert codec.decode_search(search_cursor, filters) == search
    with pytest.raises(ApiError, match="invalid_cursor"):
        codec.decode_search(club_cursor, filters)
