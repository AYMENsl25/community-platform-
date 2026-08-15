from __future__ import annotations

import asyncio
import os
import runpy
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import SecretStr
from sqlalchemy import text
from talaqi.db.engine import build_async_engine

ROOT = Path(__file__).resolve().parents[4]
REQUIRED_TABLES = {
    "schema_revisions",
    "users",
    "profiles",
    "sessions",
    "auth_tokens",
    "countries",
    "cities",
    "categories",
    "regional_policies",
    "media_assets",
    "clubs",
    "club_memberships",
    "club_join_requests",
    "events",
    "event_invite_tokens",
    "saved_events",
    "registrations",
    "registration_transitions",
    "announcements",
    "announcement_recipients",
    "event_updates",
    "event_update_recipients",
    "notifications",
    "notification_deliveries",
    "email_delivery_intents",
    "email_quota_reservations",
    "outbox_events",
    "moderation_cases",
    "moderation_case_events",
    "audit_events",
    "idempotency_keys",
    "platform_settings",
    "user_mfa_factors",
}


def test_alembic_has_exactly_one_head() -> None:
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))

    assert scripts.get_heads() == ["0013_feature_flags"]
    assert scripts.get_revision("0013_feature_flags").down_revision == "0012_communications"
    assert scripts.get_revision("0012_communications").down_revision == "0011_email_intents"
    assert scripts.get_revision("0011_email_intents").down_revision == "0010_notifications"
    assert scripts.get_revision("0009_registration_state_machine").down_revision == (
        "0008_event_publishing"
    )
    assert scripts.get_revision("0008_event_publishing").down_revision == (
        "0007_moderation_priority"
    )
    assert scripts.get_revision("0007_moderation_priority").down_revision == (
        "0006_discovery_indexes"
    )
    assert scripts.get_revision("0006_discovery_indexes").down_revision == (
        "0005_profiles_eligibility"
    )
    assert scripts.get_revision("0005_profiles_eligibility").down_revision == (
        "0004_verification_sessions"
    )
    assert scripts.get_revision("0004_verification_sessions").down_revision == (
        "0003_identity_authentication"
    )
    assert scripts.get_revision("0003_identity_authentication").down_revision == (
        "0002_regional_catalog"
    )
    assert scripts.get_revision("0002_regional_catalog").down_revision == (
        "0001_closed_beta_baseline"
    )


def test_baseline_checksum_is_stable_across_platform_line_endings() -> None:
    revision_path = ROOT / "database" / "migrations" / "versions" / "0001_closed_beta_baseline.py"
    namespace = runpy.run_path(str(revision_path))
    canonical_payload = cast(Callable[[bytes], bytes], namespace["_canonical_payload"])
    lf_payload = b"first\nsecond\n"
    crlf_payload = b"first\r\nsecond\r\n"

    assert canonical_payload(lf_payload) == canonical_payload(crlf_payload)


def test_alembic_rejects_non_test_target_without_exposing_the_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    password = "supplied-non-test-password"
    unsafe_url = f"postgresql+asyncpg://talaqi:{password}@127.0.0.1:5432/TALAQI"
    monkeypatch.setenv("TEST_DATABASE_URL", unsafe_url)

    with pytest.raises(ValueError, match="explicit local test database") as error:
        command.current(Config(str(ROOT / "alembic.ini")))

    diagnostic = f"{error.value!s} {error.value!r}"
    assert password not in diagnostic
    assert unsafe_url not in diagnostic
    assert os.environ["TEST_DATABASE_URL"] == unsafe_url


def test_offline_upgrade_emits_baseline_without_connection_details(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    password = "supplied-offline-password"
    offline_url = f"postgresql+asyncpg://test_user:{password}@127.0.0.1:5433/offline_test"
    monkeypatch.setenv("TEST_DATABASE_URL", offline_url)

    command.upgrade(Config(str(ROOT / "alembic.ini")), "head", sql=True)

    captured = capsys.readouterr()
    output = f"{captured.out}\n{captured.err}"
    assert "CREATE SCHEMA talaqi" in output
    assert "CREATE FUNCTION set_updated_at" in output
    assert password not in output
    assert offline_url not in output


async def _reset_safe_test_schema(database_url: SecretStr) -> None:
    engine = build_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA IF EXISTS talaqi CASCADE"))
            await connection.execute(text("DROP TABLE IF EXISTS public.alembic_version"))
    finally:
        await engine.dispose()


async def _schema_state(database_url: SecretStr) -> tuple[set[str], str | None]:
    engine = build_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            table_names = set(
                (
                    await connection.execute(
                        text("SELECT tablename FROM pg_tables WHERE schemaname = 'talaqi'")
                    )
                ).scalars()
            )
            revision = (
                await connection.execute(text("SELECT version_num FROM public.alembic_version"))
            ).scalar_one_or_none()
            return table_names, revision
    finally:
        await engine.dispose()


async def _base_state(database_url: SecretStr) -> tuple[bool, int]:
    engine = build_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            schema_exists = (
                await connection.execute(text("SELECT to_regnamespace('talaqi') IS NOT NULL"))
            ).scalar_one()
            revision_count = (
                await connection.execute(text("SELECT count(*) FROM public.alembic_version"))
            ).scalar_one()
            return schema_exists, revision_count
    finally:
        await engine.dispose()


async def _legacy_email_intent(database_url: SecretStr, *, seed: bool) -> tuple[str, str] | None:
    engine = build_async_engine(database_url)
    try:
        if not seed:
            async with engine.connect() as connection:
                row = (
                    await connection.execute(
                        text(
                            "SELECT auth_token_id::text, locale_hint "
                            "FROM talaqi.email_delivery_intents"
                        )
                    )
                ).one_or_none()
                return None if row is None else (str(row[0]), str(row[1]))
        async with engine.begin() as connection:
            user_id = await connection.scalar(
                text(
                    """
                    INSERT INTO talaqi.users (
                        email, password_hash, terms_version, privacy_version, age_attested_at
                    ) VALUES (
                        'legacy-email@example.test', '$argon2id$test',
                        '2026-07-11', '2026-07-11', clock_timestamp()
                    ) RETURNING id
                    """
                )
            )
            token_id = await connection.scalar(text("SELECT uuidv7()"))
            outbox_id = await connection.scalar(
                text(
                    """
                    INSERT INTO talaqi.outbox_events (
                        aggregate_type, aggregate_id, event_type, payload,
                        deduplication_key, status, processed_at
                    ) VALUES (
                        'user', :user_id, 'identity.email_verification_requested',
                        jsonb_build_object(
                            'user_id', CAST(:user_text AS text),
                            'auth_token_id', CAST(:token_text AS text),
                            'locale_hint', 'fr'
                        ), 'legacy-email-intent', 'delivered', clock_timestamp()
                    ) RETURNING id
                    """
                ),
                {
                    "user_id": user_id,
                    "user_text": str(user_id),
                    "token_text": str(token_id),
                },
            )
            notification_id = await connection.scalar(
                text(
                    """
                    INSERT INTO talaqi.notifications (
                        recipient_user_id, type_key, title_key, body_key, outbox_event_id
                    ) VALUES (
                        :user_id, 'identity.email_verification_requested',
                        'notifications.security.title',
                        'notifications.identity.email_verification_requested.body',
                        :outbox_id
                    ) RETURNING id
                    """
                ),
                {"user_id": user_id, "outbox_id": outbox_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO talaqi.notification_deliveries (notification_id, channel) "
                    "VALUES (:notification_id, 'email')"
                ),
                {"notification_id": notification_id},
            )
            return str(token_id), "fr"
    finally:
        await engine.dispose()


async def _legacy_communications(database_url: SecretStr, *, seed: bool) -> tuple[int, int]:
    engine = build_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            if not seed:
                announcements = await connection.scalar(
                    text("SELECT count(*) FROM talaqi.announcement_recipients")
                )
                updates = await connection.scalar(
                    text("SELECT count(*) FROM talaqi.event_update_recipients")
                )
                return int(announcements or 0), int(updates or 0)
            owner_id = await connection.scalar(
                text(
                    "INSERT INTO talaqi.users (email, password_hash, terms_version, "
                    "privacy_version, age_attested_at) VALUES "
                    "('legacy-owner@example.test', '$argon2id$test', '2026-07-11', "
                    "'2026-07-11', clock_timestamp()) RETURNING id"
                )
            )
            member_id = await connection.scalar(
                text(
                    "INSERT INTO talaqi.users (email, password_hash, terms_version, "
                    "privacy_version, age_attested_at) VALUES "
                    "('legacy-member@example.test', '$argon2id$test', '2026-07-11', "
                    "'2026-07-11', clock_timestamp()) RETURNING id"
                )
            )
            club_id = await connection.scalar(
                text(
                    "INSERT INTO talaqi.clubs (owner_user_id, slug, name) "
                    "VALUES (:owner_id, 'legacy-club', 'Legacy club') RETURNING id"
                ),
                {"owner_id": owner_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO talaqi.club_memberships (club_id, user_id, role) "
                    "VALUES (:club_id, :member_id, 'member')"
                ),
                {"club_id": club_id, "member_id": member_id},
            )
            event_id = await connection.scalar(
                text(
                    "INSERT INTO talaqi.events (ownership_type, owner_user_id, title) "
                    "VALUES ('independent', :owner_id, 'Legacy event') RETURNING id"
                ),
                {"owner_id": owner_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO talaqi.registrations (event_id, user_id, method, state, "
                    "seat_held, confirmed_at) VALUES "
                    "(:event_id, :member_id, 'free', 'confirmed', true, clock_timestamp())"
                ),
                {"event_id": event_id, "member_id": member_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO talaqi.announcements "
                    "(club_id, author_user_id, title, body) VALUES "
                    "(:club_id, :owner_id, 'Legacy announcement', 'Retained')"
                ),
                {"club_id": club_id, "owner_id": owner_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO talaqi.event_updates "
                    "(event_id, author_user_id, title, body) VALUES "
                    "(:event_id, :owner_id, 'Legacy update', 'Retained')"
                ),
                {"event_id": event_id, "owner_id": owner_id},
            )
            return 0, 0
    finally:
        await engine.dispose()


async def _server_uuid_version(database_url: SecretStr) -> int | None:
    engine = build_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            identifier = (await connection.execute(text("SELECT uuidv7()"))).scalar_one()
            return identifier.version
    finally:
        await engine.dispose()


async def _regional_seed_counts(database_url: SecretStr) -> tuple[int, int, int, int, int]:
    engine = build_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        """
                        SELECT
                            (SELECT count(*) FROM talaqi.countries
                             WHERE code IN ('TR', 'DZ')),
                            (SELECT count(*) FROM talaqi.cities
                             WHERE slug IN ('istanbul', 'algiers')),
                            (SELECT count(*) FROM talaqi.categories WHERE slug IN (
                                'sports', 'arts-culture', 'technology',
                                'language-exchange', 'outdoors', 'games'
                            )),
                            (SELECT count(*) FROM talaqi.regional_policies),
                            (SELECT count(*) FROM talaqi.schema_revisions
                             WHERE revision = '2026-07-14-regional-catalog')
                        """
                    )
                )
            ).one()
            return cast(tuple[int, int, int, int, int], tuple(row))
    finally:
        await engine.dispose()


async def _recovery_session_migration_state(database_url: SecretStr) -> tuple[bool, bool, int]:
    engine = build_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        """SELECT
                        to_regclass('talaqi.ix_auth_tokens_active_kind') IS NOT NULL,
                        to_regclass('talaqi.ix_sessions_active_family') IS NOT NULL,
                        (SELECT count(*) FROM talaqi.schema_revisions
                         WHERE revision='2026-07-15-verification-rotating-sessions')"""
                    )
                )
            ).one()
            return cast(tuple[bool, bool, int], tuple(row))
    finally:
        await engine.dispose()


async def _profiles_eligibility_migration_state(
    database_url: SecretStr,
) -> tuple[bool, bool, int]:
    engine = build_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        """SELECT
                        to_regclass('talaqi.ix_clubs_active_owner_eligibility') IS NOT NULL,
                        to_regclass(
                            'talaqi.ix_events_active_independent_owner_eligibility'
                        ) IS NOT NULL,
                        (SELECT count(*) FROM talaqi.schema_revisions
                         WHERE revision='2026-07-16-profiles-eligibility')"""
                    )
                )
            ).one()
            return cast(tuple[bool, bool, int], tuple(row))
    finally:
        await engine.dispose()


async def _regional_catalog_state(
    database_url: SecretStr,
) -> dict[str, tuple[tuple[object, ...], ...]]:
    engine = build_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            countries = (
                await connection.execute(
                    text(
                        """
                        SELECT code, name_key, default_locale, default_currency, enabled
                        FROM talaqi.countries ORDER BY code
                        """
                    )
                )
            ).all()
            cities = (
                await connection.execute(
                    text(
                        """
                        SELECT c.code, city.slug, city.name_key, city.time_zone,
                               city.beta_enabled, city.enabled
                        FROM talaqi.cities AS city
                        JOIN talaqi.countries AS c ON c.id = city.country_id
                        ORDER BY c.code, city.slug
                        """
                    )
                )
            ).all()
            categories = (
                await connection.execute(
                    text(
                        """
                        SELECT slug, name_key, icon_key, sort_order, enabled
                        FROM talaqi.categories ORDER BY slug
                        """
                    )
                )
            ).all()
            policies = (
                await connection.execute(
                    text(
                        """
                        SELECT c.code,
                               p.allowed_registration_methods::text[],
                               p.cash_expiry_min_minutes,
                               p.cash_expiry_default_minutes,
                               p.cash_expiry_max_minutes,
                               p.cancellation_min_minutes,
                               p.cancellation_default_minutes,
                               p.cancellation_max_minutes,
                               p.default_club_ownership_limit,
                               p.default_active_independent_event_limit,
                               p.exact_venue_public_by_default,
                               p.revision
                        FROM talaqi.regional_policies AS p
                        JOIN talaqi.countries AS c ON c.id = p.country_id
                        ORDER BY c.code
                        """
                    )
                )
            ).all()
            return {
                "countries": tuple(tuple(row) for row in countries),
                "cities": tuple(tuple(row) for row in cities),
                "categories": tuple(tuple(row) for row in categories),
                "policies": tuple((row[0], tuple(row[1]), *row[2:]) for row in policies),
            }
    finally:
        await engine.dispose()


BASELINE_CATALOG = {
    "countries": (
        ("DZ", "countries.dz", "ar", "DZD", True),
        ("TR", "countries.tr", "tr", "TRY", True),
    ),
    "cities": (
        ("DZ", "algiers", "cities.algiers", "Africa/Algiers", True, True),
        ("TR", "istanbul", "cities.istanbul", "Europe/Istanbul", True, True),
    ),
    "categories": (
        ("culture", "categories.culture", "landmark", 40, True),
        ("education", "categories.education", "book", 30, True),
        ("outdoors", "categories.outdoors", "mountain", 20, True),
        ("social", "categories.social", "users", 50, True),
        ("sports", "categories.sports", "ball", 10, True),
        ("wellness", "categories.wellness", "heart", 60, True),
    ),
    "policies": (
        (
            "DZ",
            ("free", "cash_organizer_confirmed"),
            120,
            2880,
            10080,
            0,
            1440,
            10080,
            1,
            3,
            False,
            1,
        ),
        (
            "TR",
            ("free", "cash_organizer_confirmed"),
            120,
            1440,
            4320,
            0,
            1440,
            10080,
            1,
            3,
            False,
            1,
        ),
    ),
}

APPROVED_CATALOG = {
    "countries": (
        ("DZ", "regions.country.dz", "fr", "DZD", True),
        ("TR", "regions.country.tr", "tr", "TRY", True),
    ),
    "cities": (
        ("DZ", "algiers", "regions.city.algiers", "Africa/Algiers", True, True),
        ("TR", "istanbul", "regions.city.istanbul", "Europe/Istanbul", True, True),
    ),
    "categories": (
        ("arts-culture", "categories.arts_culture", "arts-culture", 20, True),
        ("culture", "categories.culture", "landmark", 40, False),
        ("education", "categories.education", "book", 30, False),
        ("games", "categories.games", "games", 60, True),
        ("language-exchange", "categories.language_exchange", "language-exchange", 40, True),
        ("outdoors", "categories.outdoors", "outdoors", 50, True),
        ("social", "categories.social", "users", 50, False),
        ("sports", "categories.sports", "sports", 10, True),
        ("technology", "categories.technology", "technology", 30, True),
        ("wellness", "categories.wellness", "heart", 60, False),
    ),
    "policies": BASELINE_CATALOG["policies"],
}


def test_email_intent_migration_backfills_pending_0010_delivery(
    test_database_url: SecretStr,
) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    asyncio.run(_reset_safe_test_schema(test_database_url))
    command.upgrade(config, "0010_notifications")
    expected = asyncio.run(_legacy_email_intent(test_database_url, seed=True))
    command.upgrade(config, "head")
    assert asyncio.run(_legacy_email_intent(test_database_url, seed=False)) == expected


def test_communications_migration_backfills_legacy_recipient_history(
    test_database_url: SecretStr,
) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    asyncio.run(_reset_safe_test_schema(test_database_url))
    command.upgrade(config, "0011_email_intents")
    asyncio.run(_legacy_communications(test_database_url, seed=True))
    command.upgrade(config, "head")
    assert asyncio.run(_legacy_communications(test_database_url, seed=False)) == (1, 1)


def test_clean_upgrade_downgrade_and_reupgrade_against_postgresql_18(
    test_database_url: SecretStr,
) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    expected_head = ScriptDirectory.from_config(config).get_current_head()
    assert expected_head is not None
    asyncio.run(_reset_safe_test_schema(test_database_url))

    command.upgrade(config, "0001_closed_beta_baseline")
    assert asyncio.run(_regional_catalog_state(test_database_url)) == BASELINE_CATALOG
    assert asyncio.run(_regional_seed_counts(test_database_url)) == (2, 2, 2, 2, 0)

    command.upgrade(config, "head")
    table_names, revision = asyncio.run(_schema_state(test_database_url))
    assert table_names == REQUIRED_TABLES
    assert revision == expected_head
    assert asyncio.run(_regional_seed_counts(test_database_url)) == (2, 2, 6, 2, 1)
    assert asyncio.run(_regional_catalog_state(test_database_url)) == APPROVED_CATALOG
    assert asyncio.run(_server_uuid_version(test_database_url)) == 7
    assert asyncio.run(_recovery_session_migration_state(test_database_url)) == (True, True, 1)
    assert asyncio.run(_profiles_eligibility_migration_state(test_database_url)) == (
        True,
        True,
        1,
    )

    command.downgrade(config, "0004_verification_sessions")
    assert asyncio.run(_profiles_eligibility_migration_state(test_database_url)) == (
        False,
        False,
        0,
    )
    command.upgrade(config, "head")
    assert asyncio.run(_profiles_eligibility_migration_state(test_database_url)) == (
        True,
        True,
        1,
    )

    command.downgrade(config, "0003_identity_authentication")
    assert asyncio.run(_recovery_session_migration_state(test_database_url)) == (
        False,
        False,
        0,
    )
    command.upgrade(config, "head")
    assert asyncio.run(_recovery_session_migration_state(test_database_url)) == (True, True, 1)

    command.downgrade(config, "0001_closed_beta_baseline")
    table_names, revision = asyncio.run(_schema_state(test_database_url))
    assert table_names == REQUIRED_TABLES - {
        "email_delivery_intents",
        "email_quota_reservations",
        "announcement_recipients",
        "event_update_recipients",
    }
    assert revision == "0001_closed_beta_baseline"
    assert asyncio.run(_regional_seed_counts(test_database_url)) == (2, 2, 2, 2, 0)
    assert asyncio.run(_regional_catalog_state(test_database_url)) == BASELINE_CATALOG

    command.upgrade(config, "head")
    assert asyncio.run(_regional_seed_counts(test_database_url)) == (2, 2, 6, 2, 1)

    command.downgrade(config, "base")
    schema_exists, revision_count = asyncio.run(_base_state(test_database_url))
    assert schema_exists is False
    assert revision_count == 0

    command.upgrade(config, "head")
    table_names, revision = asyncio.run(_schema_state(test_database_url))
    assert table_names == REQUIRED_TABLES
    assert revision == expected_head
