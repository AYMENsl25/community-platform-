from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    id: UUID
    aggregate_type: str
    aggregate_id: UUID
    event_type: str
    payload: dict[str, object]
    deduplication_key: str
    attempt_count: int
    created_at: datetime
    locked_until: datetime


@dataclass(frozen=True, slots=True)
class DeadLetter:
    id: UUID
    aggregate_type: str
    aggregate_id: UUID
    event_type: str
    deduplication_key: str
    attempt_count: int
    last_error_code: str | None
    created_at: datetime


__all__ = ["DeadLetter", "OutboxEvent"]
