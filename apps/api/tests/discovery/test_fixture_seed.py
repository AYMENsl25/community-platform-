from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from talaqi.discovery.fixtures import (
    PUBLIC_CLUB_IDS,
    PUBLIC_EVENT_IDS,
    seed_discovery_fixtures,
    validate_fixture_target,
)

pytest_plugins = ("apps.api.tests.db.conftest",)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_fixture_target_rejects_deployed_environments(environment: str) -> None:
    with pytest.raises(ValueError, match="local development or test database"):
        validate_fixture_target(
            environment,
            "postgresql://u:p@127.0.0.1/x",  # pragma: allowlist secret
        )


@pytest.mark.parametrize(
    ("environment", "database_url"),
    [
        (
            "test",
            "postgresql+asyncpg://u:p@database.example/x",  # pragma: allowlist secret
        ),
        (
            "test",
            "postgresql+asyncpg://u:p@127.0.0.1/talaqi",  # pragma: allowlist secret
        ),
        (
            "development",
            "postgresql+asyncpg://u:p@127.0.0.1/talaqi",  # pragma: allowlist secret
        ),
        (
            "development",
            "postgresql://u:p@127.0.0.1/x",  # pragma: allowlist secret
        ),
    ],
)
def test_fixture_target_rejects_unsafe_database_urls(environment: str, database_url: str) -> None:
    with pytest.raises(ValueError, match="local development or test database") as error:
        validate_fixture_target(environment, database_url)

    assert database_url not in str(error.value)
    assert "password" not in str(error.value)


@pytest.mark.parametrize(
    ("environment", "database_url"),
    [
        (
            "test",
            "postgresql+asyncpg://u:p@127.0.0.1:5432/talaqi_test",  # pragma: allowlist secret
        ),
        (
            "development",
            "postgresql+asyncpg://u:p@localhost:5432/talaqi",  # pragma: allowlist secret
        ),
    ],
)
def test_fixture_target_accepts_explicit_local_targets(environment: str, database_url: str) -> None:
    target = validate_fixture_target(environment, database_url)

    assert target.host in {"127.0.0.1", "localhost"}
    assert target.port == 5432


@pytest.mark.asyncio
async def test_discovery_fixture_replay_is_deterministic_and_has_negative_rows(
    db_session: AsyncSession,
) -> None:
    await seed_discovery_fixtures(db_session)
    await seed_discovery_fixtures(db_session)
    await db_session.flush()

    counts = (
        await db_session.execute(
            text(
                """
                SELECT
                  (SELECT count(*) FROM talaqi.users
                   WHERE email = 'discovery-fixture-owner@invalid.example'),
                  (SELECT count(*) FROM talaqi.clubs
                   WHERE id = ANY(CAST(:club_ids AS uuid[]))),
                  (SELECT count(*) FROM talaqi.events
                   WHERE id = ANY(CAST(:event_ids AS uuid[]))),
                  (SELECT count(*) FROM talaqi.clubs
                   WHERE slug LIKE 'fixture-%' AND status = 'draft'),
                  (SELECT count(*) FROM talaqi.clubs
                   WHERE slug LIKE 'fixture-%' AND status = 'suspended'),
                  (SELECT count(*) FROM talaqi.events
                   WHERE title LIKE 'Fixture %' AND status = 'draft'),
                  (SELECT count(*) FROM talaqi.events
                   WHERE title LIKE 'Fixture %' AND status = 'suspended'),
                  (SELECT count(*) FROM talaqi.events
                   WHERE title LIKE 'Fixture %' AND visibility = 'private_link')
                """
            ),
            {
                "club_ids": [str(value) for value in PUBLIC_CLUB_IDS],
                "event_ids": [str(value) for value in PUBLIC_EVENT_IDS],
            },
        )
    ).one()

    assert tuple(counts) == (1, 2, 4, 1, 1, 1, 1, 1)
    assert all(value.version == 7 for value in (*PUBLIC_CLUB_IDS, *PUBLIC_EVENT_IDS))

    rows = (
        await db_session.execute(
            text(
                """
                SELECT c.code, city.slug, e.registration_method::text, count(*)
                FROM talaqi.events AS e
                JOIN talaqi.countries AS c ON c.id = e.country_id
                JOIN talaqi.cities AS city ON city.id = e.city_id
                WHERE e.id = ANY(CAST(:event_ids AS uuid[]))
                GROUP BY c.code, city.slug, e.registration_method
                ORDER BY c.code, city.slug, e.registration_method::text
                """
            ),
            {"event_ids": [str(value) for value in PUBLIC_EVENT_IDS]},
        )
    ).all()
    logical_rows = [tuple(row) for row in rows]
    assert cast(list[tuple[str, str, str, int]], logical_rows) == [
        ("DZ", "algiers", "cash_organizer_confirmed", 1),
        ("DZ", "algiers", "free", 1),
        ("TR", "istanbul", "cash_organizer_confirmed", 1),
        ("TR", "istanbul", "free", 1),
    ]

    owner_hash = (
        await db_session.execute(
            text(
                """
                SELECT password_hash FROM talaqi.users
                WHERE email = 'discovery-fixture-owner@invalid.example'
                """
            )
        )
    ).scalar_one()
    assert owner_hash.startswith("$argon2id$")
