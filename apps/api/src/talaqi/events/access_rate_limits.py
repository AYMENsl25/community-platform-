from __future__ import annotations

from fastapi import FastAPI

from talaqi.config import Settings
from talaqi.events.access_tokens import PrivateLinkTokenCodec
from talaqi.platform import ApiError
from talaqi.runtime import SettingsFactory
from talaqi.security import RateLimiter, RateLimitPolicy, create_rate_limiter, derive_bucket_id

_CLIENT_POLICY = RateLimitPolicy(30, 900)
_TOKEN_PREFIX_POLICY = RateLimitPolicy(1_000, 900)


class LazyEventAccessRateLimiter:
    def __init__(
        self,
        settings_factory: SettingsFactory,
        *,
        provider: RateLimiter | None = None,
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

    async def check(self, *, client_host: str | None, raw_token: str) -> None:
        limiter = self.resolve()
        settings = self._settings
        if settings is None:
            raise RuntimeError("event-access rate limiter settings were not resolved")
        secret = settings.session_secret.get_secret_value().encode("utf-8")
        client = client_host.strip() if client_host and client_host.strip() else "unknown-client"
        subjects = (
            ("event_access.client", client, _CLIENT_POLICY),
            (
                "event_access.token_prefix",
                PrivateLinkTokenCodec.rate_limit_subject(raw_token),
                _TOKEN_PREFIX_POLICY,
            ),
        )
        for namespace, subject, policy in subjects:
            decision = await limiter.consume(derive_bucket_id(secret, namespace, subject), policy)
            if not decision.allowed:
                raise ApiError(
                    code="rate_limited",
                    message_key="errors.rate_limited",
                    status_code=429,
                )


def install_event_access_rate_limits(
    application: FastAPI,
    settings_factory: SettingsFactory,
    *,
    provider: RateLimiter | None = None,
) -> LazyEventAccessRateLimiter:
    runtime = LazyEventAccessRateLimiter(settings_factory, provider=provider)
    application.state.event_access_rate_limits = runtime
    return runtime


__all__ = ["LazyEventAccessRateLimiter", "install_event_access_rate_limits"]
