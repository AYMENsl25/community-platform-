from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.identity.models import (
    LoginState,
    NewSession,
    NewUser,
    SessionRecord,
    UserRecord,
    UserStatus,
)


class IdentityRepositoryProtocol(Protocol):
    async def create_user(self, registration: NewUser) -> UserRecord: ...
    async def find_for_login(self, identifier: str) -> UserRecord | None: ...
    async def record_failed_login(self, user_id: UUID, now: datetime) -> LoginState: ...
    async def clear_failed_login(self, user_id: UUID) -> None: ...
    async def create_session(self, session: NewSession) -> SessionRecord: ...
    async def find_active_session(
        self, session_id: UUID, now: datetime
    ) -> tuple[SessionRecord, UserRecord] | None: ...
    async def revoke_session(self, session_id: UUID, reason: str, now: datetime) -> None: ...


def _user(row: object) -> UserRecord:
    mapping = cast(dict[str, object], row)
    return UserRecord(
        id=cast(UUID, mapping["id"]),
        email=cast(str, mapping["email"]),
        password_hash=cast(str, mapping["password_hash"]),
        status=cast(UserStatus, mapping["status"]),
        email_verified_at=cast(datetime | None, mapping["email_verified_at"]),
        failed_login_count=cast(int, mapping["failed_login_count"]),
        locked_until=cast(datetime | None, mapping["locked_until"]),
        is_platform_admin=cast(bool, mapping["is_platform_admin"]),
    )


_USER_COLUMNS = (
    "id, email, password_hash, status, email_verified_at, "
    "failed_login_count, locked_until, is_platform_admin"
)


class IdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_user(self, registration: NewUser) -> UserRecord:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                    INSERT INTO talaqi.users (
                        id, email, password_hash, terms_version, privacy_version, age_attested_at
                    ) VALUES (
                        :id, :email, :password_hash, :terms_version, :privacy_version,
                        :age_attested_at
                    )
                    ON CONFLICT (lower(email)) DO NOTHING
                    RETURNING id, email, password_hash, status, email_verified_at,
                              failed_login_count, locked_until, is_platform_admin
                    """
                    ),
                    {
                        "id": registration.id,
                        "email": registration.email,
                        "password_hash": registration.password_hash,
                        "terms_version": registration.terms_version,
                        "privacy_version": registration.privacy_version,
                        "age_attested_at": registration.age_attested_at,
                    },
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            row = (
                (
                    await self._session.execute(
                        text(
                            """
                            SELECT id, email, password_hash, status, email_verified_at,
                                   failed_login_count, locked_until, is_platform_admin
                            FROM talaqi.users WHERE lower(email) = :email
                            """
                        ),
                        {"email": registration.email},
                    )
                )
                .mappings()
                .one()
            )
        return _user(dict(row))

    async def find_for_login(self, identifier: str) -> UserRecord | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                    SELECT u.id, u.email, u.password_hash, u.status, u.email_verified_at,
                           u.failed_login_count, u.locked_until, u.is_platform_admin
                    FROM talaqi.users AS u
                    LEFT JOIN talaqi.profiles AS p ON p.user_id = u.id
                    WHERE lower(u.email) = :identifier OR lower(p.username) = :identifier
                    LIMIT 1
                    """
                    ),
                    {"identifier": identifier},
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else _user(dict(row))

    async def record_failed_login(self, user_id: UUID, now: datetime) -> LoginState:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                    UPDATE talaqi.users
                    SET failed_login_count = CASE
                            WHEN locked_until IS NOT NULL AND locked_until <= :now THEN 1
                            ELSE failed_login_count + 1
                        END,
                        locked_until = CASE
                            WHEN locked_until IS NOT NULL AND locked_until <= :now THEN NULL
                            WHEN failed_login_count + 1 >= 5 THEN :locked_until
                            ELSE locked_until
                        END
                    WHERE id = :user_id
                    RETURNING failed_login_count, locked_until
                    """
                    ),
                    {"user_id": user_id, "now": now, "locked_until": now + timedelta(minutes=15)},
                )
            )
            .mappings()
            .one()
        )
        return LoginState(row["failed_login_count"], row["locked_until"])

    async def clear_failed_login(self, user_id: UUID) -> None:
        await self._session.execute(
            text(
                """
                UPDATE talaqi.users SET failed_login_count = 0, locked_until = NULL
                WHERE id = :user_id
                """
            ),
            {"user_id": user_id},
        )

    async def create_session(self, session: NewSession) -> SessionRecord:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                    INSERT INTO talaqi.sessions (
                        id, user_id, family_id, refresh_token_hash, csrf_secret_hash, expires_at
                    ) VALUES (
                        :id, :user_id, :family_id, :refresh_token_hash,
                        :csrf_secret_hash, :expires_at
                    )
                    RETURNING id, user_id, family_id, refresh_token_hash,
                              csrf_secret_hash, expires_at, revoked_at
                    """
                    ),
                    asdict(session),
                )
            )
            .mappings()
            .one()
        )
        return SessionRecord(**dict(row))

    async def find_active_session(
        self, session_id: UUID, now: datetime
    ) -> tuple[SessionRecord, UserRecord] | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                    SELECT s.id AS session_id, s.user_id, s.family_id, s.refresh_token_hash,
                           s.csrf_secret_hash, s.expires_at, s.revoked_at,
                           u.id AS user_id, u.email AS user_email,
                           u.password_hash AS user_password_hash, u.status AS user_status,
                           u.email_verified_at AS user_email_verified_at,
                           u.failed_login_count AS user_failed_login_count,
                           u.locked_until AS user_locked_until,
                           u.is_platform_admin AS user_is_platform_admin
                    FROM talaqi.sessions AS s JOIN talaqi.users AS u ON u.id = s.user_id
                    WHERE s.id = :session_id AND s.revoked_at IS NULL AND s.expires_at > :now
                    """
                    ),
                    {"session_id": session_id, "now": now},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        session = SessionRecord(
            id=row["session_id"],
            user_id=row["user_id"],
            family_id=row["family_id"],
            refresh_token_hash=row["refresh_token_hash"],
            csrf_secret_hash=row["csrf_secret_hash"],
            expires_at=row["expires_at"],
            revoked_at=row["revoked_at"],
        )
        return session, _user(
            {name.strip(): row[f"user_{name.strip()}"] for name in _USER_COLUMNS.split(",")}
        )

    async def revoke_session(self, session_id: UUID, reason: str, now: datetime) -> None:
        await self._session.execute(
            text(
                """
                UPDATE talaqi.sessions SET revoked_at = COALESCE(revoked_at, :now),
                    revoke_reason = COALESCE(revoke_reason, :reason)
                WHERE id = :session_id
                """
            ),
            {"session_id": session_id, "reason": reason, "now": now},
        )
