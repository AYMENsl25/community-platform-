from __future__ import annotations

import pytest
from pydantic import ValidationError
from talaqi.config import Environment, Settings


def valid_values(environment: Environment = Environment.DEVELOPMENT) -> dict[str, object]:
    return {
        "environment": environment,
        "api_public_url": "http://localhost:8000",
        "web_public_url": "http://localhost:3000",
        "allowed_origins": ["http://localhost:3000"],
        "allowed_hosts": ["localhost", "127.0.0.1"],
        "session_secret": "development-only-secret",
        "cookie_secure": False,
        "admin_mfa_required": False,
        "database_url": "postgresql://talaqi:secret@localhost:5432/talaqi",
        "s3_endpoint": "http://localhost:9000",
        "s3_bucket": "talaqi-local",
        "s3_access_key": "local-access-key",
        "s3_secret_key": "local-secret-key",
        "smtp_host": "localhost",
        "smtp_port": 1025,
        "log_level": "INFO",
    }


def deployed_values(environment: Environment) -> dict[str, object]:
    values = valid_values(environment)
    values.update(
        api_public_url="https://api.example.com",
        web_public_url="https://www.example.com",
        allowed_origins=["https://www.example.com:8443"],
        allowed_hosts=["api.example.com:8443", "[2001:db8::1]:8443"],
        session_secret="s" * 64,
        cookie_secure=True,
        admin_mfa_required=True,
    )
    return values


def test_development_accepts_explicit_localhost_configuration() -> None:
    settings = Settings.model_validate(valid_values())

    assert settings.environment is Environment.DEVELOPMENT
    assert str(settings.api_public_url) == "http://localhost:8000/"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("allowed_origins", ["https://*.example.com"]),
        ("allowed_hosts", ["*.example.com"]),
    ],
)
def test_all_profiles_reject_wildcard_origins_and_hosts(field: str, value: list[str]) -> None:
    values = valid_values()
    values[field] = value

    with pytest.raises(ValidationError, match="wildcard"):
        Settings.model_validate(values)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("allowed_origins", [""]),
        ("allowed_origins", ["example.com"]),
        ("allowed_origins", ["ftp://example.com"]),
        ("allowed_origins", ["https://not a host"]),
        ("allowed_origins", ["https://user:password@example.com"]),
        ("allowed_origins", ["https://example.com/path"]),
        ("allowed_origins", ["https://example.com?query=yes"]),
        ("allowed_origins", ["https://example.com#fragment"]),
        ("allowed_hosts", [""]),
        ("allowed_hosts", ["https://example.com"]),
        ("allowed_hosts", ["user@example.com"]),
        ("allowed_hosts", ["example.com/path"]),
        ("allowed_hosts", ["not a host"]),
        ("allowed_hosts", ["example.com:99999"]),
    ],
)
def test_all_profiles_reject_malformed_origins_and_hosts(field: str, value: list[str]) -> None:
    values = valid_values()
    values[field] = value

    with pytest.raises(ValidationError):
        Settings.model_validate(values)


def test_origin_credential_validation_error_does_not_echo_credentials() -> None:
    values = valid_values()
    values["allowed_origins"] = ["https://user:origin-password@example.com"]

    with pytest.raises(ValidationError) as error:
        Settings.model_validate(values)

    assert "origin-password" not in str(error.value)


@pytest.mark.parametrize("environment", [Environment.STAGING, Environment.PRODUCTION])
def test_deployed_profiles_accept_valid_origins_hosts_and_public_urls(
    environment: Environment,
) -> None:
    settings = Settings.model_validate(deployed_values(environment))

    assert settings.environment is environment


@pytest.mark.parametrize("environment", [Environment.STAGING, Environment.PRODUCTION])
@pytest.mark.parametrize("field", ["api_public_url", "web_public_url"])
@pytest.mark.parametrize(
    "url",
    [
        "https://localhost",
        "https://127.0.0.1",
        "https://[::1]",
        "https://service.local",
    ],
)
def test_deployed_profiles_reject_local_public_urls(
    environment: Environment, field: str, url: str
) -> None:
    values = deployed_values(environment)
    values[field] = url

    with pytest.raises(ValidationError, match="public URLs"):
        Settings.model_validate(values)


@pytest.mark.parametrize("environment", [Environment.STAGING, Environment.PRODUCTION])
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("allowed_origins", ["https://127.0.0.1"]),
        ("allowed_origins", ["https://[::1]:8443"]),
        ("allowed_origins", ["https://service.local"]),
        ("allowed_hosts", ["127.0.0.1:8443"]),
        ("allowed_hosts", ["[::1]:8443"]),
        ("allowed_hosts", ["service.local"]),
    ],
)
def test_deployed_profiles_reject_local_origins_and_hosts(
    environment: Environment, field: str, value: list[str]
) -> None:
    values = deployed_values(environment)
    values[field] = value

    with pytest.raises(ValidationError):
        Settings.model_validate(values)


@pytest.mark.parametrize("environment", [Environment.STAGING, Environment.PRODUCTION])
@pytest.mark.parametrize(
    ("overrides", "needle"),
    [
        ({"session_secret": "weak"}, "session"),
        ({"session_secret": "CHANGEME" * 10}, "session"),
        ({"api_public_url": "http://api.example.com"}, "https"),
        ({"web_public_url": "http://web.example.com"}, "https"),
        ({"cookie_secure": False}, "cookie"),
        ({"allowed_origins": ["*"]}, "origin"),
        ({"allowed_origins": ["http://localhost:3000"]}, "origin"),
        ({"allowed_hosts": ["*"]}, "host"),
        ({"allowed_hosts": ["localhost"]}, "host"),
        ({"admin_mfa_required": False}, "mfa"),
    ],
)
def test_deployed_profiles_fail_closed(
    environment: Environment, overrides: dict[str, object], needle: str
) -> None:
    values = deployed_values(environment)
    values.update(overrides)

    with pytest.raises(ValidationError) as error:
        Settings.model_validate(values)
    assert needle in str(error.value).lower()


def test_secrets_are_redacted_from_repr_and_validation_errors() -> None:
    values = valid_values(Environment.PRODUCTION)
    values.update(session_secret="top-secret-session", s3_secret_key="top-secret-s3")

    with pytest.raises(ValidationError) as error:
        Settings.model_validate(values)

    output = str(error.value)
    assert "top-secret-session" not in output
    assert "top-secret-s3" not in output

    settings = Settings.model_validate(valid_values())
    representation = repr(settings)
    assert "development-only-secret" not in representation
    assert "local-secret-key" not in representation
