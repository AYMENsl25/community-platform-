from __future__ import annotations

from typing import Protocol
from uuid import UUID

from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError


class ClubProtocol(Protocol):
    @property
    def id(self) -> UUID: ...

    @property
    def owner_user_id(self) -> UUID: ...

    @property
    def status(self) -> str: ...


class EventProtocol(Protocol):
    @property
    def id(self) -> UUID: ...

    @property
    def ownership_type(self) -> str: ...

    @property
    def owner_user_id(self) -> UUID | None: ...

    @property
    def club_id(self) -> UUID | None: ...

    @property
    def status(self) -> str: ...


class MembershipProtocol(Protocol):
    @property
    def club_id(self) -> UUID: ...

    @property
    def user_id(self) -> UUID: ...

    @property
    def role(self) -> str: ...


def _forbidden() -> ApiError:
    return ApiError(code="forbidden", message_key="errors.forbidden", status_code=403)


def _mfa_required() -> ApiError:
    return ApiError(
        code="admin_mfa_required",
        message_key="errors.admin_mfa_required",
        status_code=403,
    )


def _check_active(principal: AuthPrincipal) -> None:
    if principal.status != "active":
        raise _forbidden()


def _is_club_manager(
    principal: AuthPrincipal,
    club: ClubProtocol,
    membership: MembershipProtocol | None,
) -> bool:
    if principal.user_id == club.owner_user_id:
        return True
    return (
        membership is not None
        and membership.club_id == club.id
        and membership.user_id == principal.user_id
        and membership.role in ("owner", "admin")
    )


def can_edit_club(
    principal: AuthPrincipal, club: ClubProtocol, membership: MembershipProtocol | None
) -> None:
    _check_active(principal)
    if club.status in ("suspended", "closed"):
        raise _forbidden()
    if _is_club_manager(principal, club, membership):
        return
    raise _forbidden()


def can_manage_members(
    principal: AuthPrincipal, club: ClubProtocol, membership: MembershipProtocol | None
) -> None:
    _check_active(principal)
    if club.status in ("suspended", "closed"):
        raise _forbidden()
    if _is_club_manager(principal, club, membership):
        return
    raise _forbidden()


def can_manage_event(
    principal: AuthPrincipal,
    event: EventProtocol,
    club: ClubProtocol | None,
    membership: MembershipProtocol | None,
) -> None:
    _check_active(principal)
    if event.status == "suspended":
        raise _forbidden()
    if event.ownership_type == "independent":
        if event.club_id is not None or principal.user_id != event.owner_user_id:
            raise _forbidden()
        return
    if event.ownership_type != "club" or event.owner_user_id is not None:
        raise _forbidden()
    if club is None or event.club_id != club.id:
        raise _forbidden()
    if club.status in ("suspended", "closed"):
        raise _forbidden()
    if _is_club_manager(principal, club, membership):
        return
    raise _forbidden()


def can_confirm_cash(
    principal: AuthPrincipal,
    event: EventProtocol,
    club: ClubProtocol | None,
    membership: MembershipProtocol | None,
) -> None:
    can_manage_event(principal, event, club, membership)


def can_access_admin(principal: AuthPrincipal) -> None:
    _check_active(principal)
    if not principal.is_platform_admin:
        raise _forbidden()


def can_perform_admin_action(
    principal: AuthPrincipal,
    *,
    has_active_mfa: bool,
) -> None:
    can_access_admin(principal)
    if not has_active_mfa:
        raise _mfa_required()


def can_moderate(principal: AuthPrincipal, *, has_active_mfa: bool) -> None:
    can_perform_admin_action(principal, has_active_mfa=has_active_mfa)
