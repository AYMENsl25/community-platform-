from __future__ import annotations

import runpy
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Protocol, cast

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

ROOT = Path(__file__).resolve().parents[4]


class DriverConnection(Protocol):
    def execute(self, query: str) -> Awaitable[str]: ...


@pytest.mark.asyncio
async def test_regional_seed_replay_is_deterministic(region_session: AsyncSession) -> None:
    revision_path = ROOT / "database/migrations/versions/0002_regional_catalog.py"
    namespace = runpy.run_path(str(revision_path))
    seed_sql = cast(Callable[[], str], namespace["_seed_sql"])

    raw_connection = await region_session.connection()
    proxied = await raw_connection.get_raw_connection()
    driver_connection = cast(DriverConnection, proxied.driver_connection)
    await driver_connection.execute(seed_sql())
    await driver_connection.execute(seed_sql())

    counts = (
        await region_session.execute(
            text(
                """
                SELECT
                    (SELECT count(*) FROM talaqi.countries WHERE code IN ('TR', 'DZ')),
                    (SELECT count(*) FROM talaqi.cities WHERE slug IN ('istanbul', 'algiers')),
                        (SELECT count(*) FROM talaqi.categories WHERE slug IN (
                            'sports', 'arts-culture', 'technology',
                            'language-exchange', 'outdoors', 'games'
                        )),
                    (SELECT count(*) FROM talaqi.regional_policies)
                """
            )
        )
    ).one()
    assert tuple(counts) == (2, 2, 6, 2)
