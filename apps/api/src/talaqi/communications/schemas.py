from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    id: UUID
    type_key: str
    title_key: str
    body_key: str
    parameters: dict[str, object]
    action_path: str | None
    source_type: str | None
    source_id: UUID | None
    read_at: datetime | None
    created_at: datetime


class NotificationPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[NotificationResponse]
    next_cursor: str | None


class UnreadCountResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    unread_count: int


class MarkAllReadResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    marked_count: int


class NotificationPreferencesResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    security_email: Literal[True]
    event_email: bool
    community_email: bool


class NotificationPreferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_email: bool
    community_email: bool


__all__ = [
    "MarkAllReadResponse",
    "NotificationPageResponse",
    "NotificationPreferencesRequest",
    "NotificationPreferencesResponse",
    "NotificationResponse",
    "UnreadCountResponse",
]
