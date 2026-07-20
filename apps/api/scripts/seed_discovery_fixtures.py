from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "apps" / "api" / "src"
sys.path.insert(0, str(SOURCE))

from talaqi.db.engine import build_async_engine, build_session_factory  # noqa: E402
from talaqi.discovery.fixtures import (  # noqa: E402
    seed_discovery_fixtures,
    validate_fixture_target,
)


async def _seed(environment: str, database_url: str) -> None:
    validate_fixture_target(environment, database_url)
    engine = build_async_engine(database_url)
    try:
        session_factory = build_session_factory(engine)
        async with session_factory.begin() as session:
            await seed_discovery_fixtures(session)
    finally:
        await engine.dispose()


def main() -> int:
    environment = os.environ.get("ENVIRONMENT", "")
    variable = "TEST_DATABASE_URL" if environment == "test" else "DATABASE_URL"
    database_url = os.environ.get(variable, "")
    try:
        asyncio.run(_seed(environment, database_url))
    except ValueError as error:
        raise SystemExit(f"{error}\n") from None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
