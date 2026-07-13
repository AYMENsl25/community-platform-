from __future__ import annotations

import asyncio
import hashlib
import hmac
import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from talaqi.config import Environment

_NAMESPACE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_BUCKET_ID = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    limit: int
    window_seconds: float

    def __post_init__(self) -> None:
        if type(self.limit) is not int or self.limit < 1:
            raise ValueError("rate limit must be a positive integer")
        if (
            type(self.window_seconds) not in {int, float}
            or not math.isfinite(self.window_seconds)
            or self.window_seconds <= 0
        ):
            raise ValueError("rate limit window must be positive and finite")


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int

    def __post_init__(self) -> None:
        if type(self.allowed) is not bool:
            raise ValueError("rate limit decision allowed must be boolean")
        if (
            type(self.remaining) is not int
            or type(self.retry_after_seconds) is not int
            or self.remaining < 0
            or self.retry_after_seconds < 0
        ):
            raise ValueError("rate limit decision counts must be non-negative integers")
        if self.allowed and self.retry_after_seconds != 0:
            raise ValueError("allowed decisions may not request a retry")


class RateLimiter(Protocol):
    async def consume(self, bucket_id: str, policy: RateLimitPolicy) -> RateLimitDecision: ...


@dataclass(slots=True)
class _Bucket:
    count: int
    expires_at: float


class InMemoryRateLimiter:
    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_buckets: int = 10_000,
    ) -> None:
        if type(max_buckets) is not int or max_buckets < 1:
            raise ValueError("maximum buckets must be a positive integer")
        self._clock = clock
        self._max_buckets = max_buckets
        self._buckets: dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()

    async def consume(self, bucket_id: str, policy: RateLimitPolicy) -> RateLimitDecision:
        if _BUCKET_ID.fullmatch(bucket_id) is None:
            raise ValueError("bucket identifier must be a lower-case SHA-256 digest")
        async with self._lock:
            now = self._clock()
            expired = [key for key, bucket in self._buckets.items() if bucket.expires_at <= now]
            for key in expired:
                del self._buckets[key]

            bucket = self._buckets.get(bucket_id)
            if bucket is None:
                if len(self._buckets) >= self._max_buckets:
                    return RateLimitDecision(
                        allowed=False,
                        remaining=0,
                        retry_after_seconds=max(1, math.ceil(policy.window_seconds)),
                    )
                self._buckets[bucket_id] = _Bucket(count=1, expires_at=now + policy.window_seconds)
                return RateLimitDecision(
                    allowed=True, remaining=policy.limit - 1, retry_after_seconds=0
                )

            if bucket.count >= policy.limit:
                return RateLimitDecision(
                    allowed=False,
                    remaining=0,
                    retry_after_seconds=max(0, math.ceil(bucket.expires_at - now)),
                )
            bucket.count += 1
            return RateLimitDecision(
                allowed=True,
                remaining=max(0, policy.limit - bucket.count),
                retry_after_seconds=0,
            )


def derive_bucket_id(secret: bytes, namespace: str, subject: str) -> str:
    if not secret:
        raise ValueError("bucket secret must not be empty")
    if _NAMESPACE.fullmatch(namespace) is None:
        raise ValueError("bucket namespace must be a stable safe identifier")
    if not subject:
        raise ValueError("bucket subject must not be empty")
    payload = namespace.encode("ascii") + b"\x00" + subject.encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def create_rate_limiter(
    environment: Environment,
    *,
    provider: RateLimiter | None = None,
) -> RateLimiter:
    if environment in {Environment.DEVELOPMENT, Environment.TEST}:
        return InMemoryRateLimiter()
    if provider is None:
        raise RuntimeError("rate limiter provider is required")
    return provider


__all__ = [
    "InMemoryRateLimiter",
    "RateLimitDecision",
    "RateLimitPolicy",
    "RateLimiter",
    "create_rate_limiter",
    "derive_bucket_id",
]
