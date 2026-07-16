from __future__ import annotations

import re
from enum import StrEnum
from functools import lru_cache
from ipaddress import ip_address
from typing import Self
from urllib.parse import SplitResult, urlsplit

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
    normalized = host.strip("[]").rstrip(".").lower()
    if normalized == "localhost" or normalized.endswith(".local"):
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


_HOSTNAME_PATTERN = re.compile(
    r"^(?=.{1,253}\.?$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.?$",
    re.IGNORECASE,
)


def _validate_hostname(hostname: str, *, field: str) -> str:
    try:
        ip_address(hostname)
    except ValueError:
        if _HOSTNAME_PATTERN.fullmatch(hostname) is None:
            raise ValueError(f"{field} must contain a valid hostname or IP address") from None
    return hostname


def _validate_optional_port(parsed: SplitResult, *, field: str) -> None:
    authority = parsed.netloc.rsplit("@", maxsplit=1)[-1]
    if authority.startswith("["):
        closing_bracket = authority.find("]")
        suffix = authority[closing_bracket + 1 :]
        has_port = suffix.startswith(":")
        port_text = suffix[1:] if has_port else ""
    else:
        has_port = ":" in authority
        port_text = authority.rsplit(":", maxsplit=1)[-1] if has_port else ""
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError(f"{field} must contain a valid optional port") from error
    if has_port and (not port_text.isdecimal() or port is None or not 1 <= port <= 65535):
        raise ValueError(f"{field} must contain a valid optional port")


def _parse_origin(value: str) -> str:
    if not value or value != value.strip() or "*" in value:
        raise ValueError("allowed origins must be explicit HTTP(S) origins without wildcards")
    parsed = urlsplit(value)
    _validate_optional_port(parsed, field="allowed origins")
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("allowed origins must contain only HTTP(S), host, and optional port")
    return _validate_hostname(parsed.hostname, field="allowed origins")


def _parse_allowed_host(value: str) -> str:
    if (
        not value
        or value != value.strip()
        or "*" in value
        or any(character in value for character in "/@?#")
    ):
        raise ValueError("allowed hosts must be explicit host identifiers without wildcards")
    parsed = urlsplit(f"//{value}")
    _validate_optional_port(parsed, field="allowed hosts")
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("allowed hosts must contain a hostname or IP address")
    return _validate_hostname(hostname, field="allowed hosts")


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
    current_terms_version: str = Field(default="2026-07-11", min_length=1, max_length=64)
    current_privacy_version: str = Field(default="2026-07-11", min_length=1, max_length=64)
    current_organizer_rules_version: str = Field(default="2026-07-11", min_length=1, max_length=64)
    current_community_rules_version: str = Field(default="2026-07-11", min_length=1, max_length=64)
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
        origin_hosts = [_parse_origin(origin) for origin in self.allowed_origins]
        allowed_hostnames = [_parse_allowed_host(host) for host in self.allowed_hosts]

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
            if any(_is_local_host(host) for host in origin_hosts):
                raise ValueError("allowed origins may not use localhost in staging or production")
            if any(_is_local_host(host) for host in allowed_hostnames):
                raise ValueError("allowed hosts may not use localhost in staging or production")
            public_hosts = (self.api_public_url.host, self.web_public_url.host)
            if any(_is_local_host(host) for host in public_hosts):
                raise ValueError(
                    "staging and production public URLs may not use local or loopback hosts"
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


def reset_settings_cache() -> None:
    get_settings.cache_clear()
