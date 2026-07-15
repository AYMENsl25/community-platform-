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


@pytest.mark.asyncio
async def test_last_used_touch_cannot_cross_users_or_touch_revoked_or_expired_rows(
    identity_engine: AsyncEngine,
) -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    owner_id = generate_uuid7()
    other_user_id = generate_uuid7()
    cross_user_id = generate_uuid7()
    revoked_id = generate_uuid7()
    expired_id = generate_uuid7()
    factory = async_sessionmaker(identity_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session, session.begin():
        await session.execute(
            text(
                """
                INSERT INTO talaqi.users (
                    id,email,password_hash,terms_version,privacy_version,age_attested_at
                ) VALUES
                    (:owner,:owner_email,:hash,'2026-07-11','2026-07-11',:now),
                    (:other,:other_email,:hash,'2026-07-11','2026-07-11',:now)
                """
            ),
            {
                "owner": owner_id,
                "owner_email": f"last-used-owner-{owner_id}@example.com",
                "other": other_user_id,
                "other_email": f"last-used-other-{other_user_id}@example.com",
                "hash": _HASH,
                "now": now,
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO talaqi.sessions (
                    id,user_id,family_id,refresh_token_hash,csrf_secret_hash,expires_at,
                    revoked_at,revoke_reason
                ) VALUES
                    (:cross,:other,:cross_family,:cross_refresh,:csrf,:future,NULL,NULL),
                    (:revoked,:owner,:revoked_family,:revoked_refresh,:csrf,:future,:now,'test'),
                    (:expired,:owner,:expired_family,:expired_refresh,:csrf,:past,NULL,NULL)
                """
            ),
            {
                "cross": cross_user_id,
                "other": other_user_id,
                "cross_family": generate_uuid7(),
                "cross_refresh": cross_user_id.bytes * 2,
                "revoked": revoked_id,
                "owner": owner_id,
                "revoked_family": generate_uuid7(),
                "revoked_refresh": revoked_id.bytes * 2,
                "expired": expired_id,
                "expired_family": generate_uuid7(),
                "expired_refresh": expired_id.bytes * 2,
                "csrf": b"s" * 32,
                "future": now + timedelta(days=1),
                "past": now - timedelta(seconds=1),
                "now": now,
            },
        )
        repository = IdentityRepository(session)
        await repository.touch_session(cross_user_id, owner_id, now)
        await repository.touch_session(revoked_id, owner_id, now)
        await repository.touch_session(expired_id, owner_id, now)
        last_used = (
            (
                await session.execute(
                    text(
                        """SELECT id,last_used_at FROM talaqi.sessions
                        WHERE id IN (:cross,:revoked,:expired)"""
                    ),
                    {"cross": cross_user_id, "revoked": revoked_id, "expired": expired_id},
                )
            )
            .mappings()
            .all()
        )

    assert {row["id"]: row["last_used_at"] for row in last_used} == {
        cross_user_id: None,
        revoked_id: None,
        expired_id: None,
    }
