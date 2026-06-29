from datetime import datetime

from pydantic import BaseModel


class ClubCard(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    logo_url: str | None = None
    cover_image_url: str | None = None
    city: str | None = None
    country: str | None = None
    member_count: int
    category_name: str | None = None


class ClubDetail(ClubCard):
    owner_id: str
    category_id: str | None = None
    visibility: str
    status: str
    owner_name: str
    owner_avatar_url: str | None = None


class ClubMembershipState(BaseModel):
    id: str
    club_id: str
    user_id: str
    role: str
    status: str
    joined_at: datetime
    left_at: datetime | None = None
