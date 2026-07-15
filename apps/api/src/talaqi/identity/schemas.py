from __future__ import annotations

from typing import Literal

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
