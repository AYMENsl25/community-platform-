from __future__ import annotations

import hashlib
import os
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.config import Settings
from talaqi.db.engine import build_async_engine
from talaqi.db.identifiers import generate_uuid7
from talaqi.identity.csrf import CsrfService
from talaqi.identity.sessions import AccessSessionCodec, AccessToken
from talaqi.main import create_app
from talaqi.media.storage import MediaStorage

from apps.api.tests.database_url import resolve_test_database_url

ROOT = Path(__file__).resolve().parents[4]
CURRENT_VERSION = "2026-07-11"


def _database_url() -> SecretStr:
    return resolve_test_database_url(ROOT)


@pytest.fixture(scope="session")
def media_database_url() -> Iterator[SecretStr]:
    secret = _database_url()
    previous = os.environ.get("TEST_DATABASE_URL")
    os.environ["TEST_DATABASE_URL"] = secret.get_secret_value()
    try:
        command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
        yield secret
    finally:
        if previous is None:
            os.environ.pop("TEST_DATABASE_URL", None)
        else:
            os.environ["TEST_DATABASE_URL"] = previous


@pytest_asyncio.fixture
async def media_engine(media_database_url: SecretStr) -> AsyncIterator[AsyncEngine]:
    engine = build_async_engine(media_database_url)
    try:
        yield engine
    finally:
        await engine.dispose()


def media_settings() -> Settings:
    return Settings.model_validate(
        {
            "environment": "test",
            "api_public_url": "http://localhost:8000",
            "web_public_url": "http://localhost:3000",
            "allowed_origins": ["http://localhost:3000"],
            "allowed_hosts": ["localhost", "127.0.0.1"],
            "session_secret": "media-test-secret",  # pragma: allowlist secret
            "current_terms_version": CURRENT_VERSION,
            "current_privacy_version": CURRENT_VERSION,
            "current_organizer_rules_version": CURRENT_VERSION,
            "current_community_rules_version": CURRENT_VERSION,
            "cookie_secure": False,
            "admin_mfa_required": False,
            "database_url": (
                "postgresql+asyncpg://unused:unused@"  # pragma: allowlist secret
                "127.0.0.1:5432/unused"
            ),
            "media_storage_backend": "local",
            "s3_endpoint": "http://localhost:9000",
            "s3_bucket": "test",
            "s3_access_key": "access",
            "s3_secret_key": "secret",  # pragma: allowlist secret
            "smtp_host": "localhost",
            "smtp_port": 1025,
            "log_level": "DEBUG",
        }
    )


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    user_id: UUID
    cookie: str
    csrf: str

    def headers(self, *, idempotency_key: str | None = None) -> dict[str, str]:
        values = {"cookie": self.cookie, "X-CSRF-Token": self.csrf}
        if idempotency_key is not None:
            values["Idempotency-Key"] = idempotency_key
        return values


async def create_user(
    engine: AsyncEngine,
    *,
    verified: bool = True,
    status: str = "active",
) -> AuthenticatedUser:
    settings = media_settings()
    now = datetime.now(UTC)
    user_id = generate_uuid7()
    session_id = generate_uuid7()
    csrf = f"csrf-{user_id}"
    csrf_hash = CsrfService(settings.session_secret.get_secret_value()).hash(csrf)
    refresh_hash = hashlib.sha256(str(session_id).encode("ascii")).digest()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO talaqi.users (
                    id, email, password_hash, status, terms_version, privacy_version,
                    organizer_rules_version, community_rules_version, age_attested_at,
                    email_verified_at
                ) VALUES (
                    :id, :email, '$argon2id$test', CAST(:status AS talaqi.user_status),
                    :version, :version, :version, :version, CAST(:now AS timestamptz),
                    CASE WHEN :verified THEN CAST(:now AS timestamptz) ELSE NULL END
                )
                """
            ),
            {
                "id": user_id,
                "email": f"media-{user_id}@example.test",
                "status": status,
                "version": CURRENT_VERSION,
                "now": now,
                "verified": verified,
            },
        )
        await connection.execute(
            text(
                """
                INSERT INTO talaqi.sessions (
                    id, user_id, family_id, refresh_token_hash, csrf_secret_hash, expires_at
                ) VALUES (:id, :user_id, :family_id, :refresh_hash, :csrf_hash, :expires_at)
                """
            ),
            {
                "id": session_id,
                "user_id": user_id,
                "family_id": generate_uuid7(),
                "refresh_hash": refresh_hash,
                "csrf_hash": csrf_hash,
                "expires_at": now + timedelta(days=1),
            },
        )
    access = AccessSessionCodec(settings.session_secret.get_secret_value()).encode(
        AccessToken(session_id, user_id, now - timedelta(seconds=1))
    )
    return AuthenticatedUser(
        user_id,
        f"talaqi_access={access}; talaqi_csrf={csrf}",
        csrf,
    )


def app_for(engine: AsyncEngine, storage: MediaStorage):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return create_app(media_settings(), session_factory=factory, media_storage=storage)


__all__ = [
    "AuthenticatedUser",
    "app_for",
    "create_user",
    "media_engine",
    "media_settings",
]
