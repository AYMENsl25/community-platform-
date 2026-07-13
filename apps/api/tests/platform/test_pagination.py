from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from talaqi.db.identifiers import generate_uuid7
from talaqi.platform import ApiError, CursorCodec, CursorPage, CursorParams


def _tamper(value: str) -> str:
    payload, signature = value.split(".", maxsplit=1)
    tampered_signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    return f"{payload}.{tampered_signature}"


def _malformed(_value: str) -> str:
    return "not-a-cursor"


def _oversized(value: str) -> str:
    return value + "x" * 5000


def test_cursor_params_default_and_bounds_are_locked() -> None:
    assert CursorParams().limit == 20
    assert CursorParams(limit=1).limit == 1
    assert CursorParams(limit=100).limit == 100

    for invalid in (0, -1, 101, 1.5, "not-an-integer"):
        with pytest.raises(ValidationError):
            CursorParams.model_validate({"limit": invalid})


def test_cursor_page_emits_only_locked_fields() -> None:
    page = CursorPage[dict[str, str]](items=[{"name": "Talaqi"}], next_cursor=None)

    assert page.model_dump() == {"items": [{"name": "Talaqi"}], "next_cursor": None}


def test_cursor_codec_is_deterministic_and_round_trips_datetime_and_opaque_sort() -> None:
    codec = CursorCodec(b"s" * 32)
    identifier = generate_uuid7()
    ordering_time = datetime(2026, 7, 13, 8, 9, 10, 123456, tzinfo=UTC)

    encoded = codec.encode(ordering=ordering_time, tie_breaker=identifier)
    assert codec.encode(ordering=ordering_time, tie_breaker=identifier) == encoded
    decoded = codec.decode(encoded)
    assert decoded.ordering == ordering_time
    assert decoded.tie_breaker == identifier

    text_encoded = codec.encode(ordering="rank:00042", tie_breaker=identifier)
    text_decoded = codec.decode(text_encoded)
    assert text_decoded.ordering == "rank:00042"
    assert text_decoded.tie_breaker == identifier


def test_cursor_codec_rejects_unsafe_encode_inputs() -> None:
    codec = CursorCodec(b"s" * 32)

    with pytest.raises(ValueError, match="timezone-aware"):
        codec.encode(ordering=datetime(2026, 7, 13), tie_breaker=generate_uuid7())
    with pytest.raises(ValueError, match="UUIDv7"):
        codec.encode(ordering="rank", tie_breaker=uuid4())


@pytest.mark.parametrize(
    "mutator",
    [
        _tamper,
        _malformed,
        _oversized,
    ],
)
def test_cursor_decode_failures_are_uniform_and_secret_safe(
    mutator: Callable[[str], str],
) -> None:
    codec = CursorCodec(b"top-secret-signing-material" * 2)
    encoded = codec.encode(ordering="rank", tie_breaker=generate_uuid7())
    invalid = mutator(encoded)

    with pytest.raises(ApiError) as captured:
        codec.decode(invalid)

    error = captured.value
    assert error.status_code == 400
    assert error.code == "invalid_cursor"
    assert error.message_key == "errors.invalid_cursor"
    assert "top-secret" not in str(error)
    assert invalid not in str(error)


def test_wrong_cursor_version_maps_to_the_same_safe_error() -> None:
    old_codec = CursorCodec(b"s" * 32, version=1)
    future_codec = CursorCodec(b"s" * 32, version=2)
    cursor = future_codec.encode(ordering="rank", tie_breaker=generate_uuid7())

    with pytest.raises(ApiError, match="invalid_cursor"):
        old_codec.decode(cursor)


@pytest.mark.parametrize(
    "ordering",
    [
        "a" * 512,
        "é" * 512,
        "🙂" * 300,
    ],
)
def test_cursor_size_boundary_and_multibyte_values_round_trip(ordering: str) -> None:
    codec = CursorCodec(b"s" * 32)
    identifier = generate_uuid7()

    encoded = codec.encode(ordering=ordering, tie_breaker=identifier)

    assert len(encoded) <= 2048
    assert codec.decode(encoded).ordering == ordering


def test_cursor_encode_rejects_astral_value_that_cannot_be_decoded() -> None:
    codec = CursorCodec(b"s" * 32)

    with pytest.raises(ValueError, match="encoded cursor exceeds maximum size"):
        codec.encode(ordering="🙂" * 512, tie_breaker=generate_uuid7())
