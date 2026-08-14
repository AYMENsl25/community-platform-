from __future__ import annotations

from fastapi import FastAPI

from talaqi.config import Settings
from talaqi.platform import ApiError
from talaqi.runtime import SettingsFactory
from talaqi.security import RateLimiter, RateLimitPolicy, create_rate_limiter, derive_bucket_id

_REPORTER_POLICY = RateLimitPolicy(10, 3600)
_TARGET_POLICY = RateLimitPolicy(30, 3600)


class LazyModerationRateLimiter:
    def __init__(
        self, settings_factory: SettingsFactory, *, provider: RateLimiter | None = None
    ) -> None:
        self._settings_factory = settings_factory
        self._provider = provider
        self._resolved: RateLimiter | None = None
        self._settings: Settings | None = None

    def resolve(self) -> RateLimiter:
        if self._resolved is None:
            self._settings = self._settings_factory()
            self._resolved = self._provider or create_rate_limiter(self._settings.environment)
        return self._resolved

    async def check_report(self, *, reporter_id: str, target_key: str) -> None:
        limiter = self.resolve()
        if self._settings is None:
            raise RuntimeError("moderation rate limiter settings were not resolved")
        secret = self._settings.session_secret.get_secret_value().encode("utf-8")
        checks = (
            ("moderation.report.reporter", reporter_id, _REPORTER_POLICY),
            ("moderation.report.target", target_key, _TARGET_POLICY),
        )
        for namespace, subject, policy in checks:
            decision = await limiter.consume(derive_bucket_id(secret, namespace, subject), policy)
            if not decision.allowed:
                raise ApiError(
                    code="rate_limited",
                    message_key="errors.rate_limited",
                    status_code=429,
                )


def install_moderation_rate_limits(
    application: FastAPI,
    settings_factory: SettingsFactory,
    *,
    provider: RateLimiter | None = None,
) -> LazyModerationRateLimiter:
    runtime = LazyModerationRateLimiter(settings_factory, provider=provider)
    application.state.moderation_rate_limits = runtime
    return runtime


__all__ = ["LazyModerationRateLimiter", "install_moderation_rate_limits"]
