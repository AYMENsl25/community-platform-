from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.db.identifiers import generate_uuid7
from talaqi.platform import (
    ApiError,
    IdempotencyClaimLostError,
    IdempotencyCoordinator,
    IdempotencyRepository,
    hash_request_body,
)

NOW = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
ROUTE = "/api/v1/events/{event_id}/registrations"
KEY = "stable-idempotency-key"


def arguments(actor_id: UUID, body: bytes = b'{"event_id":"opaque"}') -> dict[str, object]:
    return {
        "actor_id": actor_id,
        "http_method": "POST",
        "route_fingerprint": ROUTE,
        "key": KEY,
        "request_hash": hash_request_body(body),
        "now": NOW,
        "lease_duration": timedelta(seconds=30),
        "expires_at": NOW + timedelta(days=1),
    }


@pytest.mark.asyncio
async def test_first_claim_persists_safe_scope_hash_lease_and_expiry(
    idempotency_actor: UUID,
    platform_session_factory: async_sessionmaker[AsyncSession],
    platform_database_engine: AsyncEngine,
) -> None:
    body = b'{"password":"must-never-be-stored"}'
    repository = IdempotencyRepository(platform_session_factory)

    acquired = await repository.acquire(**arguments(idempotency_actor, body))  # pyright: ignore[reportArgumentType]

    assert acquired.outcome == "acquired"
    assert acquired.claim is not None
    async with platform_database_engine.connect() as connection:
        row = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT user_id, http_method, route_fingerprint, key, request_hash,
                               response_status, response_body, completed_at,
                               locked_until, expires_at
                        FROM talaqi.idempotency_keys
                        WHERE user_id = :actor_id AND key = :key
                        """
                    ),
                    {"actor_id": idempotency_actor, "key": KEY},
                )
            )
            .mappings()
            .one()
        )
    assert row["user_id"] == idempotency_actor
    assert row["http_method"] == "POST"
    assert row["route_fingerprint"] == ROUTE
    assert row["request_hash"] == hash_request_body(body)
    assert row["response_status"] is None
    assert row["response_body"] is None
    assert row["completed_at"] is None
    assert row["locked_until"] == NOW + timedelta(seconds=30)
    assert row["expires_at"] == NOW + timedelta(days=1)
    assert body not in bytes(row["request_hash"])


@pytest.mark.asyncio
async def test_active_completion_replay_conflict_and_coordinator_mapping(
    idempotency_actor: UUID,
    platform_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = IdempotencyRepository(platform_session_factory)
    coordinator = IdempotencyCoordinator(repository)
    claim_arguments = arguments(idempotency_actor)
    acquired = await repository.acquire(**claim_arguments)  # pyright: ignore[reportArgumentType]
    assert acquired.claim is not None

    active = await repository.acquire(**claim_arguments)  # pyright: ignore[reportArgumentType]
    assert active.outcome == "in_progress"
    with pytest.raises(ApiError) as in_progress:
        await coordinator.acquire(**claim_arguments)  # pyright: ignore[reportArgumentType]
    assert (in_progress.value.status_code, in_progress.value.code) == (
        409,
        "idempotency_in_progress",
    )

    response_body = {"registration_id": str(generate_uuid7()), "state": "confirmed"}
    await repository.complete(
        acquired.claim,
        response_status=201,
        response_body=response_body,
        completed_at=NOW + timedelta(seconds=1),
    )
    replay = await repository.acquire(**claim_arguments)  # pyright: ignore[reportArgumentType]
    assert replay.outcome == "replay"
    assert replay.response_status == 201
    assert replay.response_body == response_body

    conflicting = arguments(idempotency_actor, b'{"event_id":"different"}')
    conflict = await repository.acquire(**conflicting)  # pyright: ignore[reportArgumentType]
    assert conflict.outcome == "conflict"
    assert conflict.response_status is None
    assert conflict.response_body is None
    with pytest.raises(ApiError) as mapped:
        await coordinator.acquire(**conflicting)  # pyright: ignore[reportArgumentType]
    assert (mapped.value.status_code, mapped.value.code) == (409, "idempotency_conflict")


@pytest.mark.asyncio
async def test_expired_lease_reacquires_and_old_claim_cannot_complete(
    idempotency_actor: UUID,
    platform_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = IdempotencyRepository(platform_session_factory)
    initial_arguments = arguments(idempotency_actor)
    initial_arguments["lease_duration"] = timedelta(seconds=5)
    first = await repository.acquire(**initial_arguments)  # pyright: ignore[reportArgumentType]
    assert first.claim is not None

    retry_arguments = dict(initial_arguments)
    retry_arguments["now"] = NOW + timedelta(seconds=6)
    retry_arguments["expires_at"] = NOW + timedelta(days=2)
    second = await repository.acquire(**retry_arguments)  # pyright: ignore[reportArgumentType]
    assert second.outcome == "acquired"
    assert second.claim is not None
    assert second.claim.locked_until > first.claim.locked_until

    with pytest.raises(IdempotencyClaimLostError):
        await repository.complete(
            first.claim,
            response_status=200,
            response_body={"old": True},
            completed_at=NOW + timedelta(seconds=7),
        )


@pytest.mark.asyncio
async def test_expired_record_resets_hash_and_prior_response(
    idempotency_actor: UUID,
    platform_session_factory: async_sessionmaker[AsyncSession],
    platform_database_engine: AsyncEngine,
) -> None:
    repository = IdempotencyRepository(platform_session_factory)
    initial = arguments(idempotency_actor, b"first")
    initial["lease_duration"] = timedelta(seconds=10)
    initial["expires_at"] = NOW + timedelta(seconds=10)
    acquired = await repository.acquire(**initial)  # pyright: ignore[reportArgumentType]
    assert acquired.claim is not None
    await repository.complete(
        acquired.claim,
        response_status=200,
        response_body={"prior": "response"},
        completed_at=NOW + timedelta(seconds=1),
    )

    replacement = arguments(idempotency_actor, b"second")
    replacement["now"] = NOW + timedelta(seconds=11)
    replacement["expires_at"] = NOW + timedelta(days=2)
    reset = await repository.acquire(**replacement)  # pyright: ignore[reportArgumentType]
    assert reset.outcome == "acquired"
    async with platform_database_engine.connect() as connection:
        row = (
            await connection.execute(
                text(
                    """
                    SELECT request_hash, response_status, response_body, completed_at
                    FROM talaqi.idempotency_keys WHERE user_id = :actor_id AND key = :key
                    """
                ),
                {"actor_id": idempotency_actor, "key": KEY},
            )
        ).one()
    assert row.request_hash == hash_request_body(b"second")
    assert row.response_status is None
    assert row.response_body is None
    assert row.completed_at is None


@pytest.mark.asyncio
async def test_overall_expired_same_hash_reset_rejects_stale_completion_and_completes_new_claim(
    idempotency_actor: UUID,
    platform_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = IdempotencyRepository(platform_session_factory)
    initial = arguments(idempotency_actor, b"same-request")
    initial["lease_duration"] = timedelta(seconds=10)
    initial["expires_at"] = NOW + timedelta(seconds=10)
    first = await repository.acquire(**initial)  # pyright: ignore[reportArgumentType]
    assert first.claim is not None

    replacement = arguments(idempotency_actor, b"same-request")
    replacement["now"] = NOW + timedelta(seconds=11)
    replacement["lease_duration"] = timedelta(seconds=10)
    replacement["expires_at"] = NOW + timedelta(seconds=21)
    reset = await repository.acquire(**replacement)  # pyright: ignore[reportArgumentType]
    assert reset.outcome == "acquired"
    assert reset.claim is not None
    assert reset.claim.locked_until != first.claim.locked_until

    with pytest.raises(IdempotencyClaimLostError):
        await repository.complete(
            first.claim,
            response_status=200,
            response_body={"stale": True},
            completed_at=NOW + timedelta(seconds=12),
        )

    await repository.complete(
        reset.claim,
        response_status=202,
        response_body={"current": True},
        completed_at=NOW + timedelta(seconds=12),
    )
    replay_arguments = dict(replacement)
    replay_arguments["now"] = NOW + timedelta(seconds=13)
    replay_arguments["lease_duration"] = timedelta(seconds=8)
    replay = await repository.acquire(**replay_arguments)  # pyright: ignore[reportArgumentType]
    assert replay.outcome == "replay"
    assert replay.response_status == 202
    assert replay.response_body == {"current": True}


@pytest.mark.asyncio
async def test_scope_separates_actor_method_and_route(
    idempotency_actor: UUID,
    platform_session_factory: async_sessionmaker[AsyncSession],
    platform_database_engine: AsyncEngine,
) -> None:
    second_actor = generate_uuid7()
    async with platform_database_engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO talaqi.users (
                    id, email, password_hash, terms_version, privacy_version, age_attested_at
                ) VALUES (:id, :email, '$argon2id$test', 'test', 'test', clock_timestamp())
                """
            ),
            {"id": second_actor, "email": f"idempotency-{second_actor}@example.test"},
        )
    repository = IdempotencyRepository(platform_session_factory)
    variants = [
        arguments(idempotency_actor),
        {**arguments(idempotency_actor), "http_method": "DELETE"},
        {**arguments(idempotency_actor), "route_fingerprint": "/api/v1/events/{event_id}"},
        arguments(second_actor),
    ]
    try:
        outcomes = [
            (await repository.acquire(**variant)).outcome  # pyright: ignore[reportArgumentType]
            for variant in variants
        ]
        assert outcomes == ["acquired", "acquired", "acquired", "acquired"]
    finally:
        async with platform_database_engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM talaqi.users WHERE id = :actor_id"),
                {"actor_id": second_actor},
            )


@pytest.mark.asyncio
async def test_concurrent_same_scope_has_exactly_one_acquisition(
    idempotency_actor: UUID,
    platform_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = IdempotencyRepository(platform_session_factory)

    outcomes = await asyncio.gather(
        *(repository.acquire(**arguments(idempotency_actor)) for _ in range(8))  # pyright: ignore[reportArgumentType]
    )

    assert [item.outcome for item in outcomes].count("acquired") == 1
    assert [item.outcome for item in outcomes].count("in_progress") == 7
