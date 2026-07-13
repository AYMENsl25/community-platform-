from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.db.identifiers import validate_uuid7
from talaqi.db.session import transactional_session
from talaqi.platform.errors import ApiError

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type MutationMethod = Literal["POST", "PUT", "PATCH", "DELETE"]
type AcquisitionKind = Literal["acquired", "replay", "conflict", "in_progress"]

_SUPPORTED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def hash_request_body(body: bytes) -> bytes:
    return hashlib.sha256(body).digest()


@dataclass(frozen=True, slots=True)
class IdempotencyClaim:
    actor_id: UUID
    http_method: MutationMethod
    route_fingerprint: str
    key: str
    request_hash: bytes
    locked_until: datetime


@dataclass(frozen=True, slots=True)
class IdempotencyAcquisition:
    outcome: AcquisitionKind
    claim: IdempotencyClaim | None = None
    response_status: int | None = None
    response_body: JsonValue | None = None


class IdempotencyClaimLostError(RuntimeError):
    pass


class IdempotencyRepository:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def acquire(
        self,
        *,
        actor_id: UUID,
        http_method: str,
        route_fingerprint: str,
        key: str,
        request_hash: bytes,
        now: datetime,
        lease_duration: timedelta,
        expires_at: datetime,
    ) -> IdempotencyAcquisition:
        validated = _validate_acquisition(
            actor_id=actor_id,
            http_method=http_method,
            route_fingerprint=route_fingerprint,
            key=key,
            request_hash=request_hash,
            now=now,
            lease_duration=lease_duration,
            expires_at=expires_at,
        )
        locked_until = validated.now + validated.lease_duration
        claim = IdempotencyClaim(
            actor_id=validated.actor_id,
            http_method=validated.http_method,
            route_fingerprint=validated.route_fingerprint,
            key=validated.key,
            request_hash=validated.request_hash,
            locked_until=locked_until,
        )
        result: IdempotencyAcquisition
        async with transactional_session(self._session_factory) as session:
            inserted = (
                await session.execute(
                    text(
                        """
                        INSERT INTO talaqi.idempotency_keys (
                            user_id, http_method, route_fingerprint, key, request_hash,
                            locked_until, expires_at
                        )
                        VALUES (
                            :actor_id, :http_method, :route_fingerprint, :key, :request_hash,
                            :locked_until, :expires_at
                        )
                        ON CONFLICT (user_id, http_method, route_fingerprint, key) DO NOTHING
                        RETURNING id
                        """
                    ),
                    {
                        "actor_id": validated.actor_id,
                        "http_method": validated.http_method,
                        "route_fingerprint": validated.route_fingerprint,
                        "key": validated.key,
                        "request_hash": validated.request_hash,
                        "locked_until": locked_until,
                        "expires_at": validated.expires_at,
                    },
                )
            ).scalar_one_or_none()
            if inserted is not None:
                result = IdempotencyAcquisition(outcome="acquired", claim=claim)
            else:
                row = (
                    (
                        await session.execute(
                            text(
                                """
                                SELECT request_hash, response_status, response_body,
                                       locked_until, completed_at, expires_at
                                FROM talaqi.idempotency_keys
                                WHERE user_id = :actor_id
                                  AND http_method = :http_method
                                  AND route_fingerprint = :route_fingerprint
                                  AND key = :key
                                FOR UPDATE
                                """
                            ),
                            {
                                "actor_id": validated.actor_id,
                                "http_method": validated.http_method,
                                "route_fingerprint": validated.route_fingerprint,
                                "key": validated.key,
                            },
                        )
                    )
                    .mappings()
                    .one()
                )
                if row["expires_at"] <= validated.now:
                    await self._reset_claim(session, validated, locked_until)
                    result = IdempotencyAcquisition(outcome="acquired", claim=claim)
                elif row["request_hash"] != validated.request_hash:
                    result = IdempotencyAcquisition(outcome="conflict")
                elif row["completed_at"] is not None:
                    result = IdempotencyAcquisition(
                        outcome="replay",
                        response_status=cast(int, row["response_status"]),
                        response_body=cast(JsonValue, row["response_body"]),
                    )
                elif row["locked_until"] is not None and row["locked_until"] > validated.now:
                    result = IdempotencyAcquisition(outcome="in_progress")
                else:
                    await session.execute(
                        text(
                            """
                            UPDATE talaqi.idempotency_keys
                            SET locked_until = :locked_until, expires_at = :expires_at
                            WHERE user_id = :actor_id
                              AND http_method = :http_method
                              AND route_fingerprint = :route_fingerprint
                              AND key = :key
                            """
                        ),
                        {
                            "actor_id": validated.actor_id,
                            "http_method": validated.http_method,
                            "route_fingerprint": validated.route_fingerprint,
                            "key": validated.key,
                            "locked_until": locked_until,
                            "expires_at": validated.expires_at,
                        },
                    )
                    result = IdempotencyAcquisition(outcome="acquired", claim=claim)
        return result

    async def complete(
        self,
        claim: IdempotencyClaim,
        *,
        response_status: int,
        response_body: object,
        completed_at: datetime,
    ) -> None:
        if not 100 <= response_status <= 599:
            raise ValueError("response status must be between 100 and 599")
        completed_at = _validate_utc(completed_at, "completion time")
        normalized_body = _normalize_json(response_body)
        async with transactional_session(self._session_factory) as session:
            completed = (
                await session.execute(
                    text(
                        """
                        UPDATE talaqi.idempotency_keys
                        SET response_status = :response_status,
                            response_body = CAST(:response_body AS jsonb),
                            completed_at = :completed_at
                        WHERE user_id = :actor_id
                          AND http_method = :http_method
                          AND route_fingerprint = :route_fingerprint
                          AND key = :key
                          AND request_hash = :request_hash
                          AND locked_until = :locked_until
                          AND locked_until > :completed_at
                          AND expires_at > :completed_at
                          AND completed_at IS NULL
                        RETURNING id
                        """
                    ),
                    {
                        "actor_id": claim.actor_id,
                        "http_method": claim.http_method,
                        "route_fingerprint": claim.route_fingerprint,
                        "key": claim.key,
                        "request_hash": claim.request_hash,
                        "locked_until": claim.locked_until,
                        "response_status": response_status,
                        "response_body": json.dumps(
                            normalized_body,
                            ensure_ascii=False,
                            separators=(",", ":"),
                            sort_keys=True,
                        ),
                        "completed_at": completed_at,
                    },
                )
            ).scalar_one_or_none()
            if completed is None:
                raise IdempotencyClaimLostError("idempotency claim is no longer current")

    async def _reset_claim(
        self,
        session: AsyncSession,
        validated: _ValidatedAcquisition,
        locked_until: datetime,
    ) -> None:
        await session.execute(
            text(
                """
                UPDATE talaqi.idempotency_keys
                SET request_hash = :request_hash,
                    response_status = NULL,
                    response_body = NULL,
                    locked_until = :locked_until,
                    completed_at = NULL,
                    expires_at = :expires_at,
                    created_at = clock_timestamp()
                WHERE user_id = :actor_id
                  AND http_method = :http_method
                  AND route_fingerprint = :route_fingerprint
                  AND key = :key
                """
            ),
            {
                "actor_id": validated.actor_id,
                "http_method": validated.http_method,
                "route_fingerprint": validated.route_fingerprint,
                "key": validated.key,
                "request_hash": validated.request_hash,
                "locked_until": locked_until,
                "expires_at": validated.expires_at,
            },
        )


class IdempotencyCoordinator:
    def __init__(self, repository: IdempotencyRepository) -> None:
        self._repository = repository

    async def acquire(
        self,
        *,
        actor_id: UUID,
        http_method: str,
        route_fingerprint: str,
        key: str,
        request_hash: bytes,
        now: datetime,
        lease_duration: timedelta,
        expires_at: datetime,
    ) -> IdempotencyAcquisition:
        acquisition = await self._repository.acquire(
            actor_id=actor_id,
            http_method=http_method,
            route_fingerprint=route_fingerprint,
            key=key,
            request_hash=request_hash,
            now=now,
            lease_duration=lease_duration,
            expires_at=expires_at,
        )
        if acquisition.outcome == "conflict":
            raise ApiError(
                code="idempotency_conflict",
                message_key="errors.idempotency_conflict",
                status_code=409,
            )
        if acquisition.outcome == "in_progress":
            raise ApiError(
                code="idempotency_in_progress",
                message_key="errors.idempotency_in_progress",
                status_code=409,
            )
        return acquisition


@dataclass(frozen=True, slots=True)
class _ValidatedAcquisition:
    actor_id: UUID
    http_method: MutationMethod
    route_fingerprint: str
    key: str
    request_hash: bytes
    now: datetime
    lease_duration: timedelta
    expires_at: datetime


def _validate_acquisition(
    *,
    actor_id: UUID,
    http_method: str,
    route_fingerprint: str,
    key: str,
    request_hash: bytes,
    now: datetime,
    lease_duration: timedelta,
    expires_at: datetime,
) -> _ValidatedAcquisition:
    identifier = validate_uuid7(actor_id)
    if http_method not in _SUPPORTED_METHODS:
        raise ValueError("HTTP method is not a supported mutation method")
    method = cast(MutationMethod, http_method)
    if (
        not route_fingerprint.startswith("/api/v1/")
        or len(route_fingerprint) > 500
        or any(value in route_fingerprint for value in ("?", "#", "://"))
        or any(character.isspace() for character in route_fingerprint)
    ):
        raise ValueError("route fingerprint must be a stable API path template")
    if not 16 <= len(key) <= 200:
        raise ValueError("idempotency key must contain 16 to 200 characters")
    if len(request_hash) != 32:
        raise ValueError("request hash must be a 32-byte SHA-256 digest")
    normalized_now = _validate_utc(now, "current time")
    normalized_expiry = _validate_utc(expires_at, "expiry")
    if lease_duration <= timedelta(0):
        raise ValueError("lease duration must be positive")
    if normalized_expiry <= normalized_now:
        raise ValueError("idempotency expiry must be after now")
    try:
        locked_until = normalized_now + lease_duration
    except OverflowError:
        raise ValueError("idempotency lease must not extend past expiry") from None
    if locked_until > normalized_expiry:
        raise ValueError("idempotency lease must not extend past expiry")
    return _ValidatedAcquisition(
        actor_id=identifier,
        http_method=method,
        route_fingerprint=route_fingerprint,
        key=key,
        request_hash=request_hash,
        now=normalized_now,
        lease_duration=lease_duration,
        expires_at=normalized_expiry,
    )


def _validate_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{name} must be UTC")
    return value.astimezone(UTC)


def _normalize_json(value: object) -> JsonValue:
    _validate_json(value)
    return cast(JsonValue, json.loads(json.dumps(value, allow_nan=False)))


def _validate_json(value: object) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("response body must contain finite JSON numbers")
        return
    if isinstance(value, list):
        for item in cast(list[object], value):
            _validate_json(item)
        return
    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)
        if not all(isinstance(key, str) for key in mapping):
            raise ValueError("response body JSON object keys must be strings")
        for item in mapping.values():
            _validate_json(item)
        return
    raise ValueError("response body must be a JSON-compatible mapping, list, or scalar")
