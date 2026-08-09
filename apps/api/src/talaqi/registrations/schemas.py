from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from talaqi.registrations.models import RegistrationMethod, RegistrationState


class RegistrationCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    private_link: SecretStr | None = None


class RegistrationResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    event_id: UUID
    user_id: UUID
    method: RegistrationMethod
    state: RegistrationState
    seat_held: bool
    waitlist_sequence: int | None
    cash_expires_at: datetime | None
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    expired_at: datetime | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime


class AttendeeResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    registration_id: UUID
    user_id: UUID
    username: str
    display_name: str
    method: RegistrationMethod
    state: RegistrationState
    waitlist_sequence: int | None
    cash_expires_at: datetime | None
    confirmed_at: datetime | None
    created_at: datetime


class AttendeePageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[AttendeeResponse]
    next_cursor: str | None


class AttendeeExportRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    state: RegistrationState | None = None
    search: str | None = Field(default=None, min_length=1, max_length=80)


class AttendeeExportResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: UUID
    status: Literal["queued"]


__all__ = [
    "AttendeeExportRequest",
    "AttendeeExportResponse",
    "AttendeePageResponse",
    "AttendeeResponse",
    "RegistrationCreateRequest",
    "RegistrationResponse",
]
