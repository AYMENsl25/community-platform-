from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Notification:
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


@dataclass(frozen=True, slots=True)
class NotificationPreferences:
    security_email: bool
    event_email: bool
    community_email: bool


__all__ = ["Notification", "NotificationPreferences"]
