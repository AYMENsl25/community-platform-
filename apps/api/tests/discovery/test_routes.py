from __future__ import annotations

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
from talaqi.discovery.fixtures import (
    PUBLIC_CLUB_IDS,
    PUBLIC_EVENT_IDS,
    seed_discovery_fixtures,
)
from talaqi.identity.csrf import CsrfService
from talaqi.identity.sessions import AccessSessionCodec, AccessToken
from talaqi.main import create_app

pytestmark = pytest.mark.asyncio


def settings() -> Settings:
    return Settings.model_validate(
        {
            "environment": "test",
            "api_public_url": "http://localhost:8000",
            "web_public_url": "http://localhost:3000",
            "allowed_origins": ["http://localhost:3000"],
            "allowed_hosts": ["localhost"],
            "session_secret": "discovery-test-session-secret-123456",  # pragma: allowlist secret
            "cookie_secure": False,
            "admin_mfa_required": False,
            "database_url": "postgresql://u:p@localhost/unused_test",  # pragma: allowlist secret
            "s3_endpoint": "http://localhost:9000",
            "s3_bucket": "test",
            "s3_access_key": "access",
            "s3_secret_key": "secret",  # pragma: allowlist secret
            "smtp_host": "localhost",
            "smtp_port": 1025,
            "log_level": "DEBUG",
        }
    )


@dataclass(frozen=True)
class Member:
    id: UUID
    cookie: str
    csrf: str


async def create_member(engine: AsyncEngine, *, verified: bool, complete: bool) -> Member:
    configured = settings()
    now = datetime.now(UTC)
    user_id, session_id = generate_uuid7(), generate_uuid7()
    csrf = f"csrf-{user_id}"
    csrf_hash = CsrfService(configured.session_secret.get_secret_value()).hash(csrf)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """INSERT INTO talaqi.users (
                       id,email,password_hash,terms_version,privacy_version,age_attested_at,
                       email_verified_at,organizer_rules_version,community_rules_version
                   ) VALUES (
                       :id,:email,'$argon2id$test',:terms,:privacy,CAST(:now AS timestamptz),
                       CASE WHEN :verified THEN CAST(:now AS timestamptz) END,:organizer,:community
                   )"""
            ),
            {
                "id": user_id,
                "email": f"discovery-{user_id}@example.test",
                "terms": configured.current_terms_version,
                "privacy": configured.current_privacy_version,
                "organizer": configured.current_organizer_rules_version,
                "community": configured.current_community_rules_version,
                "now": now,
                "verified": verified,
            },
        )
        if complete:
            await connection.execute(
                text(
                    """INSERT INTO talaqi.profiles (
                           user_id,username,display_name,country_id,city_id,locale,time_zone,
                           preferred_currency,profile_completed_at
                       ) SELECT :id,:username,'Discovery Member',country.id,city.id,'tr',
                                city.time_zone,country.default_currency,:now
                         FROM talaqi.countries AS country
                         JOIN talaqi.cities AS city ON city.country_id=country.id
                         WHERE country.code='TR' AND city.slug='istanbul'"""
                ),
                {"id": user_id, "username": f"d{str(user_id).replace('-', '')[:20]}", "now": now},
            )
        await connection.execute(
            text(
                """INSERT INTO talaqi.sessions (
                       id,user_id,family_id,refresh_token_hash,csrf_secret_hash,expires_at
                   ) VALUES (:id,:user_id,:family,:refresh,:csrf,:expires)"""
            ),
            {
                "id": session_id,
                "user_id": user_id,
                "family": generate_uuid7(),
                "refresh": hashlib.sha256(str(session_id).encode()).digest(),
                "csrf": csrf_hash,
                "expires": now + timedelta(days=1),
            },
        )
    access = AccessSessionCodec(configured.session_secret.get_secret_value()).encode(
        AccessToken(session_id, user_id, now - timedelta(seconds=1))
    )
    return Member(user_id, f"talaqi_access={access}; talaqi_csrf={csrf}", csrf)


async def cleanup(engine: AsyncEngine, *members: Member) -> None:
    async with engine.begin() as connection:
        ids = [member.id for member in members]
        await connection.execute(
            text("DELETE FROM talaqi.profiles WHERE user_id=ANY(CAST(:ids AS uuid[]))"),
            {"ids": ids},
        )
        await connection.execute(
            text("DELETE FROM talaqi.users WHERE id=ANY(CAST(:ids AS uuid[]))"), {"ids": ids}
        )


async def test_public_routes_filter_paginate_search_and_never_expose_private_fields(
    discovery_engine: AsyncEngine,
) -> None:
    async with (
        async_sessionmaker(discovery_engine, class_=AsyncSession)() as session,
        session.begin(),
    ):
        await seed_discovery_fixtures(session)
    factory = async_sessionmaker(discovery_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(settings(), session_factory=factory)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        first = await client.get("/api/v1/events", params={"limit": 2})
        second = await client.get(
            "/api/v1/events", params={"limit": 2, "cursor": first.json()["next_cursor"]}
        )
        turkey_free = await client.get("/api/v1/events", params={"country": "tr", "price": "free"})
        search = await client.get("/api/v1/search", params={"search": "weekend run"})
        private = await client.get("/api/v1/events/018f0000-0000-7000-8000-000000000293")
    assert (
        first.status_code
        == second.status_code
        == turkey_free.status_code
        == search.status_code
        == 200
    )
    assert [item["id"] for item in first.json()["items"] + second.json()["items"]] == [
        str(value) for value in PUBLIC_EVENT_IDS
    ]
    assert [item["title"] for item in turkey_free.json()["items"]] == ["Istanbul Weekend Run"]
    assert search.json()["items"][0]["title"] == "Istanbul Weekend Run"
    assert private.status_code == 404
    rendered = repr(first.json()).casefold()
    assert all(
        value not in rendered
        for value in (
            "exact_address",
            "latitude",
            "longitude",
            "owner_user_id",
            "fixture exact address",
        )
    )


async def test_save_routes_require_csrf_verification_and_are_idempotent_without_capacity_effect(
    discovery_engine: AsyncEngine,
) -> None:
    async with (
        async_sessionmaker(discovery_engine, class_=AsyncSession)() as session,
        session.begin(),
    ):
        await seed_discovery_fixtures(session)
    verified = await create_member(discovery_engine, verified=True, complete=True)
    restricted = await create_member(discovery_engine, verified=False, complete=True)
    factory = async_sessionmaker(discovery_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(settings(), session_factory=factory)
    path = f"/api/v1/events/{PUBLIC_EVENT_IDS[0]}/saved"
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            no_csrf = await client.put(path, headers={"cookie": verified.cookie})
            denied = await client.put(
                path, headers={"cookie": restricted.cookie, "X-CSRF-Token": restricted.csrf}
            )
            first = await client.put(
                path, headers={"cookie": verified.cookie, "X-CSRF-Token": verified.csrf}
            )
            duplicate = await client.put(
                path, headers={"cookie": verified.cookie, "X-CSRF-Token": verified.csrf}
            )
            saved = await client.get("/api/v1/me/saved-events", headers={"cookie": verified.cookie})
            assert saved.headers["Cache-Control"] == "private, no-store"
            assert "Cookie" in saved.headers["Vary"]
            deleted = await client.delete(
                path, headers={"cookie": verified.cookie, "X-CSRF-Token": verified.csrf}
            )
            duplicate_delete = await client.delete(
                path, headers={"cookie": verified.cookie, "X-CSRF-Token": verified.csrf}
            )
        assert no_csrf.status_code == 403
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "email_verification_required"
        assert (
            first.status_code
            == duplicate.status_code
            == deleted.status_code
            == duplicate_delete.status_code
            == 204
        )
        assert [item["id"] for item in saved.json()["items"]] == [str(PUBLIC_EVENT_IDS[0])]
        async with discovery_engine.connect() as connection:
            registrations = await connection.scalar(
                text("SELECT count(*) FROM talaqi.registrations WHERE event_id=:id"),
                {"id": PUBLIC_EVENT_IDS[0]},
            )
        assert registrations == 0
    finally:
        await cleanup(discovery_engine, verified, restricted)


async def test_club_and_combined_search_routes_have_stable_non_starving_pagination(
    discovery_engine: AsyncEngine,
) -> None:
    async with (
        async_sessionmaker(discovery_engine, class_=AsyncSession)() as session,
        session.begin(),
    ):
        await seed_discovery_fixtures(session)
    factory = async_sessionmaker(discovery_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(settings(), session_factory=factory)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        clubs_one = await client.get("/api/v1/clubs", params={"limit": 1})
        clubs_two = await client.get(
            "/api/v1/clubs",
            params={"limit": 1, "cursor": clubs_one.json()["next_cursor"]},
        )
        kinds: list[str] = []
        cursor = None
        search_cache = ""
        for _ in range(5):
            params = {"search": "istanbul", "limit": 1}
            if cursor is not None:
                params["cursor"] = cursor
            response = await client.get("/api/v1/search", params=params)
            assert response.status_code == 200
            search_cache = response.headers["Cache-Control"]
            kinds.extend(item["kind"] for item in response.json()["items"])
            cursor = response.json()["next_cursor"]
            if cursor is None:
                break

    assert clubs_one.headers["Cache-Control"].startswith("public")
    assert search_cache.startswith("public")
    assert clubs_one.json()["next_cursor"] is not None
    assert clubs_one.json()["items"][0]["id"] != clubs_two.json()["items"][0]["id"]
    assert set(kinds) == {"event", "club"}


async def test_public_events_resolve_optional_caller_state_without_public_caching(
    discovery_engine: AsyncEngine,
) -> None:
    async with (
        async_sessionmaker(discovery_engine, class_=AsyncSession)() as session,
        session.begin(),
    ):
        await seed_discovery_fixtures(session)
    member = await create_member(discovery_engine, verified=True, complete=True)
    factory = async_sessionmaker(discovery_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(settings(), session_factory=factory)
    event_id = PUBLIC_EVENT_IDS[0]
    try:
        async with discovery_engine.begin() as connection:
            await connection.execute(
                text(
                    """INSERT INTO talaqi.saved_events (user_id,event_id) VALUES (:user,:event)
                       ON CONFLICT DO NOTHING"""
                ),
                {"user": member.id, "event": event_id},
            )
            await connection.execute(
                text(
                    """INSERT INTO talaqi.registrations (
                           id,event_id,user_id,method,state,seat_held,confirmed_at
                       ) VALUES (uuidv7(),:event,:user,'free','confirmed',true,clock_timestamp())"""
                ),
                {"user": member.id, "event": event_id},
            )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            anonymous = await client.get(f"/api/v1/events/{event_id}")
            caller = await client.get(
                f"/api/v1/events/{event_id}", headers={"cookie": member.cookie}
            )

        assert anonymous.headers["Cache-Control"].startswith("public")
        assert "Cookie" in anonymous.headers["Vary"]
        assert anonymous.json()["is_saved"] is False
        assert anonymous.json()["registration_state"] is None
        assert caller.json()["is_saved"] is True
        assert caller.json()["registration_state"] == "confirmed"
        assert caller.json()["organizer_display_name"] == "Istanbul Community Club"
        assert caller.headers["Cache-Control"] == "private, no-store"
        assert "Cookie" in caller.headers["Vary"]
    finally:
        async with discovery_engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM talaqi.registrations WHERE user_id=:user"),
                {"user": member.id},
            )
        await cleanup(discovery_engine, member)


async def test_save_and_unsave_hide_event_after_owning_club_suspension(
    discovery_engine: AsyncEngine,
) -> None:
    async with (
        async_sessionmaker(discovery_engine, class_=AsyncSession)() as session,
        session.begin(),
    ):
        await seed_discovery_fixtures(session)
    member = await create_member(discovery_engine, verified=True, complete=True)
    factory = async_sessionmaker(discovery_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(settings(), session_factory=factory)
    path = f"/api/v1/events/{PUBLIC_EVENT_IDS[0]}/saved"
    headers = {"cookie": member.cookie, "X-CSRF-Token": member.csrf}
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            assert (await client.put(path, headers=headers)).status_code == 204
            async with discovery_engine.begin() as connection:
                await connection.execute(
                    text(
                        """UPDATE talaqi.clubs
                           SET status='suspended',suspended_at=clock_timestamp(),
                               suspension_reason='test suspension'
                           WHERE id=:id"""
                    ),
                    {"id": PUBLIC_CLUB_IDS[0]},
                )
            save = await client.put(path, headers=headers)
            unsave = await client.delete(path, headers=headers)

        assert save.status_code == 404
        assert unsave.status_code == 404
        assert save.json()["error"]["code"] == "not_found"
        assert unsave.json()["error"]["code"] == "not_found"
    finally:
        await cleanup(discovery_engine, member)
        async with (
            async_sessionmaker(discovery_engine, class_=AsyncSession)() as session,
            session.begin(),
        ):
            await seed_discovery_fixtures(session)
