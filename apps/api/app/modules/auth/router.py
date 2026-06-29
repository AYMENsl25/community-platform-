from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, require_authenticated_user
from app.modules.auth.schemas import CurrentUserProfile

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=CurrentUserProfile)
async def get_me(
    current_user: Annotated[CurrentUser, Depends(require_authenticated_user)],
) -> CurrentUserProfile:
    return CurrentUserProfile(
        id=current_user.id,
        clerk_user_id=current_user.clerk_user_id,
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        platform_role=current_user.platform_role,
    )
