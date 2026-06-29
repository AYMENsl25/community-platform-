from pydantic import BaseModel


class CurrentUserProfile(BaseModel):
    id: str
    clerk_user_id: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    platform_role: str
