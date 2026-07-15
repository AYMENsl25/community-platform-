from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.db.identifiers import generate_uuid7
from talaqi.identity.repository import IdentityRepository

_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$Lpm/Lp7Pi4/BGiV5tCGoQg$"
    "yBSqOu3Mu/QL0TgL8EngAUcK6oI8W0ln7GNcBBaYHnE"  # pragma: allowlist secret
)


@pytest.mark.asyncio
async def test_failed_login_window_resets_at_expiry_then_locks_on_fifth_attempt(
    identity_engine: AsyncEngine,
) -> None:
    user_id = generate_uuid7()
    now = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session, session.begin():
        await session.execute(
            text(
                """
                INSERT INTO talaqi.users (
                    id, email, password_hash, terms_version, privacy_version, age_attested_at,
                    failed_login_count, locked_until
                ) VALUES (:id, :email, :hash, '2026-07-11', '2026-07-11', :now, 5, :now)
                """
            ),
            {"id": user_id, "email": f"lock-{user_id}@example.com", "hash": _HASH, "now": now},
        )
        repository = IdentityRepository(session)
        states = [await repository.record_failed_login(user_id, now)]
        states.extend([await repository.record_failed_login(user_id, now) for _ in range(4)])

    assert [state.failed_login_count for state in states] == [1, 2, 3, 4, 5]
    assert [state.locked_until for state in states[:4]] == [None, None, None, None]
    assert states[4].locked_until == now + timedelta(seconds=900)


@pytest.mark.asyncio
async def test_failed_login_expiry_boundary_is_exact_to_one_microsecond(
    identity_engine: AsyncEngine,
) -> None:
    user_id = generate_uuid7()
    now = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session, session.begin():
        await session.execute(
            text(
                """
                INSERT INTO talaqi.users (
                    id, email, password_hash, terms_version, privacy_version, age_attested_at,
                    failed_login_count, locked_until
                ) VALUES (:id, :email, :hash, '2026-07-11', '2026-07-11', :now, 5, :locked)
                """
            ),
            {
                "id": user_id,
                "email": f"boundary-{user_id}@example.com",
                "hash": _HASH,
                "now": now,
                "locked": now - timedelta(microseconds=1),
            },
        )
        state = await IdentityRepository(session).record_failed_login(user_id, now)
    assert state == type(state)(failed_login_count=1, locked_until=None)
