from __future__ import annotations

import hashlib
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
    refresh_token: bytes
    csrf_secret: bytes

    def refresh_token_hash(self) -> bytes:
        return hashlib.sha256(b"talaqi:refresh:v1\0" + self.refresh_token).digest()

    def csrf_secret_hash(self) -> bytes:
        return hashlib.sha256(b"talaqi:csrf:v1\0" + self.csrf_secret).digest()


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    accepted: bool = True
