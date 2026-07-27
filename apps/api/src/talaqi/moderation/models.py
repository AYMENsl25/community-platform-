from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

TargetType = Literal["user", "club", "event"]
CaseStatus = Literal["open", "investigating", "actioned", "dismissed"]
Priority = Literal["standard", "high", "emergency"]
ModerationAction = Literal["suspend", "unpublish", "restore"]

REPORT_CATEGORIES = (
    "safety",
    "harassment",
    "fraud",
    "illegal_content",
    "privacy",
    "spam",
    "other",
)


@dataclass(frozen=True, slots=True)
class ModerationCase:
    id: UUID
    reporter_user_id: UUID | None
    target_type: TargetType
    target_id: UUID
    category: str
    description: str
    status: CaseStatus
    priority: Priority
    assigned_admin_user_id: UUID | None
    resolution_reason: str | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ModerationTarget:
    type: TargetType
    id: UUID
    label: str
    secondary_label: str | None
    status: str


@dataclass(frozen=True, slots=True)
class ModerationCaseEvent:
    id: UUID
    moderation_case_id: UUID
    actor_user_id: UUID | None
    action: str | None
    from_status: str | None
    to_status: str
    reason: str
    created_at: datetime
