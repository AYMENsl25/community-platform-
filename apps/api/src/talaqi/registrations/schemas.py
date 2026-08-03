from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, SecretStr

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


__all__ = ["RegistrationCreateRequest", "RegistrationResponse"]
