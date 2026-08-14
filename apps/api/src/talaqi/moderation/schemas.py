from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from talaqi.moderation.models import (
    CaseStatus,
    ModerationAction,
    Priority,
    TargetType,
)


class ReportRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    target_type: TargetType
    target_id: UUID
    category: Literal[
        "safety", "harassment", "fraud", "illegal_content", "privacy", "spam", "other"
    ]
    description: str = Field(min_length=10, max_length=5_000)
    source_path: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        pattern=r"^/[A-Za-z0-9/_-]*$",
        description="Optional query-free application path where the issue was observed.",
    )


class ReportResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    status: Literal["open"]
    priority: Priority
    emergency_notice: bool
    created_at: datetime


class TargetResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    type: TargetType
    id: UUID
    label: str
    secondary_label: str | None
    status: str


class CaseResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    category: str
    status: CaseStatus
    priority: Priority
    assigned_admin_user_id: UUID | None
    resolution_reason: str | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    emergency_notice: bool
    response_due_at: datetime
    response_breached: bool
    target: TargetResponse
    available_actions: list[ModerationAction]


class CasePageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: list[CaseResponse]
    next_cursor: str | None


class CaseEventResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: UUID
    actor_user_id: UUID | None
    action: str | None
    from_status: str | None
    to_status: str
    reason: str
    created_at: datetime


class CaseDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    case: CaseResponse
    events: list[CaseEventResponse]


class TargetPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: list[TargetResponse]
    next_cursor: None = None


class ActionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    action: ModerationAction
    reason: str = Field(min_length=1, max_length=2_000)


class ActionResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    action: ModerationAction
    case: CaseResponse
    events: list[CaseEventResponse]
    status: Literal["actioned"] = "actioned"


class AuditResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: UUID
    actor_user_id: UUID | None
    actor_kind: str
    action: str
    target_type: str
    target_id: UUID | None
    reason: str | None
    safe_before: dict[str, object] | None
    safe_after: dict[str, object] | None
    request_id: UUID | None
    created_at: datetime


class AuditPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: list[AuditResponse]
    next_cursor: str | None
