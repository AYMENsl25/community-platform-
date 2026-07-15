from __future__ import annotations

from dataclasses import dataclass

import pytest
from talaqi.config import Environment
from talaqi.identity.rate_limits import AuthRateLimitAction, LazyAuthRateLimiter
from talaqi.platform import ApiError
from talaqi.security import RateLimitDecision, RateLimitPolicy

from .test_routes import identity_settings


@dataclass
class RecordingLimiter:
    deny_at: int | None = None

    def __post_init__(self) -> None:
        self.calls: list[tuple[str, RateLimitPolicy]] = []

    async def consume(self, bucket_id: str, policy: RateLimitPolicy) -> RateLimitDecision:
        self.calls.append((bucket_id, policy))
        denied = self.deny_at == len(self.calls)
        return RateLimitDecision(not denied, 0 if denied else 1, 1 if denied else 0)


@pytest.mark.asyncio
async def test_auth_limits_use_exact_isolated_namespaces_policies_and_persisted_provider() -> None:
    provider = RecordingLimiter()
    runtime = LazyAuthRateLimiter(lambda: identity_settings(), provider=provider)
    await runtime.check(
        AuthRateLimitAction.LOGIN, client_host="127.0.0.1", identifier="USER@Example.COM"
    )
    await runtime.check(AuthRateLimitAction.REGISTER, client_host=None, identifier="bad identifier")
    assert [policy for _, policy in provider.calls] == [
        RateLimitPolicy(20, 900),
        RateLimitPolicy(10, 900),
        RateLimitPolicy(5, 3600),
        RateLimitPolicy(3, 86400),
    ]
    assert len({bucket for bucket, _ in provider.calls}) == 4
    assert all("user" not in bucket and "127.0.0.1" not in bucket for bucket, _ in provider.calls)
    assert runtime.resolve() is provider


@pytest.mark.asyncio
async def test_denied_auth_bucket_returns_safe_rate_limit_error_before_work() -> None:
    runtime = LazyAuthRateLimiter(lambda: identity_settings(), provider=RecordingLimiter(deny_at=1))
    with pytest.raises(ApiError) as error:
        await runtime.check(
            AuthRateLimitAction.LOGIN, client_host=None, identifier="missing@example.com"
        )
    assert (error.value.status_code, error.value.code, error.value.message_key) == (
        429,
        "rate_limited",
        "errors.rate_limited",
    )


def test_deployed_auth_rate_limit_fails_closed_without_provider() -> None:
    settings = identity_settings().model_copy(update={"environment": Environment.PRODUCTION})
    runtime = LazyAuthRateLimiter(lambda: settings)
    with pytest.raises(RuntimeError, match="rate limiter provider"):
        runtime.resolve()
