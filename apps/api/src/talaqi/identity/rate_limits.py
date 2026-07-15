from __future__ import annotations

import hashlib
from enum import StrEnum

from fastapi import FastAPI

from talaqi.config import Settings
from talaqi.identity.passwords import normalize_login_identifier
from talaqi.platform import ApiError
from talaqi.runtime import SettingsFactory
from talaqi.security import (
    RateLimiter,
    RateLimitPolicy,
    create_rate_limiter,
    derive_bucket_id,
)


class AuthRateLimitAction(StrEnum):
    LOGIN = "login"
    REGISTER = "register"


_POLICIES = {
    (AuthRateLimitAction.LOGIN, "client"): ("auth.login.client", RateLimitPolicy(20, 900)),
    (AuthRateLimitAction.LOGIN, "identifier"): (
        "auth.login.identifier",
        RateLimitPolicy(10, 900),
    ),
    (AuthRateLimitAction.REGISTER, "client"): (
        "auth.register.client",
        RateLimitPolicy(5, 3600),
    ),
    (AuthRateLimitAction.REGISTER, "identifier"): (
        "auth.register.identifier",
        RateLimitPolicy(3, 86400),
    ),
}


def _identifier_subject(value: str) -> str:
    stripped = value.strip()
    normalized = normalize_login_identifier(stripped)
    if normalized is not None:
        return normalized
    return "invalid:" + hashlib.sha256(stripped.lower().encode("utf-8")).hexdigest()


class LazyAuthRateLimiter:
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

    async def check(
        self,
        action: AuthRateLimitAction,
        *,
        client_host: str | None,
        identifier: str,
    ) -> None:
        limiter = self.resolve()
        settings = self._settings
        if settings is None:
            raise RuntimeError("authentication rate limiter settings were not resolved")
        secret = settings.session_secret.get_secret_value().encode("utf-8")
        subjects = {
            "client": client_host.strip()
            if client_host and client_host.strip()
            else "unknown-client",
            "identifier": _identifier_subject(identifier),
        }
        for dimension in ("client", "identifier"):
            namespace, policy = _POLICIES[(action, dimension)]
            bucket = derive_bucket_id(secret, namespace, subjects[dimension])
            decision = await limiter.consume(bucket, policy)
            if not decision.allowed:
                raise ApiError(
                    code="rate_limited",
                    message_key="errors.rate_limited",
                    status_code=429,
                )


def install_auth_rate_limits(
    application: FastAPI,
    settings_factory: SettingsFactory,
    *,
    provider: RateLimiter | None = None,
) -> LazyAuthRateLimiter:
    runtime = LazyAuthRateLimiter(settings_factory, provider=provider)
    application.state.auth_rate_limits = runtime
    return runtime


__all__ = [
    "AuthRateLimitAction",
    "LazyAuthRateLimiter",
    "install_auth_rate_limits",
]
