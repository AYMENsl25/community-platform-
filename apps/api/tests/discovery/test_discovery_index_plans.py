from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from talaqi.discovery.fixtures import seed_discovery_fixtures

pytest_plugins = ("apps.api.tests.db.conftest",)


async def _plan(session: AsyncSession, query: str) -> str:
    await session.execute(text("SET LOCAL enable_seqscan = off"))
    rows = (await session.execute(text(f"EXPLAIN (COSTS OFF) {query}"))).scalars()
    return "\n".join(rows)


@pytest.mark.asyncio
async def test_repository_event_ordering_uses_partial_discovery_indexes(
    db_session: AsyncSession,
) -> None:
    await seed_discovery_fixtures(db_session)

    upcoming = await _plan(
        db_session,
        """
        SELECT event.id,
               CASE WHEN event.ownership_type = 'club' THEN 10 ELSE 0 END AS featured_score
        FROM talaqi.events AS event
        WHERE event.status = 'published' AND event.visibility = 'public'
          AND event.suspended_at IS NULL
        ORDER BY featured_score DESC, event.start_at, event.id LIMIT 20
        """,
    )
    by_price = await _plan(
        db_session,
        """
        SELECT event.id,
               CASE WHEN event.ownership_type = 'club' THEN 10 ELSE 0 END AS featured_score
        FROM talaqi.events AS event
        WHERE event.status = 'published' AND event.visibility = 'public'
          AND event.suspended_at IS NULL AND event.registration_method = 'free'
        ORDER BY featured_score DESC, event.start_at, event.id LIMIT 20
        """,
    )

    assert "ix_events_public_featured" in upcoming
    assert "ix_events_public_featured" in by_price


@pytest.mark.asyncio
async def test_repository_club_ordering_uses_partial_name_index(
    db_session: AsyncSession,
) -> None:
    await seed_discovery_fixtures(db_session)
    # The fixture set is intentionally tiny, so PostgreSQL can otherwise prefer
    # scanning an unrelated index and sorting its handful of rows. Disabling an
    # explicit sort makes this a deterministic check that the production
    # ordering is satisfiable by the purpose-built partial expression index.
    await db_session.execute(text("SET LOCAL enable_sort = off"))

    plan = await _plan(
        db_session,
        """
        SELECT club.id FROM talaqi.clubs AS club
        WHERE club.status = 'published' AND club.suspended_at IS NULL
        ORDER BY lower(club.name), club.id LIMIT 20
        """,
    )

    assert "ix_clubs_public_name" in plan
    assert "Sort" not in plan
