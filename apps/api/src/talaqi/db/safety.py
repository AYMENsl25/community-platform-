from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from pydantic import SecretStr

_SAFE_TEST_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_UNSAFE_TARGET_MESSAGE = "database target is not an explicit local test database"


@dataclass(frozen=True, slots=True)
class SafeDatabaseTarget:
    host: str
    port: int
    database: str


def validate_test_database_url(value: str | SecretStr | None) -> SafeDatabaseTarget:
    """Validate a destructive-use URL while returning only non-secret target facts."""
    raw_value = value.get_secret_value() if isinstance(value, SecretStr) else value
    if not raw_value:
        raise ValueError(_UNSAFE_TARGET_MESSAGE)

    try:
        parsed = urlsplit(raw_value)
        port = parsed.port
    except ValueError:
        raise ValueError(_UNSAFE_TARGET_MESSAGE) from None

    host = parsed.hostname
    database = parsed.path.removeprefix("/")
    valid = (
        parsed.scheme == "postgresql+asyncpg"
        and host in _SAFE_TEST_HOSTS
        and port is not None
        and parsed.netloc != ""
        and parsed.path == f"/{database}"
        and database.endswith("_test")
        and database.lower() != "talaqi"
        and parsed.query == ""
        and parsed.fragment == ""
    )
    if not valid:
        raise ValueError(_UNSAFE_TARGET_MESSAGE)

    assert host is not None
    assert port is not None
    return SafeDatabaseTarget(host=host, port=port, database=database)
