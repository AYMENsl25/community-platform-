from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.identity.models import (
    AuthTokenRecord,
    LoginState,
    NewAuthToken,
    NewSession,
    NewUser,
    SessionRecord,
    SessionSummary,
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
    async def touch_session(self, session_id: UUID, user_id: UUID, now: datetime) -> None: ...
    async def find_user_by_email(self, email: str) -> UserRecord | None: ...
    async def create_auth_token(self, token: NewAuthToken, locale_hint: str) -> None: ...
    async def lock_auth_token(
        self, token_id: UUID
    ) -> tuple[AuthTokenRecord, UserRecord] | None: ...
    async def mark_auth_token_used(self, token_id: UUID, now: datetime) -> None: ...
    async def mark_email_verified(self, user_id: UUID, now: datetime) -> None: ...
    async def replace_password(self, user_id: UUID, password_hash: str) -> None: ...
    async def find_refresh_session_for_update(
        self, refresh_hash: bytes
    ) -> tuple[SessionRecord, UserRecord] | None: ...
    async def rotate_session(
        self, current: SessionRecord, replacement: NewSession, now: datetime
    ) -> None: ...
    async def revoke_family(self, family_id: UUID, reason: str, now: datetime) -> None: ...
    async def persist_replay_revocation(self, family_id: UUID, now: datetime) -> None: ...
    async def revoke_all_sessions(self, user_id: UUID, reason: str, now: datetime) -> None: ...
    async def list_sessions(
        self, user_id: UUID, current_id: UUID
    ) -> tuple[SessionSummary, ...]: ...
    async def revoke_owned_session(
        self, user_id: UUID, session_id: UUID, reason: str, now: datetime
    ) -> bool: ...


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

    async def touch_session(self, session_id: UUID, user_id: UUID, now: datetime) -> None:
        await self._session.execute(
            text(
                """UPDATE talaqi.sessions SET last_used_at=:now
                WHERE id=:session_id AND user_id=:user_id AND revoked_at IS NULL
                  AND expires_at>:now"""
            ),
            {"session_id": session_id, "user_id": user_id, "now": now},
        )

    async def find_user_by_email(self, email: str) -> UserRecord | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """SELECT id,email,password_hash,status,email_verified_at,
                        failed_login_count,locked_until,is_platform_admin
                        FROM talaqi.users WHERE lower(email)=:email"""
                    ),
                    {"email": email},
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else _user(dict(row))

    async def create_auth_token(self, token: NewAuthToken, locale_hint: str) -> None:
        await self._session.execute(
            text(
                """
                UPDATE talaqi.auth_tokens SET used_at = COALESCE(used_at, clock_timestamp())
                WHERE user_id=:user_id AND kind=CAST(:kind AS talaqi.auth_token_kind)
                  AND used_at IS NULL
                """
            ),
            {"user_id": token.user_id, "kind": token.kind},
        )
        await self._session.execute(
            text(
                """
                INSERT INTO talaqi.auth_tokens (id,user_id,kind,token_hash,expires_at)
                VALUES (:id,:user_id,CAST(:kind AS talaqi.auth_token_kind),:token_hash,:expires_at)
                """
            ),
            asdict(token),
        )
        await self._session.execute(
            text(
                """
                INSERT INTO talaqi.outbox_events (
                    id,aggregate_type,aggregate_id,event_type,payload,deduplication_key
                ) VALUES (
                    uuidv7(),'user',:user_id,:event_type,
                    jsonb_build_object('user_id',CAST(:user_text AS text),
                                       'auth_token_id',CAST(:token_text AS text),
                                       'locale_hint',CAST(:locale_hint AS text),
                                       'template',CAST(:template AS text)),
                    :deduplication_key
                )
                """
            ),
            {
                "user_id": token.user_id,
                "user_text": str(token.user_id),
                "token_text": str(token.id),
                "locale_hint": locale_hint,
                "template": token.kind,
                "event_type": f"identity.{token.kind}_requested",
                "deduplication_key": f"identity:{token.kind}:{token.id}",
            },
        )

    async def lock_auth_token(self, token_id: UUID) -> tuple[AuthTokenRecord, UserRecord] | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT t.id AS token_id,t.user_id AS token_user_id,
                               t.kind::text AS token_kind,
                               t.token_hash,t.expires_at AS token_expires_at,t.used_at,
                               u.id,u.email,u.password_hash,u.status,u.email_verified_at,
                               u.failed_login_count,u.locked_until,u.is_platform_admin
                        FROM talaqi.auth_tokens t
                        JOIN talaqi.users u ON u.id=t.user_id
                        WHERE t.id=:token_id
                        FOR UPDATE OF t
                        """
                    ),
                    {"token_id": token_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        token = AuthTokenRecord(
            id=row["token_id"],
            user_id=row["token_user_id"],
            kind=row["token_kind"],
            token_hash=row["token_hash"],
            expires_at=row["token_expires_at"],
            used_at=row["used_at"],
        )
        return token, _user(dict(row))

    async def mark_auth_token_used(self, token_id: UUID, now: datetime) -> None:
        await self._session.execute(
            text("UPDATE talaqi.auth_tokens SET used_at=:now WHERE id=:token_id"),
            {"now": now, "token_id": token_id},
        )

    async def mark_email_verified(self, user_id: UUID, now: datetime) -> None:
        await self._session.execute(
            text(
                """UPDATE talaqi.users
                SET email_verified_at=COALESCE(email_verified_at,:now) WHERE id=:id"""
            ),
            {"id": user_id, "now": now},
        )

    async def replace_password(self, user_id: UUID, password_hash: str) -> None:
        await self._session.execute(
            text("UPDATE talaqi.users SET password_hash=:password_hash WHERE id=:id"),
            {"id": user_id, "password_hash": password_hash},
        )

    async def find_refresh_session_for_update(
        self, refresh_hash: bytes
    ) -> tuple[SessionRecord, UserRecord] | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT s.id,s.user_id,s.family_id,s.refresh_token_hash,s.csrf_secret_hash,
                               s.expires_at,s.revoked_at,s.rotated_at,s.revoke_reason,
                               s.replaced_by_session_id,
                               u.id AS account_id,u.email AS account_email,
                               u.password_hash AS account_password_hash,
                               u.status AS account_status,
                               u.email_verified_at AS account_email_verified_at,
                               u.failed_login_count AS account_failed_login_count,
                               u.locked_until AS account_locked_until,
                               u.is_platform_admin AS account_is_platform_admin
                        FROM talaqi.sessions s JOIN talaqi.users u ON u.id=s.user_id
                        WHERE s.refresh_token_hash=:refresh_hash FOR UPDATE OF s
                        """
                    ),
                    {"refresh_hash": refresh_hash},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        data = dict(row)
        session = SessionRecord(
            id=data["id"],
            user_id=data["user_id"],
            family_id=data["family_id"],
            refresh_token_hash=data["refresh_token_hash"],
            csrf_secret_hash=data["csrf_secret_hash"],
            expires_at=data["expires_at"],
            revoked_at=data["revoked_at"],
            rotated_at=data["rotated_at"],
            revoke_reason=data["revoke_reason"],
            replaced_by_session_id=data["replaced_by_session_id"],
        )
        return session, _user(
            {
                "id": data["account_id"],
                "email": data["account_email"],
                "password_hash": data["account_password_hash"],
                "status": data["account_status"],
                "email_verified_at": data["account_email_verified_at"],
                "failed_login_count": data["account_failed_login_count"],
                "locked_until": data["account_locked_until"],
                "is_platform_admin": data["account_is_platform_admin"],
            }
        )

    async def rotate_session(
        self, current: SessionRecord, replacement: NewSession, now: datetime
    ) -> None:
        await self.create_session(replacement)
        await self._session.execute(
            text(
                """
                UPDATE talaqi.sessions SET rotated_at=:now,revoked_at=:now,revoke_reason='rotated',
                    replaced_by_session_id=:replacement WHERE id=:current AND revoked_at IS NULL
                """
            ),
            {"now": now, "replacement": replacement.id, "current": current.id},
        )

    async def revoke_family(self, family_id: UUID, reason: str, now: datetime) -> None:
        await self._session.execute(
            text(
                """UPDATE talaqi.sessions SET revoked_at=COALESCE(revoked_at,:now),
                revoke_reason=COALESCE(revoke_reason,:reason) WHERE family_id=:family_id"""
            ),
            {"family_id": family_id, "reason": reason, "now": now},
        )

    async def persist_replay_revocation(self, family_id: UUID, now: datetime) -> None:
        await self.revoke_family(family_id, "refresh_replay", now)
        # Replay response is an error, so persist the security revocation before it unwinds
        # the request transaction. No caller-controlled data is committed here.
        await self._session.commit()

    async def revoke_all_sessions(self, user_id: UUID, reason: str, now: datetime) -> None:
        await self._session.execute(
            text(
                """UPDATE talaqi.sessions SET revoked_at=COALESCE(revoked_at,:now),
                revoke_reason=COALESCE(revoke_reason,:reason) WHERE user_id=:user_id"""
            ),
            {"user_id": user_id, "reason": reason, "now": now},
        )

    async def list_sessions(self, user_id: UUID, current_id: UUID) -> tuple[SessionSummary, ...]:
        rows = (
            (
                await self._session.execute(
                    text(
                        """SELECT id,created_at,last_used_at,expires_at FROM talaqi.sessions
                        WHERE user_id=:user_id AND revoked_at IS NULL
                          AND expires_at>clock_timestamp()
                        ORDER BY created_at DESC,id DESC"""
                    ),
                    {"user_id": user_id},
                )
            )
            .mappings()
            .all()
        )
        return tuple(SessionSummary(current=row["id"] == current_id, **dict(row)) for row in rows)

    async def revoke_owned_session(
        self, user_id: UUID, session_id: UUID, reason: str, now: datetime
    ) -> bool:
        result = await self._session.execute(
            text(
                """UPDATE talaqi.sessions SET revoked_at=:now,revoke_reason=:reason
                WHERE id=:session_id AND user_id=:user_id AND revoked_at IS NULL"""
            ),
            {"user_id": user_id, "session_id": session_id, "reason": reason, "now": now},
        )
        return cast(CursorResult[object], result).rowcount > 0
