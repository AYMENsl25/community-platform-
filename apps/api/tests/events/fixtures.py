from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.config import Settings
from talaqi.db.identifiers import generate_uuid7
from talaqi.identity.csrf import CsrfService
from talaqi.identity.sessions import AccessSessionCodec, AccessToken
from talaqi.main import create_app

CURRENT_VERSION = "2026-07-11"


def event_settings() -> Settings:
    return Settings.model_validate(
        {
            "environment": "test",
            "api_public_url": "http://localhost:8000",
            "web_public_url": "http://localhost:3000",
            "allowed_origins": ["http://localhost:3000"],
            "allowed_hosts": ["localhost"],
            "session_secret": "event-test-session-secret",  # pragma: allowlist secret
            "cookie_secure": False,
            "admin_mfa_required": False,
            "database_url": "postgresql+asyncpg://u:p@localhost/t",  # pragma: allowlist secret
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
    profile_complete: bool = True,
    rules_current: bool = True,
    status: str = "active",
) -> AuthenticatedUser:
    settings = event_settings()
    now = datetime.now(UTC)
    user_id = generate_uuid7()
    session_id = generate_uuid7()
    csrf = f"csrf-{user_id}"
    csrf_hash = CsrfService(settings.session_secret.get_secret_value()).hash(csrf)
    refresh_hash = hashlib.sha256(str(session_id).encode("ascii")).digest()
    username = f"event_{str(user_id).replace('-', '')[-12:]}"
    rules_version = CURRENT_VERSION if rules_current else "outdated"
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO talaqi.users (
                    id, email, password_hash, status, terms_version, privacy_version,
                    organizer_rules_version, community_rules_version, age_attested_at,
                    email_verified_at, suspended_at, suspension_reason
                ) VALUES (
                    :id, :email, '$argon2id$test', CAST(:status AS talaqi.user_status),
                    :version, :version, :rules_version, :rules_version,
                    CAST(:now AS timestamptz),
                    CASE WHEN :verified THEN CAST(:now AS timestamptz) ELSE NULL END,
                    CASE WHEN :status = 'suspended' THEN CAST(:now AS timestamptz) ELSE NULL END,
                    CASE WHEN :status = 'suspended' THEN 'safety_review' ELSE NULL END
                )
                """
            ),
            {
                "id": user_id,
                "email": f"{username}@example.test",
                "status": status,
                "version": CURRENT_VERSION,
                "rules_version": rules_version,
                "now": now,
                "verified": verified,
            },
        )
        if profile_complete:
            await connection.execute(
                text(
                    """
                    INSERT INTO talaqi.profiles (
                        user_id, username, display_name, country_id, city_id, locale,
                        time_zone, preferred_currency, notify_security_email,
                        notify_event_email, notify_community_email, profile_completed_at
                    )
                    SELECT :user_id, :username, 'Event Organizer', country.id, city.id, 'tr',
                           city.time_zone, country.default_currency, true, true, true, :now
                    FROM talaqi.countries AS country
                    JOIN talaqi.cities AS city ON city.country_id = country.id
                    WHERE country.code = 'TR' AND city.slug = 'istanbul'
                    """
                ),
                {"user_id": user_id, "username": username, "now": now},
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
    return AuthenticatedUser(user_id, f"talaqi_access={access}; talaqi_csrf={csrf}", csrf)


def app_for(engine: AsyncEngine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return create_app(event_settings(), session_factory=factory)


def complete_event_body(**changes: object) -> dict[str, object]:
    start = datetime.now(UTC) + timedelta(days=10)
    values: dict[str, object] = {
        "ownership_type": "independent",
        "club_id": None,
        "title": "Talaqi Community Run",
        "description": "A welcoming event for the Talaqi community.",
        "category_slug": "sports",
        "country_code": "TR",
        "city_slug": "istanbul",
        "start_at": start.isoformat(),
        "end_at": (start + timedelta(hours=2)).isoformat(),
        "time_zone": "Europe/Istanbul",
        "capacity": None,
        "visibility": "public",
        "registration_method": "free",
        "cash_expiry_minutes": None,
        "cancellation_cutoff_minutes": None,
        "district": "Kadikoy",
        "public_meeting_area": "Waterfront entrance",
        "exact_address": "Private managed address",
        "latitude": 40.991,
        "longitude": 29.027,
        "exact_venue_is_public": False,
        "cover_media_id": None,
        "publish": True,
    }
    values.update(changes)
    return values


async def create_club(engine: AsyncEngine, owner: AuthenticatedUser) -> UUID:
    club_id = generate_uuid7()
    slug = f"event-club-{str(club_id).replace('-', '')[-12:]}"
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO talaqi.clubs (
                    id, owner_user_id, slug, name, description, category_id,
                    country_id, city_id, membership_policy, status, published_at
                )
                SELECT :id, :owner, :slug, 'Event Club', 'A complete club.',
                       category.id, country.id, city.id, 'open', 'published', clock_timestamp()
                FROM talaqi.categories AS category
                CROSS JOIN talaqi.countries AS country
                JOIN talaqi.cities AS city ON city.country_id = country.id
                WHERE category.slug = 'sports' AND country.code = 'TR'
                  AND city.slug = 'istanbul'
                """
            ),
            {"id": club_id, "owner": owner.user_id, "slug": slug},
        )
        await connection.execute(
            text(
                """
                INSERT INTO talaqi.club_memberships (club_id, user_id, role)
                VALUES (:club_id, :user_id, 'owner')
                """
            ),
            {"club_id": club_id, "user_id": owner.user_id},
        )
    return club_id


async def add_club_member(
    engine: AsyncEngine, club_id: UUID, user: AuthenticatedUser, *, role: str
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO talaqi.club_memberships (club_id, user_id, role)
                VALUES (:club_id, :user_id, CAST(:role AS talaqi.club_role))
                """
            ),
            {"club_id": club_id, "user_id": user.user_id, "role": role},
        )


async def create_media(
    engine: AsyncEngine, owner: AuthenticatedUser, *, status: str = "verified"
) -> UUID:
    media_id = generate_uuid7()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO talaqi.media_assets (
                    id, owner_user_id, status, storage_key, original_filename,
                    content_type, byte_size, width, height, sha256, verified_at
                ) VALUES (
                    :id, :owner_user_id, CAST(:status AS talaqi.media_status),
                    :storage_key, 'event.webp', 'image/webp', 128,
                    CASE WHEN :status = 'verified' THEN 64 ELSE NULL END,
                    CASE WHEN :status = 'verified' THEN 64 ELSE NULL END,
                    CASE WHEN :status = 'verified' THEN CAST(:sha256 AS bytea) ELSE NULL END,
                    CASE WHEN :status = 'verified' THEN clock_timestamp() ELSE NULL END
                )
                """
            ),
            {
                "id": media_id,
                "owner_user_id": owner.user_id,
                "status": status,
                "storage_key": f"tests/events/{media_id}.webp",
                "sha256": bytes(32),
            },
        )
    return media_id
