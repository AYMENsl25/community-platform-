from __future__ import annotations

import pytest
from talaqi.db.safety import SafeDatabaseTarget, validate_test_database_url


def test_safe_local_asyncpg_test_url_returns_only_sanitized_facts() -> None:
    target = validate_test_database_url(
        "postgresql+asyncpg://test_user:sensitive-password@127.0.0.1:5433/talaqi_test"
    )

    assert target == SafeDatabaseTarget(host="127.0.0.1", port=5433, database="talaqi_test")
    representation = repr(target)
    assert "sensitive-password" not in representation
    assert "postgresql" not in representation


@pytest.mark.parametrize(
    "url",
    [
        None,
        "",
        "sqlite+aiosqlite:///talaqi_test.db",
        "postgresql://test_user:password@127.0.0.1:5433/talaqi_test",
        "postgresql+asyncpg://test_user:password@database.example:5433/talaqi_test",
        "postgresql+asyncpg://test_user:password@127.0.0.1/talaqi_test",
        "postgresql+asyncpg://test_user:password@127.0.0.1:5433/talaqi",
        "postgresql+asyncpg://test_user:password@127.0.0.1:5433/TALAQI",
        "postgresql+asyncpg://test_user:password@127.0.0.1:5433/not_a_test_database",
        "postgresql+asyncpg://test_user:password@127.0.0.1:5433/test_talaqi",
        "postgresql+asyncpg://test_user:password@127.0.0.1:5433/talaqi_test?host=remote",
    ],
)
def test_unsafe_database_urls_are_rejected_without_secret_leakage(url: str | None) -> None:
    with pytest.raises(ValueError, match="explicit local test database") as error:
        validate_test_database_url(url)

    message = str(error.value)
    assert "password" not in message
    assert "postgresql" not in message
    assert "sqlite" not in message
    assert "database.example" not in message
    assert "TALAQI" not in message
    assert "talaqi_test" not in message


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "[::1]"])
def test_all_explicit_loopback_hosts_are_allowed(host: str) -> None:
    target = validate_test_database_url(
        f"postgresql+asyncpg://test_user:sensitive-password@{host}:5433/talaqi_test"
    )

    assert target.database == "talaqi_test"
    assert target.port == 5433
