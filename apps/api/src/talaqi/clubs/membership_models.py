from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

ClubRole = Literal["owner", "admin", "member"]
JoinRequestStatus = Literal["pending", "approved", "rejected", "cancelled"]


@dataclass(frozen=True, slots=True)
class Membership:
    id: UUID
    club_id: UUID
    user_id: UUID
    role: ClubRole
    joined_at: datetime
    display_name: str | None = None
    email: str | None = None


@dataclass(frozen=True, slots=True)
class JoinRequest:
    id: UUID
    club_id: UUID
    user_id: UUID
    status: JoinRequestStatus
    message: str | None
    decided_by_user_id: UUID | None
    decision_reason: str | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime
    display_name: str | None = None
    email: str | None = None


@dataclass(frozen=True, slots=True)
class JoinResult:
    state: Literal["member", "pending"]
    membership: Membership | None = None
    join_request: JoinRequest | None = None
