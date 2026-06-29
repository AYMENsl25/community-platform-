from datetime import datetime

from pydantic import BaseModel, Field


class OrganizerRequestCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class OrganizerRequestReview(BaseModel):
    admin_note: str | None = Field(default=None, max_length=1000)


class OrganizerRequestState(BaseModel):
    id: str
    user_id: str
    user_email: str
    user_display_name: str
    status: str
    reason: str | None = None
    admin_note: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
