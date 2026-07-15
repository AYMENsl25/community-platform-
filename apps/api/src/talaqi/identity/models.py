from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

UserStatus = Literal["active", "suspended", "deleted"]


@dataclass(frozen=True, slots=True)
class NewUser:
    id: UUID
    email: str
    password_hash: str
    terms_version: str
    privacy_version: str
    age_attested_at: datetime


@dataclass(frozen=True, slots=True)
class UserRecord:
    id: UUID
    email: str
    password_hash: str
    status: UserStatus
    email_verified_at: datetime | None
    failed_login_count: int
    locked_until: datetime | None
    is_platform_admin: bool


@dataclass(frozen=True, slots=True)
class LoginState:
    failed_login_count: int
    locked_until: datetime | None


@dataclass(frozen=True, slots=True)
class NewSession:
    id: UUID
    user_id: UUID
    family_id: UUID
    refresh_token_hash: bytes
    csrf_secret_hash: bytes
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class SessionRecord(NewSession):
    revoked_at: datetime | None
    rotated_at: datetime | None = None
    revoke_reason: str | None = None
    replaced_by_session_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class AuthPrincipal:
    user_id: UUID
    session_id: UUID
    email_verified: bool
    status: UserStatus
    is_platform_admin: bool


@dataclass(frozen=True, slots=True)
class LoginResult:
    principal: AuthPrincipal
    access_cookie: str
    credentials: SessionCredentials


@dataclass(frozen=True, slots=True)
class SessionCredentials:
    refresh_token: str
    csrf_secret: str
    refresh_hash: bytes
    csrf_hash: bytes

    def refresh_token_hash(self) -> bytes:
        return self.refresh_hash

    def csrf_secret_hash(self) -> bytes:
        return self.csrf_hash


@dataclass(frozen=True, slots=True)
class NewAuthToken:
    id: UUID
    user_id: UUID
    kind: str
    token_hash: bytes
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AuthTokenRecord(NewAuthToken):
    used_at: datetime | None


@dataclass(frozen=True, slots=True)
class SessionBundle:
    principal: AuthPrincipal
    access_cookie: str
    credentials: SessionCredentials


@dataclass(frozen=True, slots=True)
class SessionSummary:
    id: UUID
    current: bool
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    accepted: bool = True
