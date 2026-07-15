from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)
    age_attested: Literal[True]
    terms_version: str = Field(min_length=1, max_length=64)
    privacy_version: str = Field(min_length=1, max_length=64)


class RegistrationResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    accepted: Literal[True] = True


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identifier: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class AuthenticationResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    authenticated: Literal[True] = True
    email_verified: bool
    status: Literal["active"] = "active"


class LogoutResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    logged_out: Literal[True] = True


class RecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)


class RecoveryConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=40, max_length=200)


class PasswordResetConfirm(RecoveryConfirm):
    new_password: str = Field(min_length=12, max_length=128)


class AcceptedResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    accepted: Literal[True] = True


class ConfirmedResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    confirmed: Literal[True] = True


class RefreshedResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    refreshed: Literal[True] = True
    email_verified: bool


class SessionResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: UUID
    current: bool
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime


class SessionsResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    sessions: tuple[SessionResponse, ...]


class RevokedResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    revoked: Literal[True] = True
