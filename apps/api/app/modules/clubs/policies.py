from app.core.security import CurrentUser

MANAGER_ROLES = {"owner", "admin"}


def can_manage_club(
    user: CurrentUser,
    *,
    owner_id: str,
    member_role: str | None = None,
    member_status: str | None = None,
) -> bool:
    if user.platform_role == "admin":
        return True
    if owner_id == user.id:
        return True
    return member_role in MANAGER_ROLES and member_status == "active"
