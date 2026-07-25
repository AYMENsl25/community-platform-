from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.config import Settings
from talaqi.db.identifiers import generate_uuid7
from talaqi.identity.csrf import CsrfService
from talaqi.identity.sessions import AccessSessionCodec, AccessToken
from talaqi.main import create_app

CURRENT_VERSION = "2026-07-11"


def club_settings() -> Settings:
    return Settings.model_validate(
        {
            "environment": "test",
            "api_public_url": "http://localhost:8000",
            "web_public_url": "http://localhost:3000",
            "allowed_origins": ["http://localhost:3000"],
            "allowed_hosts": ["localhost"],
            "session_secret": "club-test-session-secret",  # pragma: allowlist secret
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
    settings = club_settings()
    now = datetime.now(UTC)
    user_id = generate_uuid7()
    session_id = generate_uuid7()
    csrf = f"csrf-{user_id}"
    csrf_hash = CsrfService(settings.session_secret.get_secret_value()).hash(csrf)
    refresh_hash = hashlib.sha256(str(session_id).encode("ascii")).digest()
    username = f"club_{str(user_id).replace('-', '')[-12:]}"
    rules_version = CURRENT_VERSION if rules_current else "outdated"
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
                    :version, :version, :rules_version, :rules_version,
                    CAST(:now AS timestamptz),
                    CASE WHEN :verified THEN CAST(:now AS timestamptz) ELSE NULL END
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
                    SELECT :user_id, :username, 'Club Creator', country.id, city.id, 'tr',
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


def slug(prefix: str) -> str:
    return f"{prefix}-{str(generate_uuid7()).replace('-', '')[-12:]}"


def complete_club_body(value: str) -> dict[str, object]:
    return {
        "slug": value,
        "name": "Talaqi Runners",
        "description": "A welcoming community for weekly city runs.",
        "category_slug": "sports",
        "country_code": "TR",
        "city_slug": "istanbul",
        "membership_policy": "approval_required",
        "social_links": {"website": "https://example.test/runners"},
        "logo_media_id": None,
        "cover_media_id": None,
    }


def app_for(engine: AsyncEngine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return create_app(club_settings(), session_factory=factory)


async def create_verified_media(engine: AsyncEngine, owner_user_id: UUID) -> UUID:
    media_id = generate_uuid7()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO talaqi.media_assets (
                    id, owner_user_id, status, storage_key, original_filename,
                    content_type, byte_size, width, height, sha256, verified_at
                ) VALUES (
                    :id, :owner_user_id, 'verified', :storage_key, 'club.webp',
                    'image/webp', 128, 64, 64, :sha256, clock_timestamp()
                )
                """
            ),
            {
                "id": media_id,
                "owner_user_id": owner_user_id,
                "storage_key": f"tests/clubs/{media_id}.webp",
                "sha256": bytes(32),
            },
        )
    return media_id


@pytest.mark.asyncio
async def test_incomplete_draft_is_owner_only_and_auto_publishes_when_completed(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    value = slug("draft")
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        created = await client.post(
            "/api/v1/clubs",
            json={"slug": value, "name": "Draft Club"},
            headers=owner.headers(idempotency_key=f"create-{generate_uuid7()}"),
        )
        assert created.status_code == 201
        draft = created.json()
        assert draft["status"] == "draft"
        assert draft["revision"] == 1
        assert draft["missing_fields"] == [
            "description",
            "category_slug",
            "country_code",
            "city_slug",
        ]

        public_draft = await client.get(f"/api/v1/clubs/{value}")
        owner_draft = await client.get(
            f"/api/v1/clubs/{draft['id']}", headers={"cookie": owner.cookie}
        )
        completed = await client.patch(
            f"/api/v1/clubs/{draft['id']}",
            json={
                "revision": 1,
                "description": "A complete community description.",
                "category_slug": "sports",
                "country_code": "TR",
                "city_slug": "istanbul",
            },
            headers=owner.headers(),
        )
        public_club = await client.get(f"/api/v1/clubs/{value}")

    assert public_draft.status_code == 404
    assert owner_draft.status_code == 200
    assert completed.status_code == 200
    assert completed.json()["status"] == "published"
    assert completed.json()["revision"] == 2
    assert completed.json()["missing_fields"] == []
    assert completed.json()["published_at"] is not None
    assert public_club.status_code == 200


@pytest.mark.asyncio
async def test_complete_creation_is_atomic_and_emits_owner_membership_and_audit(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        response = await client.post(
            "/api/v1/clubs",
            json=complete_club_body(slug("published")),
            headers=owner.headers(idempotency_key=f"create-{generate_uuid7()}"),
        )

    assert response.status_code == 201
    club = response.json()
    assert club["status"] == "published"
    assert club["published_at"] is not None
    assert club["membership_policy"] == "approval_required"
    assert club["social_links"] == {"website": "https://example.test/runners"}
    async with club_engine.connect() as connection:
        membership = (
            await connection.execute(
                text(
                    """
                    SELECT role::text
                    FROM talaqi.club_memberships
                    WHERE club_id = :club_id AND user_id = :user_id
                    """
                ),
                {"club_id": UUID(club["id"]), "user_id": owner.user_id},
            )
        ).scalar_one()
        audits = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT action, target_type, request_id, safe_after
                        FROM talaqi.audit_events
                        WHERE target_id = :club_id
                        ORDER BY created_at, id
                        """
                    ),
                    {"club_id": UUID(club["id"])},
                )
            )
            .mappings()
            .all()
        )
    assert membership == "owner"
    assert [row["action"] for row in audits] == ["club.create", "club.publish"]
    assert all(row["target_type"] == "club" for row in audits)
    assert all(row["request_id"] is not None for row in audits)
    assert audits[-1]["safe_after"]["status"] == "published"


@pytest.mark.asyncio
async def test_media_references_must_be_verified_and_owned_by_creator(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    media_owner = await create_user(club_engine)
    attacker = await create_user(club_engine)
    owned_media = await create_verified_media(club_engine, owner.user_id)
    outsider_media = await create_verified_media(club_engine, media_owner.user_id)
    app = app_for(club_engine)
    owned_body = {**complete_club_body(slug("owned-media")), "logo_media_id": str(owned_media)}
    rejected_body = {
        **complete_club_body(slug("cross-media")),
        "cover_media_id": str(outsider_media),
    }
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        accepted = await client.post(
            "/api/v1/clubs",
            json=owned_body,
            headers=owner.headers(idempotency_key=f"create-{generate_uuid7()}"),
        )
        rejected = await client.post(
            "/api/v1/clubs",
            json=rejected_body,
            headers=attacker.headers(idempotency_key=f"create-{generate_uuid7()}"),
        )

    assert accepted.status_code == 201
    assert accepted.json()["logo_media_id"] == str(owned_media)
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "invalid_club"


@pytest.mark.asyncio
async def test_duplicate_slug_is_conflict_across_owners(club_engine: AsyncEngine) -> None:
    first = await create_user(club_engine)
    second = await create_user(club_engine)
    value = slug("duplicate")
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        initial = await client.post(
            "/api/v1/clubs",
            json={"slug": value, "name": "First Club"},
            headers=first.headers(idempotency_key=f"create-{generate_uuid7()}"),
        )
        duplicate = await client.post(
            "/api/v1/clubs",
            json={"slug": value, "name": "Second Club"},
            headers=second.headers(idempotency_key=f"create-{generate_uuid7()}"),
        )

    assert initial.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_slug"


@pytest.mark.asyncio
async def test_stale_revision_and_cross_owner_access_are_denied(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    outsider = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        created = await client.post(
            "/api/v1/clubs",
            json={"slug": slug("revision"), "name": "Revision Club"},
            headers=owner.headers(idempotency_key=f"create-{generate_uuid7()}"),
        )
        club_id = created.json()["id"]
        updated = await client.patch(
            f"/api/v1/clubs/{club_id}",
            json={"revision": 1, "name": "Updated Club"},
            headers=owner.headers(),
        )
        stale = await client.patch(
            f"/api/v1/clubs/{club_id}",
            json={"revision": 1, "name": "Stale Club"},
            headers=owner.headers(),
        )
        outsider_get = await client.get(
            f"/api/v1/clubs/{club_id}", headers={"cookie": outsider.cookie}
        )
        outsider_patch = await client.patch(
            f"/api/v1/clubs/{club_id}",
            json={"revision": 2, "name": "Hijacked Club"},
            headers=outsider.headers(),
        )

    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "stale_revision"
    assert outsider_get.status_code == 403
    assert outsider_patch.status_code == 403


@pytest.mark.asyncio
async def test_concurrent_creation_enforces_regional_owner_limit(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        first, second = await asyncio.gather(
            client.post(
                "/api/v1/clubs",
                json={"slug": slug("limit-a"), "name": "Limit A"},
                headers=owner.headers(idempotency_key=f"create-{generate_uuid7()}"),
            ),
            client.post(
                "/api/v1/clubs",
                json={"slug": slug("limit-b"), "name": "Limit B"},
                headers=owner.headers(idempotency_key=f"create-{generate_uuid7()}"),
            ),
        )

    assert sorted((first.status_code, second.status_code)) == [201, 403]
    denied = first if first.status_code == 403 else second
    assert denied.json()["error"]["code"] == "club_limit_reached"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("user_options", "expected_code"),
    [
        ({"verified": False}, "email_verification_required"),
        ({"profile_complete": False}, "profile_incomplete"),
        ({"rules_current": False}, "rules_acceptance_required"),
    ],
)
async def test_creation_eligibility_fails_closed(
    club_engine: AsyncEngine,
    user_options: dict[str, bool],
    expected_code: str,
) -> None:
    user = await create_user(
        club_engine,
        verified=user_options.get("verified", True),
        profile_complete=user_options.get("profile_complete", True),
        rules_current=user_options.get("rules_current", True),
    )
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        response = await client.post(
            "/api/v1/clubs",
            json={"slug": slug("blocked"), "name": "Blocked Club"},
            headers=user.headers(idempotency_key=f"create-{generate_uuid7()}"),
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == expected_code


@pytest.mark.asyncio
async def test_suspended_club_and_actor_cannot_be_mutated(club_engine: AsyncEngine) -> None:
    owner = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        created = await client.post(
            "/api/v1/clubs",
            json=complete_club_body(slug("suspended")),
            headers=owner.headers(idempotency_key=f"create-{generate_uuid7()}"),
        )
        club_id = UUID(created.json()["id"])
        async with club_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    UPDATE talaqi.clubs
                    SET status = 'suspended', suspended_at = clock_timestamp(),
                        suspension_reason = 'safety_review'
                    WHERE id = :club_id
                    """
                ),
                {"club_id": club_id},
            )
        club_denial = await client.patch(
            f"/api/v1/clubs/{club_id}",
            json={"revision": 1, "name": "Cannot Edit"},
            headers=owner.headers(),
        )
        async with club_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    UPDATE talaqi.users
                    SET status = 'suspended', suspended_at = clock_timestamp(),
                        suspension_reason = 'account_review'
                    WHERE id = :user_id
                    """
                ),
                {"user_id": owner.user_id},
            )
        actor_denial = await client.patch(
            f"/api/v1/clubs/{club_id}",
            json={"revision": 1, "name": "Still Cannot Edit"},
            headers=owner.headers(),
        )

    assert club_denial.status_code == 403
    assert actor_denial.status_code == 401


@pytest.mark.asyncio
async def test_create_is_csrf_protected_and_transactionally_idempotent(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    value = slug("idempotent")
    key = f"create-{generate_uuid7()}"
    body = {"slug": value, "name": "Idempotent Club"}
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        missing_csrf = await client.post(
            "/api/v1/clubs",
            json=body,
            headers={"cookie": owner.cookie, "Idempotency-Key": key},
        )
        first = await client.post(
            "/api/v1/clubs",
            json=body,
            headers=owner.headers(idempotency_key=key),
        )
        replay = await client.post(
            "/api/v1/clubs",
            json=body,
            headers=owner.headers(idempotency_key=key),
        )
        conflict = await client.post(
            "/api/v1/clubs",
            json={**body, "name": "Different Request"},
            headers=owner.headers(idempotency_key=key),
        )

    assert missing_csrf.status_code == 403
    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"
    async with club_engine.connect() as connection:
        count = (
            await connection.execute(
                text("SELECT count(*) FROM talaqi.clubs WHERE owner_user_id = :user_id"),
                {"user_id": owner.user_id},
            )
        ).scalar_one()
    assert count == 1
