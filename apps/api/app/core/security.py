from dataclasses import dataclass

from fastapi import HTTPException, status


@dataclass(frozen=True)
class CurrentUser:
    id: str
    clerk_user_id: str
    email: str
    platform_role: str = "user"


def require_authenticated_user() -> CurrentUser:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Clerk authentication will be implemented after read APIs are connected.",
    )
