from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JoinClubRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str | None = Field(default=None, max_length=500)


class JoinClubResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    state: Literal["member", "pending"]
    membership_id: UUID | None
    join_request_id: UUID | None


class MemberResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    user_id: UUID
    display_name: str | None
    email: str | None
    role: Literal["owner", "admin", "member"]
    joined_at: datetime


class MemberPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[MemberResponse]


class JoinRequestResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    user_id: UUID
    display_name: str | None
    email: str | None
    status: Literal["pending", "approved", "rejected", "cancelled"]
    message: str | None
    decision_reason: str | None
    decided_at: datetime | None
    created_at: datetime


class JoinRequestPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[JoinRequestResponse]


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=500)


class RoleChangeRequest(DecisionRequest):
    role: Literal["admin", "member"]


class OwnershipTransferRequest(DecisionRequest):
    target_user_id: UUID


class CloseClubRequest(DecisionRequest):
    pass


class OperationResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["left", "approved", "rejected", "role_changed", "transferred", "closed"]
