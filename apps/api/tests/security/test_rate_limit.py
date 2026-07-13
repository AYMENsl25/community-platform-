from __future__ import annotations

import asyncio

import pytest
from talaqi.config import Environment
from talaqi.security.rate_limit import (
    InMemoryRateLimiter,
    RateLimitDecision,
    RateLimitPolicy,
    create_rate_limiter,
    derive_bucket_id,
)


class Clock:
    value = 0.0

    def __call__(self) -> float:
        return self.value


def test_policy_and_bucket_validation_and_hmac_domain_separation() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        RateLimitPolicy(limit=0, window_seconds=1)
    with pytest.raises(ValueError, match="positive integer"):
        RateLimitPolicy(limit=1.5, window_seconds=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="positive and finite"):
        RateLimitPolicy(limit=1, window_seconds=0)
    with pytest.raises(ValueError, match="positive and finite"):
        RateLimitPolicy(limit=1, window_seconds=True)
    with pytest.raises(ValueError, match="allowed must be boolean"):
        RateLimitDecision(allowed=1, remaining=0, retry_after_seconds=0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="non-negative integers"):
        RateLimitDecision(allowed=False, remaining=0.5, retry_after_seconds=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="maximum buckets must be a positive integer"):
        InMemoryRateLimiter(max_buckets=1.5)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must not be empty"):
        derive_bucket_id(b"", "login", "subject")
    with pytest.raises(ValueError, match="stable safe identifier"):
        derive_bucket_id(b"secret", "Unsafe Namespace", "subject")
    first = derive_bucket_id(b"secret", "login", "person@example.test")
    assert first == derive_bucket_id(b"secret", "login", "person@example.test")
    assert first != derive_bucket_id(b"secret", "reset", "person@example.test")
    assert len(first) == 64
    assert first == first.lower()
    assert "person" not in first


@pytest.mark.asyncio
async def test_fixed_window_first_last_over_limit_and_exact_reset() -> None:
    clock = Clock()
    limiter = InMemoryRateLimiter(clock=clock)
    policy = RateLimitPolicy(limit=2, window_seconds=10)
    bucket = derive_bucket_id(b"secret", "login", "subject")
    assert (await limiter.consume(bucket, policy)).remaining == 1
    assert (await limiter.consume(bucket, policy)).remaining == 0
    denied = await limiter.consume(bucket, policy)
    assert not denied.allowed
    assert denied.remaining == 0
    assert denied.retry_after_seconds == 10
    clock.value = 9.1
    assert (await limiter.consume(bucket, policy)).retry_after_seconds == 1
    clock.value = 10.0
    reset = await limiter.consume(bucket, policy)
    assert reset.allowed
    assert reset.remaining == 1
    assert reset.retry_after_seconds == 0


@pytest.mark.asyncio
async def test_concurrent_last_allowance_is_atomic() -> None:
    limiter = InMemoryRateLimiter(clock=Clock())
    policy = RateLimitPolicy(limit=1, window_seconds=60)
    bucket = derive_bucket_id(b"secret", "login", "subject")
    decisions = await asyncio.gather(*(limiter.consume(bucket, policy) for _ in range(20)))
    assert sum(decision.allowed for decision in decisions) == 1


@pytest.mark.asyncio
async def test_capacity_evicts_expired_and_fails_closed_for_active_new_bucket() -> None:
    clock = Clock()
    limiter = InMemoryRateLimiter(clock=clock, max_buckets=1)
    policy = RateLimitPolicy(limit=2, window_seconds=5)
    one = derive_bucket_id(b"secret", "login", "one")
    two = derive_bucket_id(b"secret", "login", "two")
    assert (await limiter.consume(one, policy)).allowed
    full = await limiter.consume(two, policy)
    assert not full.allowed
    assert full.remaining == 0
    clock.value = 5
    assert (await limiter.consume(two, policy)).allowed


def test_factory_is_development_only_and_deployed_fails_closed() -> None:
    assert isinstance(create_rate_limiter(Environment.DEVELOPMENT), InMemoryRateLimiter)
    assert isinstance(create_rate_limiter(Environment.TEST), InMemoryRateLimiter)
    injected = InMemoryRateLimiter()
    assert create_rate_limiter(Environment.DEVELOPMENT, provider=injected) is not injected
    for environment in (Environment.STAGING, Environment.PRODUCTION):
        with pytest.raises(RuntimeError, match="rate limiter provider is required"):
            create_rate_limiter(environment)
        provider = InMemoryRateLimiter()
        assert create_rate_limiter(environment, provider=provider) is provider


@pytest.mark.asyncio
async def test_cancellation_while_waiting_for_lock_propagates() -> None:
    limiter = InMemoryRateLimiter()
    await limiter._lock.acquire()  # pyright: ignore[reportPrivateUsage]
    task = asyncio.create_task(
        limiter.consume("a" * 64, RateLimitPolicy(limit=1, window_seconds=1))
    )
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    limiter._lock.release()  # pyright: ignore[reportPrivateUsage]
