from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from ipaddress import ip_address
from typing import Self
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def _is_local_host(host: str | None) -> bool:
    if host is None:
        return True
    normalized = host.rstrip(".").lower()
    if normalized == "localhost" or normalized.endswith(".local"):
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    environment: Environment
    api_public_url: AnyHttpUrl
    web_public_url: AnyHttpUrl
    allowed_origins: tuple[str, ...] = Field(min_length=1)
    allowed_hosts: tuple[str, ...] = Field(min_length=1)
    session_secret: SecretStr
    cookie_secure: bool
    admin_mfa_required: bool
    database_url: SecretStr
    s3_endpoint: AnyHttpUrl
    s3_bucket: str = Field(min_length=1)
    s3_access_key: SecretStr
    s3_secret_key: SecretStr
    smtp_host: str = Field(min_length=1)
    smtp_port: int = Field(ge=1, le=65535)
    log_level: LogLevel

    @model_validator(mode="after")
    def validate_security_profile(self) -> Self:
        origins = [origin.strip() for origin in self.allowed_origins]
        hosts = [host.strip().lower() for host in self.allowed_hosts]
        if any("*" in origin for origin in origins):
            raise ValueError("allowed origins must be explicit and may not contain a wildcard")
        if any("*" in host for host in hosts):
            raise ValueError("allowed hosts must be explicit and may not contain a wildcard")

        deployed = self.environment in {Environment.STAGING, Environment.PRODUCTION}
        if deployed:
            if self.api_public_url.scheme != "https" or self.web_public_url.scheme != "https":
                raise ValueError("public API and web URLs must use HTTPS")
            if not self.cookie_secure:
                raise ValueError("secure cookies are required in staging and production")
            if not self.admin_mfa_required:
                raise ValueError("admin MFA enforcement is required in staging and production")
            secret = self.session_secret.get_secret_value()
            placeholders = ("changeme", "placeholder", "replace", "example")
            if len(secret) < 64 or any(token in secret.lower() for token in placeholders):
                raise ValueError("session secret must be strong and may not be a known placeholder")
            if any(_is_local_host(urlsplit(origin).hostname) for origin in origins):
                raise ValueError("allowed origins may not use localhost in staging or production")
            if any(_is_local_host(host.split(":", maxsplit=1)[0]) for host in hosts):
                raise ValueError("allowed hosts may not use localhost in staging or production")

        if self.environment is Environment.PRODUCTION:
            public_hosts = (self.api_public_url.host, self.web_public_url.host)
            if any(_is_local_host(host) for host in public_hosts):
                raise ValueError("production public URLs may not use local or loopback hosts")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


def reset_settings_cache() -> None:
    get_settings.cache_clear()
