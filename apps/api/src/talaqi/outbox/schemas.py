from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OperationalOutboxEventResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    id: UUID
    aggregate_type: str
    event_type: str
    status: str
    attempt_count: int
    last_error_code: str | None
    available_at: datetime
    created_at: datetime
    processed_at: datetime | None
    locked_until: datetime | None


class OperationalOutboxPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: list[OperationalOutboxEventResponse]
    next_cursor: None = None


class OutboxRetryRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    reason: str = Field(min_length=3, max_length=1_000)


class OutboxRetryResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event: OperationalOutboxEventResponse
    status: Literal["retried"] = "retried"
