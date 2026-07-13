from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from talaqi.db.identifiers import generate_uuid7
from talaqi.platform import IdempotencyRepository, hash_request_body


def test_request_hash_is_deterministic_sha256_without_retaining_body() -> None:
    body = b'{"password":"never-store-this"}'

    first = hash_request_body(body)
    second = hash_request_body(body)

    assert first == second
    assert len(first) == 32
    assert body not in first


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"key": "x" * 15}, "16 to 200"),
        ({"key": "x" * 201}, "16 to 200"),
        ({"http_method": "GET"}, "supported mutation"),
        ({"http_method": "post"}, "supported mutation"),
        ({"route_fingerprint": "/events?private=token"}, "route fingerprint"),
        ({"route_fingerprint": "https://internal/events"}, "route fingerprint"),
        ({"request_hash": b"x" * 31}, "32-byte"),
        ({"now": datetime(2026, 7, 13)}, "timezone-aware"),
        ({"lease_duration": timedelta(0)}, "positive"),
        ({"lease_duration": timedelta(days=2)}, "past expiry"),
    ],
)
async def test_invalid_claims_are_rejected_before_opening_a_session(
    override: dict[str, object], message: str
) -> None:
    session_requested = False

    def forbidden_session() -> AsyncSession:
        nonlocal session_requested
        session_requested = True
        raise AssertionError("SQL must not be reached")

    now = datetime(2026, 7, 13, tzinfo=UTC)
    arguments: dict[str, object] = {
        "actor_id": generate_uuid7(),
        "http_method": "POST",
        "route_fingerprint": "/api/v1/events/{event_id}/registrations",
        "key": "safe-idempotency-key",
        "request_hash": hash_request_body(b"{}"),
        "now": now,
        "lease_duration": timedelta(seconds=30),
        "expires_at": now + timedelta(days=1),
    }
    arguments.update(override)
    repository = IdempotencyRepository(forbidden_session)

    with pytest.raises(ValueError, match=message):
        await repository.acquire(**arguments)  # pyright: ignore[reportArgumentType]

    assert session_requested is False


@pytest.mark.asyncio
async def test_expiry_must_be_future_utc_before_sql() -> None:
    def forbidden_session() -> AsyncSession:
        raise AssertionError("SQL must not be reached")

    now = datetime(2026, 7, 13, tzinfo=UTC)
    repository = IdempotencyRepository(forbidden_session)

    with pytest.raises(ValueError, match="after now"):
        await repository.acquire(
            actor_id=generate_uuid7(),
            http_method="DELETE",
            route_fingerprint="/api/v1/events/{event_id}",
            key="safe-idempotency-key",
            request_hash=hash_request_body(b"{}"),
            now=now,
            lease_duration=timedelta(seconds=30),
            expires_at=now,
        )
