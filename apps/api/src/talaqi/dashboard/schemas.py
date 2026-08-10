from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DashboardEvent(BaseModel):
    id: UUID
    title: str
    start_at: datetime | None
    status: str
    registration_state: str | None = None
    capacity: int | None = None
    held: int | None = None
    cash_pending: int | None = None
    action_path: str


class DashboardClub(BaseModel):
    id: UUID
    name: str
    slug: str
    role: str
    status: str
    pending_requests: int = 0
    action_path: str


class DashboardNotification(BaseModel):
    id: UUID
    type_key: str
    title_key: str
    body_key: str
    action_path: str | None
    read_at: datetime | None
    created_at: datetime


class MemberDashboardResponse(BaseModel):
    upcoming_events: tuple[DashboardEvent, ...]
    saved_events: tuple[DashboardEvent, ...]
    joined_clubs: tuple[DashboardClub, ...]
    notifications: tuple[DashboardNotification, ...]
    profile_blockers: tuple[str, ...]


class OrganizerDashboardResponse(BaseModel):
    clubs: tuple[DashboardClub, ...]
    events: tuple[DashboardEvent, ...]
    alerts: tuple[DashboardAlert, ...]


class DashboardAlert(BaseModel):
    key: str
    action_path: str


__all__ = ["MemberDashboardResponse", "OrganizerDashboardResponse"]
