from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClubAnnouncementRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=10_000)
    audience: Literal["all_members", "admins"] = "all_members"


class EventUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    revision: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=10_000)
    audience: Literal["all_active", "confirmed", "cash_pending", "waitlisted"] = "all_active"


class PublishedContentResponse(BaseModel):
    id: UUID
    title: str
    body: str
    audience: str
    published_at: datetime


class PublishedContentPageResponse(BaseModel):
    items: tuple[PublishedContentResponse, ...]


__all__ = [
    "ClubAnnouncementRequest",
    "EventUpdateRequest",
    "PublishedContentPageResponse",
    "PublishedContentResponse",
]
