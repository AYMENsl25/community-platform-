from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.config import Settings
from talaqi.db.identifiers import generate_uuid7
from talaqi.identity.csrf import CsrfService
from talaqi.identity.sessions import AccessSessionCodec, AccessToken
from talaqi.main import create_app
from talaqi.profiles.models import ProfileReplacement
from talaqi.profiles.repository import ProfileRepository
from talaqi.profiles.service import ProfileService
from talaqi.regions.repository import RegionRepository
from talaqi.regions.service import RegionPolicyService


def profile_settings(*, admin_mfa_required: bool = False) -> Settings:
    return Settings.model_validate(
        {
            "environment": "test",
            "api_public_url": "http://localhost:8000",
            "web_public_url": "http://localhost:3000",
            "allowed_origins": ["http://localhost:3000"],
            "allowed_hosts": ["localhost"],
            "session_secret": "profile-test-session-secret",
            "cookie_secure": False,
            "admin_mfa_required": admin_mfa_required,
            "database_url": "postgresql+asyncpg://unused:unused@localhost:5432/unused_test",
            "s3_endpoint": "http://localhost:9000",
            "s3_bucket": "test",
            "s3_access_key": "access",
            "s3_secret_key": "secret",
            "smtp_host": "localhost",
            "smtp_port": 1025,
            "log_level": "DEBUG",
        }
    )


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: UUID
    cookie: str
    csrf: str


async def create_authenticated_user(
    engine: AsyncEngine,
    *,
    email: str,
    verified: bool,
    platform_admin: bool = False,
) -> AuthenticatedUser:
    settings = profile_settings()
    now = datetime.now(UTC)
    user_id = generate_uuid7()
    session_id = generate_uuid7()
    csrf = f"csrf-{user_id}"
    csrf_hash = CsrfService(settings.session_secret.get_secret_value()).hash(csrf)
    refresh_hash = hashlib.sha256(str(session_id).encode("ascii")).digest()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """DELETE FROM talaqi.profiles
                WHERE user_id IN (SELECT id FROM talaqi.users WHERE email = :email)"""
            ),
            {"email": email},
        )
        await connection.execute(
            text("DELETE FROM talaqi.users WHERE email = :email"),
            {"email": email},
        )
        await connection.execute(
            text(
                """
                INSERT INTO talaqi.users (
                    id,email,password_hash,terms_version,privacy_version,age_attested_at,
                    email_verified_at,is_platform_admin
                ) VALUES (
                    :id,:email,'$argon2id$test','2026-07-11','2026-07-11',CAST(:now AS timestamptz),
                    CASE WHEN :verified THEN CAST(:now AS timestamptz) ELSE NULL END,:platform_admin
                )
                """
            ),
            {
                "id": user_id,
                "email": email,
                "now": now,
                "verified": verified,
                "platform_admin": platform_admin,
            },
        )
        await connection.execute(
            text(
                """
                INSERT INTO talaqi.sessions (
                    id,user_id,family_id,refresh_token_hash,csrf_secret_hash,expires_at
                ) VALUES (:id,:user_id,:family_id,:refresh_hash,:csrf_hash,:expires_at)
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


def replacement(username: str = "Member_25") -> dict[str, object]:
    return {
        "username": username,
        "display_name": "  Talaqi Member  ",
        "country_code": "tr",
        "city_slug": "ISTANBUL",
        "locale": "tr",
        "time_zone": "Europe/Istanbul",
        "preferred_currency": "try",
        "notify_event_email": True,
        "notify_community_email": False,
        "organizer_rules_version": "2026-07-11",
        "community_rules_version": "2026-07-11",
    }


async def delete_users(engine: AsyncEngine, *user_ids: UUID) -> None:
    async with engine.begin() as connection:
        identifiers = {"ids": list(user_ids)}
        await connection.execute(
            text("DELETE FROM talaqi.events WHERE owner_user_id = ANY(CAST(:ids AS uuid[]))"),
            identifiers,
        )
        await connection.execute(
            text("DELETE FROM talaqi.clubs WHERE owner_user_id = ANY(CAST(:ids AS uuid[]))"),
            identifiers,
        )
        await connection.execute(
            text("DELETE FROM talaqi.profiles WHERE user_id = ANY(CAST(:ids AS uuid[]))"),
            identifiers,
        )
        await connection.execute(
            text("DELETE FROM talaqi.users WHERE id = ANY(CAST(:ids AS uuid[]))"),
            identifiers,
        )


@pytest.mark.asyncio
async def test_profile_routes_are_caller_owned_safe_and_csrf_protected(
    profile_engine: AsyncEngine,
) -> None:
    user = await create_authenticated_user(
        profile_engine, email="profile-route@example.test", verified=True
    )
    factory = async_sessionmaker(profile_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(profile_settings(), session_factory=factory)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            missing = await client.get("/api/v1/me", headers={"cookie": user.cookie})
            missing_capabilities = await client.get(
                "/api/v1/me/capabilities", headers={"cookie": user.cookie}
            )
            no_csrf = await client.patch(
                "/api/v1/me", json=replacement(), headers={"cookie": user.cookie}
            )
            updated = await client.patch(
                "/api/v1/me",
                json=replacement(),
                headers={"cookie": user.cookie, "X-CSRF-Token": user.csrf},
            )
            fetched = await client.get("/api/v1/me", headers={"cookie": user.cookie})
            capabilities = await client.get(
                "/api/v1/me/capabilities", headers={"cookie": user.cookie}
            )

        assert missing.status_code == 200
        assert missing.json()["username"] is None
        assert missing.json()["avatar"] is None
        assert missing_capabilities.status_code == 200
        assert missing_capabilities.json()["blockers"] == ["profile_incomplete"]
        assert missing_capabilities.json()["create_club"] is False
        assert missing_capabilities.json()["create_independent_event"] is False
        assert no_csrf.status_code == 403
        assert no_csrf.json()["error"]["code"] == "csrf_failed"
        assert updated.status_code == fetched.status_code == 200
        assert updated.json() == fetched.json()
        assert updated.json()["username"] == "member_25"
        assert updated.json()["display_name"] == "Talaqi Member"
        assert updated.json()["notify_security_email"] is True
        assert updated.json()["avatar"] is None
        serialized = repr(updated.json())
        assert "profile-route@example.test" not in serialized
        assert "is_platform_admin" not in serialized
        assert capabilities.json() == {
            "create_club": True,
            "create_independent_event": True,
            "save_event": True,
            "register_event": True,
            "access_admin": False,
            "blockers": [],
        }
    finally:
        await delete_users(profile_engine, user.user_id)


@pytest.mark.asyncio
async def test_security_email_and_avatar_are_not_editable(
    profile_engine: AsyncEngine,
) -> None:
    user = await create_authenticated_user(
        profile_engine, email="profile-security@example.test", verified=True
    )
    factory = async_sessionmaker(profile_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(profile_settings(), session_factory=factory)
    body = replacement()
    body["notify_security_email"] = False
    body["avatar"] = "not-allowed"
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            response = await client.patch(
                "/api/v1/me",
                json=body,
                headers={"cookie": user.cookie, "X-CSRF-Token": user.csrf},
            )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
    finally:
        await delete_users(profile_engine, user.user_id)


@pytest.mark.asyncio
async def test_unverified_complete_profile_remains_restricted(
    profile_engine: AsyncEngine,
) -> None:
    user = await create_authenticated_user(
        profile_engine, email="profile-unverified@example.test", verified=False
    )
    factory = async_sessionmaker(profile_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(profile_settings(), session_factory=factory)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            updated = await client.patch(
                "/api/v1/me",
                json=replacement("restricted_member"),
                headers={"cookie": user.cookie, "X-CSRF-Token": user.csrf},
            )
            capabilities = await client.get(
                "/api/v1/me/capabilities", headers={"cookie": user.cookie}
            )
        assert updated.status_code == 200
        assert capabilities.status_code == 200
        assert capabilities.json()["save_event"] is False
        assert capabilities.json()["register_event"] is False
        assert capabilities.json()["blockers"] == ["email_verification_required"]
    finally:
        await delete_users(profile_engine, user.user_id)


@pytest.mark.asyncio
async def test_normalized_username_race_has_one_winner_and_no_cross_user_leak(
    profile_engine: AsyncEngine,
) -> None:
    first = await create_authenticated_user(
        profile_engine, email="profile-race-one@example.test", verified=True
    )
    second = await create_authenticated_user(
        profile_engine, email="profile-race-two@example.test", verified=True
    )
    factory = async_sessionmaker(profile_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(profile_settings(), session_factory=factory)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            responses = await asyncio.gather(
                client.patch(
                    "/api/v1/me",
                    json=replacement("Shared_Name"),
                    headers={"cookie": first.cookie, "X-CSRF-Token": first.csrf},
                ),
                client.patch(
                    "/api/v1/me",
                    json=replacement(" shared_name "),
                    headers={"cookie": second.cookie, "X-CSRF-Token": second.csrf},
                ),
            )
            reads = await asyncio.gather(
                client.get("/api/v1/me", headers={"cookie": first.cookie}),
                client.get("/api/v1/me", headers={"cookie": second.cookie}),
            )
        assert sorted(response.status_code for response in responses) == [200, 409]
        assert sum(response.json()["username"] == "shared_name" for response in reads) == 1
        assert all("email" not in response.json() for response in reads)
    finally:
        await delete_users(profile_engine, first.user_id, second.user_id)


def test_profile_openapi_is_lazy_and_has_no_actor_identifier() -> None:
    document = create_app().openapi()
    assert set(document["paths"]) >= {"/api/v1/me", "/api/v1/me/capabilities"}
    assert set(document["paths"]["/api/v1/me"]) == {"get", "patch"}
    rendered = repr(document["paths"]["/api/v1/me"])
    assert "user_id" not in rendered
    assert "email" not in document["components"]["schemas"]["ProfileResponse"]["properties"]


@pytest.mark.asyncio
async def test_patch_is_complete_replacement_of_editable_profile_values(
    profile_engine: AsyncEngine,
) -> None:
    user = await create_authenticated_user(
        profile_engine, email="profile-replacement@example.test", verified=True
    )
    factory = async_sessionmaker(profile_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(profile_settings(), session_factory=factory)
    try:
        second = replacement("replacement_member")
        second.update(
            display_name="  Replacement Name  ",
            locale="en",
            notify_event_email=False,
            notify_community_email=True,
        )
        incomplete = dict(second)
        incomplete.pop("notify_community_email")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            first_response = await client.patch(
                "/api/v1/me",
                json=replacement("original_member"),
                headers={"cookie": user.cookie, "X-CSRF-Token": user.csrf},
            )
            second_response = await client.patch(
                "/api/v1/me",
                json=second,
                headers={"cookie": user.cookie, "X-CSRF-Token": user.csrf},
            )
            rejected = await client.patch(
                "/api/v1/me",
                json=incomplete,
                headers={"cookie": user.cookie, "X-CSRF-Token": user.csrf},
            )
            fetched = await client.get("/api/v1/me", headers={"cookie": user.cookie})

        assert first_response.status_code == second_response.status_code == 200
        assert rejected.status_code == 422
        assert second_response.json() == fetched.json()
        assert second_response.json()["username"] == "replacement_member"
        assert second_response.json()["display_name"] == "Replacement Name"
        assert second_response.json()["locale"] == "en"
        assert second_response.json()["notify_event_email"] is False
        assert second_response.json()["notify_community_email"] is True
        assert second_response.json()["profile_completed_at"] is not None
    finally:
        await delete_users(profile_engine, user.user_id)


@pytest.mark.asyncio
async def test_real_ownership_counts_enforce_regional_limits(
    profile_engine: AsyncEngine,
) -> None:
    user = await create_authenticated_user(
        profile_engine, email="profile-counts@example.test", verified=True
    )
    factory = async_sessionmaker(profile_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(profile_settings(), session_factory=factory)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            completed = await client.patch(
                "/api/v1/me",
                json=replacement("counted_member"),
                headers={"cookie": user.cookie, "X-CSRF-Token": user.csrf},
            )
        assert completed.status_code == 200

        async with profile_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    INSERT INTO talaqi.clubs (id, owner_user_id, slug, name)
                    VALUES (:id, :user_id, :slug, 'Counted club')
                    """
                ),
                {
                    "id": generate_uuid7(),
                    "user_id": user.user_id,
                    "slug": f"counted-{user.user_id.hex}",
                },
            )
            for number in range(3):
                await connection.execute(
                    text(
                        """
                        INSERT INTO talaqi.events (
                            id, ownership_type, owner_user_id, title
                        ) VALUES (:id, 'independent', :user_id, :title)
                        """
                    ),
                    {
                        "id": generate_uuid7(),
                        "user_id": user.user_id,
                        "title": f"Counted event {number}",
                    },
                )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            capabilities = await client.get(
                "/api/v1/me/capabilities", headers={"cookie": user.cookie}
            )

        assert capabilities.status_code == 200
        assert capabilities.json()["create_club"] is False
        assert capabilities.json()["create_independent_event"] is False
        assert capabilities.json()["save_event"] is True
        assert capabilities.json()["register_event"] is True
        assert capabilities.json()["blockers"] == [
            "club_limit_reached",
            "independent_event_limit_reached",
        ]
    finally:
        await delete_users(profile_engine, user.user_id)


@pytest.mark.asyncio
async def test_stale_rules_and_disabled_region_have_exact_blockers(
    profile_engine: AsyncEngine,
) -> None:
    user = await create_authenticated_user(
        profile_engine, email="profile-stale-region@example.test", verified=True
    )
    factory = async_sessionmaker(profile_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(profile_settings(), session_factory=factory)
    country_disabled = False
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            completed = await client.patch(
                "/api/v1/me",
                json=replacement("stale_region_member"),
                headers={"cookie": user.cookie, "X-CSRF-Token": user.csrf},
            )
        assert completed.status_code == 200

        async with profile_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    UPDATE talaqi.users
                    SET organizer_rules_version = 'superseded'
                    WHERE id = :user_id
                    """
                ),
                {"user_id": user.user_id},
            )
            await connection.execute(
                text("UPDATE talaqi.countries SET enabled = false WHERE code = 'TR'")
            )
            country_disabled = True

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            capabilities = await client.get(
                "/api/v1/me/capabilities", headers={"cookie": user.cookie}
            )

        assert capabilities.status_code == 200
        assert capabilities.json()["blockers"] == [
            "rules_acceptance_required",
            "region_unavailable",
        ]
        assert capabilities.json()["save_event"] is False
        assert capabilities.json()["register_event"] is False
    finally:
        if country_disabled:
            async with profile_engine.begin() as connection:
                await connection.execute(
                    text("UPDATE talaqi.countries SET enabled = true WHERE code = 'TR'")
                )
        await delete_users(profile_engine, user.user_id)


@pytest.mark.asyncio
async def test_platform_admin_requires_real_verified_mfa_factor(
    profile_engine: AsyncEngine,
) -> None:
    user = await create_authenticated_user(
        profile_engine,
        email="profile-admin-mfa@example.test",
        verified=True,
        platform_admin=True,
    )
    factory = async_sessionmaker(profile_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(
        profile_settings(admin_mfa_required=True),
        session_factory=factory,
    )
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            completed = await client.patch(
                "/api/v1/me",
                json=replacement("admin_mfa_member"),
                headers={"cookie": user.cookie, "X-CSRF-Token": user.csrf},
            )
            blocked = await client.get("/api/v1/me/capabilities", headers={"cookie": user.cookie})
        assert completed.status_code == 200
        assert blocked.json()["access_admin"] is False
        assert blocked.json()["blockers"] == ["admin_mfa_required"]

        async with profile_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    INSERT INTO talaqi.user_mfa_factors (
                        id, user_id, factor_type, secret_ciphertext, verified_at
                    ) VALUES (:id, :user_id, 'totp', :secret, :verified_at)
                    """
                ),
                {
                    "id": generate_uuid7(),
                    "user_id": user.user_id,
                    "secret": b"test-ciphertext",
                    "verified_at": datetime.now(UTC),
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            allowed = await client.get("/api/v1/me/capabilities", headers={"cookie": user.cookie})
        assert allowed.status_code == 200
        assert allowed.json()["access_admin"] is True
        assert allowed.json()["blockers"] == []
    finally:
        await delete_users(profile_engine, user.user_id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("country_code", "DZ"),
        ("city_slug", "algiers"),
        ("locale", "fr"),
        ("time_zone", "Africa/Algiers"),
        ("preferred_currency", "DZD"),
    ],
)
async def test_route_rejects_incompatible_region_profile_combinations(
    profile_engine: AsyncEngine,
    field: str,
    value: str,
) -> None:
    user = await create_authenticated_user(
        profile_engine,
        email=f"profile-invalid-{field.replace('_', '-')}@example.test",
        verified=True,
    )
    factory = async_sessionmaker(profile_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(profile_settings(), session_factory=factory)
    body = replacement(f"invalid_{field}")
    body[field] = value
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            response = await client.patch(
                "/api/v1/me",
                json=body,
                headers={"cookie": user.cookie, "X-CSRF-Token": user.csrf},
            )
            fetched = await client.get("/api/v1/me", headers={"cookie": user.cookie})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_profile"
        assert fetched.status_code == 200
        assert fetched.json()["profile_completed_at"] is None
    finally:
        await delete_users(profile_engine, user.user_id)


async def apply_region_mutation(
    engine: AsyncEngine,
    mutation: str,
    *,
    user_id: UUID | None = None,
) -> dict[str, object]:
    statements = {
        "country_disabled": (
            "UPDATE talaqi.countries SET enabled = false WHERE code = 'TR'",
            "UPDATE talaqi.countries SET enabled = true WHERE code = 'TR'",
        ),
        "city_disabled": (
            """UPDATE talaqi.cities SET enabled = false
               WHERE country_id = (SELECT id FROM talaqi.countries WHERE code = 'TR')
                 AND slug = 'istanbul'""",
            """UPDATE talaqi.cities SET enabled = true
               WHERE country_id = (SELECT id FROM talaqi.countries WHERE code = 'TR')
                 AND slug = 'istanbul'""",
        ),
        "beta_disabled": (
            """UPDATE talaqi.cities SET beta_enabled = false
               WHERE country_id = (SELECT id FROM talaqi.countries WHERE code = 'TR')
                 AND slug = 'istanbul'""",
            """UPDATE talaqi.cities SET beta_enabled = true
               WHERE country_id = (SELECT id FROM talaqi.countries WHERE code = 'TR')
                 AND slug = 'istanbul'""",
        ),
        "currency_changed": (
            "UPDATE talaqi.countries SET default_currency = 'USD' WHERE code = 'TR'",
            "UPDATE talaqi.countries SET default_currency = 'TRY' WHERE code = 'TR'",
        ),
        "timezone_changed": (
            """UPDATE talaqi.cities SET time_zone = 'UTC'
               WHERE country_id = (SELECT id FROM talaqi.countries WHERE code = 'TR')
                 AND slug = 'istanbul'""",
            """UPDATE talaqi.cities SET time_zone = 'Europe/Istanbul'
               WHERE country_id = (SELECT id FROM talaqi.countries WHERE code = 'TR')
                 AND slug = 'istanbul'""",
        ),
    }
    async with engine.begin() as connection:
        if mutation == "policy_missing":
            row = (
                (
                    await connection.execute(
                        text(
                            """SELECT policy.*
                           FROM talaqi.regional_policies AS policy
                           JOIN talaqi.countries AS country ON country.id = policy.country_id
                           WHERE country.code = 'TR'"""
                        )
                    )
                )
                .mappings()
                .one()
            )
            snapshot = dict(row)

            await connection.execute(
                text(
                    """DELETE FROM talaqi.regional_policies
                       WHERE country_id = (SELECT id FROM talaqi.countries WHERE code = 'TR')"""
                )
            )
            return snapshot
        if mutation == "profile_locale_changed":
            assert user_id is not None
            await connection.execute(
                text("UPDATE talaqi.profiles SET locale = 'fr' WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
            return {}
        apply_sql, _restore_sql = statements[mutation]
        await connection.execute(text(apply_sql))
    return {}


async def restore_region_mutation(
    engine: AsyncEngine,
    mutation: str,
    snapshot: dict[str, object],
    *,
    user_id: UUID | None = None,
) -> None:
    restore_statements = {
        "country_disabled": "UPDATE talaqi.countries SET enabled = true WHERE code = 'TR'",
        "city_disabled": """UPDATE talaqi.cities SET enabled = true
            WHERE country_id = (SELECT id FROM talaqi.countries WHERE code = 'TR')
              AND slug = 'istanbul'""",
        "beta_disabled": """UPDATE talaqi.cities SET beta_enabled = true
            WHERE country_id = (SELECT id FROM talaqi.countries WHERE code = 'TR')
              AND slug = 'istanbul'""",
        "currency_changed": (
            "UPDATE talaqi.countries SET default_currency = 'TRY' WHERE code = 'TR'"
        ),
        "timezone_changed": """UPDATE talaqi.cities SET time_zone = 'Europe/Istanbul'
            WHERE country_id = (SELECT id FROM talaqi.countries WHERE code = 'TR')
              AND slug = 'istanbul'""",
    }
    async with engine.begin() as connection:
        if mutation == "policy_missing":
            await connection.execute(
                text(
                    """INSERT INTO talaqi.regional_policies (
                           id, country_id, allowed_registration_methods,
                           cash_expiry_default_minutes, cash_expiry_min_minutes,
                           cash_expiry_max_minutes, cancellation_default_minutes,
                           cancellation_min_minutes, cancellation_max_minutes,
                           default_club_ownership_limit,
                           default_active_independent_event_limit,
                           exact_venue_public_by_default, revision, created_at, updated_at
                       ) VALUES (
                           :id, :country_id,
                           CAST(:allowed_registration_methods AS talaqi.registration_method[]),
                           :cash_expiry_default_minutes, :cash_expiry_min_minutes,
                           :cash_expiry_max_minutes, :cancellation_default_minutes,
                           :cancellation_min_minutes, :cancellation_max_minutes,
                           :default_club_ownership_limit,
                           :default_active_independent_event_limit,
                           :exact_venue_public_by_default, :revision, :created_at, :updated_at
                       )"""
                ),
                snapshot,
            )
            return
        if mutation == "profile_locale_changed":
            assert user_id is not None
            await connection.execute(
                text("UPDATE talaqi.profiles SET locale = 'tr' WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
            return
        await connection.execute(text(restore_statements[mutation]))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutation",
    [
        "country_disabled",
        "city_disabled",
        "beta_disabled",
        "profile_locale_changed",
        "currency_changed",
        "timezone_changed",
        "policy_missing",
    ],
)
async def test_post_completion_region_mutations_fail_closed_with_exact_capabilities(
    profile_engine: AsyncEngine,
    mutation: str,
) -> None:
    user = await create_authenticated_user(
        profile_engine,
        email=f"profile-current-region-{mutation.replace('_', '-')}@example.test",
        verified=True,
        platform_admin=True,
    )
    factory = async_sessionmaker(profile_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(profile_settings(), session_factory=factory)
    snapshot: dict[str, object] | None = None
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            completed = await client.patch(
                "/api/v1/me",
                json=replacement(f"current_{mutation}"),
                headers={"cookie": user.cookie, "X-CSRF-Token": user.csrf},
            )
            before = await client.get("/api/v1/me/capabilities", headers={"cookie": user.cookie})
        assert completed.status_code == 200
        assert before.json()["access_admin"] is True
        assert before.json()["blockers"] == []

        snapshot = await apply_region_mutation(
            profile_engine,
            mutation,
            user_id=user.user_id,
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            capabilities = await client.get(
                "/api/v1/me/capabilities", headers={"cookie": user.cookie}
            )

        assert capabilities.status_code == 200
        assert capabilities.json() == {
            "create_club": False,
            "create_independent_event": False,
            "save_event": False,
            "register_event": False,
            "access_admin": False,
            "blockers": ["region_unavailable"],
        }
    finally:
        if snapshot is not None:
            await restore_region_mutation(
                profile_engine,
                mutation,
                snapshot,
                user_id=user.user_id,
            )
        await delete_users(profile_engine, user.user_id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mutation", "body_field", "body_value"),
    [
        ("country_disabled", None, None),
        ("city_disabled", None, None),
        ("beta_disabled", None, None),
        ("policy_missing", None, None),
        (None, "locale", "fr"),
        (None, "preferred_currency", "DZD"),
        (None, "time_zone", "Africa/Algiers"),
    ],
)
async def test_rejected_profile_replacement_preserves_profile_and_rule_versions(
    profile_engine: AsyncEngine,
    mutation: str | None,
    body_field: str | None,
    body_value: str | None,
) -> None:
    case = mutation or body_field or "unknown"
    user = await create_authenticated_user(
        profile_engine,
        email=f"profile-atomic-{case.replace('_', '-')}@example.test",
        verified=True,
    )
    factory = async_sessionmaker(profile_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(profile_settings(), session_factory=factory)
    snapshot: dict[str, object] | None = None
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            completed = await client.patch(
                "/api/v1/me",
                json=replacement(f"original_{case}"),
                headers={"cookie": user.cookie, "X-CSRF-Token": user.csrf},
            )
        assert completed.status_code == 200
        async with profile_engine.begin() as connection:
            await connection.execute(
                text(
                    """UPDATE talaqi.users
                       SET organizer_rules_version = 'previous-organizer',
                           community_rules_version = 'previous-community'
                       WHERE id = :user_id"""
                ),
                {"user_id": user.user_id},
            )
        if mutation is not None:
            snapshot = await apply_region_mutation(profile_engine, mutation)

        body = replacement(f"changed_{case}")
        body["display_name"] = "Changed display"
        if body_field is not None:
            body[body_field] = body_value
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            rejected = await client.patch(
                "/api/v1/me",
                json=body,
                headers={"cookie": user.cookie, "X-CSRF-Token": user.csrf},
            )
        assert rejected.status_code == 422
        assert rejected.json()["error"]["code"] == "invalid_profile"

        async with profile_engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            """SELECT profile.username, profile.display_name,
                                  users.organizer_rules_version,
                                  users.community_rules_version
                           FROM talaqi.profiles AS profile
                           JOIN talaqi.users AS users ON users.id = profile.user_id
                           WHERE profile.user_id = :user_id"""
                        ),
                        {"user_id": user.user_id},
                    )
                )
                .mappings()
                .one()
            )
        assert row["username"] == f"original_{case}"
        assert row["display_name"] == "Talaqi Member"
        assert row["organizer_rules_version"] == "previous-organizer"
        assert row["community_rules_version"] == "previous-community"
    finally:
        if mutation is not None and snapshot is not None:
            await restore_region_mutation(profile_engine, mutation, snapshot)
        await delete_users(profile_engine, user.user_id)


@pytest.mark.asyncio
async def test_profile_write_locks_country_city_and_policy_until_commit(
    profile_engine: AsyncEngine,
) -> None:
    user = await create_authenticated_user(
        profile_engine,
        email="profile-region-locks@example.test",
        verified=True,
    )
    factory = async_sessionmaker(profile_engine, class_=AsyncSession, expire_on_commit=False)
    updates = (
        "UPDATE talaqi.countries SET default_currency = 'USD' WHERE code = 'TR'",
        """UPDATE talaqi.cities SET time_zone = 'UTC'
           WHERE country_id = (SELECT id FROM talaqi.countries WHERE code = 'TR')
             AND slug = 'istanbul'""",
        """UPDATE talaqi.regional_policies SET default_club_ownership_limit = 2
           WHERE country_id = (SELECT id FROM talaqi.countries WHERE code = 'TR')""",
    )
    try:
        async with factory() as writer_session, writer_session.begin():
            service = ProfileService(
                ProfileRepository(writer_session),
                RegionPolicyService(RegionRepository(writer_session)),
                current_organizer_rules_version="2026-07-11",
                current_community_rules_version="2026-07-11",
            )
            profile = await service.replace(
                user.user_id,
                ProfileReplacement(**replacement("locked_region_member")),  # pyright: ignore[reportArgumentType]
            )
            assert profile.preferred_currency == "TRY"
            assert profile.time_zone == "Europe/Istanbul"

            for update in updates:
                async with profile_engine.connect() as contender:
                    transaction = await contender.begin()
                    await contender.execute(text("SET LOCAL lock_timeout = '150ms'"))
                    with pytest.raises(DBAPIError, match="lock timeout"):
                        await contender.execute(text(update))
                    await transaction.rollback()

        async with profile_engine.connect() as connection:
            stored = (
                (
                    await connection.execute(
                        text(
                            """SELECT profile.preferred_currency, profile.time_zone
                           FROM talaqi.profiles AS profile
                           WHERE profile.user_id = :user_id"""
                        ),
                        {"user_id": user.user_id},
                    )
                )
                .mappings()
                .one()
            )
        assert stored["preferred_currency"].strip() == "TRY"
        assert stored["time_zone"] == "Europe/Istanbul"
    finally:
        await delete_users(profile_engine, user.user_id)


@pytest.mark.asyncio
async def test_username_conflict_rolls_back_profile_and_rule_versions(
    profile_engine: AsyncEngine,
) -> None:
    first = await create_authenticated_user(
        profile_engine,
        email="profile-atomic-conflict-first@example.test",
        verified=True,
    )
    second = await create_authenticated_user(
        profile_engine,
        email="profile-atomic-conflict-second@example.test",
        verified=True,
    )
    factory = async_sessionmaker(profile_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(profile_settings(), session_factory=factory)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            first_completed = await client.patch(
                "/api/v1/me",
                json=replacement("atomic_original"),
                headers={"cookie": first.cookie, "X-CSRF-Token": first.csrf},
            )
            second_completed = await client.patch(
                "/api/v1/me",
                json=replacement("atomic_reserved"),
                headers={"cookie": second.cookie, "X-CSRF-Token": second.csrf},
            )
        assert first_completed.status_code == second_completed.status_code == 200
        async with profile_engine.begin() as connection:
            await connection.execute(
                text(
                    """UPDATE talaqi.users
                       SET organizer_rules_version = 'previous-organizer',
                           community_rules_version = 'previous-community'
                       WHERE id = :user_id"""
                ),
                {"user_id": first.user_id},
            )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            conflict = await client.patch(
                "/api/v1/me",
                json=replacement("atomic_reserved"),
                headers={"cookie": first.cookie, "X-CSRF-Token": first.csrf},
            )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "username_unavailable"

        async with profile_engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            """SELECT profile.username,
                                  users.organizer_rules_version,
                                  users.community_rules_version
                           FROM talaqi.profiles AS profile
                           JOIN talaqi.users AS users ON users.id = profile.user_id
                           WHERE profile.user_id = :user_id"""
                        ),
                        {"user_id": first.user_id},
                    )
                )
                .mappings()
                .one()
            )
        assert row["username"] == "atomic_original"
        assert row["organizer_rules_version"] == "previous-organizer"
        assert row["community_rules_version"] == "previous-community"
    finally:
        await delete_users(profile_engine, first.user_id, second.user_id)
