from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from apps.api.tests.database_url import reset_test_database_schema, resolve_test_database_url

TEST_URL = "postgresql+asyncpg://postgres@127.0.0.1:55432/talaqi_ci_test"


def test_environment_database_url_takes_precedence(tmp_path: Path) -> None:
    (tmp_path / ".env.test.local").write_text(
        "TEST_DATABASE_URL=postgresql+asyncpg://ignored@localhost/ignored_test\n",
        encoding="utf-8",
    )

    resolved = resolve_test_database_url(tmp_path, environ={"TEST_DATABASE_URL": TEST_URL})

    assert resolved.get_secret_value() == TEST_URL


def test_local_env_file_is_used_as_fallback(tmp_path: Path) -> None:
    (tmp_path / ".env.test.local").write_text(
        f"TEST_DATABASE_URL='{TEST_URL}'\n",
        encoding="utf-8",
    )

    resolved = resolve_test_database_url(tmp_path, environ={})

    assert resolved.get_secret_value() == TEST_URL


def test_missing_configuration_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Set TEST_DATABASE_URL"):
        resolve_test_database_url(tmp_path, environ={})


def test_schema_reset_rejects_a_non_test_database(tmp_path: Path) -> None:
    unsafe = SecretStr("postgresql+asyncpg://postgres@127.0.0.1:5432/talaqi")

    with pytest.raises(ValueError, match="explicit local test database"):
        reset_test_database_schema(unsafe, tmp_path)
