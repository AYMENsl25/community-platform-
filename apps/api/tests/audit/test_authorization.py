from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import pytest
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.security.authorization import (
    can_access_admin,
    can_confirm_cash,
    can_edit_club,
    can_manage_event,
    can_manage_members,
    can_moderate,
    can_perform_admin_action,
)

ACTOR_ID = UUID("019b2345-6789-7abc-8def-0123456789ab")
OTHER_USER_ID = UUID("019b2345-6789-7abc-8def-0123456789ac")
CLUB_ID = UUID("019b2345-6789-7abc-8def-0123456789ad")
OTHER_CLUB_ID = UUID("019b2345-6789-7abc-8def-0123456789ae")
EVENT_ID = UUID("019b2345-6789-7abc-8def-0123456789af")


@dataclass(frozen=True)
class Club:
    id: UUID = CLUB_ID
    owner_user_id: UUID = OTHER_USER_ID
    status: str = "published"


@dataclass(frozen=True)
class Membership:
    club_id: UUID = CLUB_ID
    user_id: UUID = ACTOR_ID
    role: str = "member"


@dataclass(frozen=True)
class Event:
    id: UUID = EVENT_ID
    ownership_type: str = "club"
    owner_user_id: UUID | None = None
    club_id: UUID | None = CLUB_ID
    status: str = "published"


def principal(
    *,
    user_id: UUID = ACTOR_ID,
    status: str = "active",
    is_platform_admin: bool = False,
) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id,
        session_id=UUID("019b2345-6789-7abc-8def-0123456789b0"),
        email_verified=True,
        status=status,  # type: ignore[arg-type]
        is_platform_admin=is_platform_admin,
    )


def assert_forbidden(call: Callable[[], None], *, code: str = "forbidden") -> None:
    with pytest.raises(ApiError) as captured:
        call()
    assert captured.value.status_code == 403
    assert captured.value.code == code


@pytest.mark.parametrize("policy", [can_edit_club, can_manage_members])
@pytest.mark.parametrize(
    ("role", "is_owner", "allowed"),
    [
        (None, True, True),
        ("owner", False, True),
        ("admin", False, True),
        ("member", False, False),
        (None, False, False),
    ],
)
def test_club_role_action_matrix(
    policy: Callable[[AuthPrincipal, Club, Membership | None], None],
    role: str | None,
    is_owner: bool,
    allowed: bool,
) -> None:
    actor = principal()
    club = Club(owner_user_id=actor.user_id if is_owner else OTHER_USER_ID)
    membership = Membership(role=role) if role is not None else None

    if allowed:
        assert policy(actor, club, membership) is None
    else:
        assert_forbidden(lambda: policy(actor, club, membership))


@pytest.mark.parametrize("policy", [can_edit_club, can_manage_members])
def test_club_policy_rejects_membership_from_another_club(
    policy: Callable[[AuthPrincipal, Club, Membership | None], None],
) -> None:
    assert_forbidden(
        lambda: policy(
            principal(),
            Club(),
            Membership(club_id=OTHER_CLUB_ID, role="admin"),
        )
    )


@pytest.mark.parametrize("policy", [can_edit_club, can_manage_members])
def test_club_policy_rejects_membership_for_another_user(
    policy: Callable[[AuthPrincipal, Club, Membership | None], None],
) -> None:
    assert_forbidden(
        lambda: policy(
            principal(),
            Club(),
            Membership(user_id=OTHER_USER_ID, role="admin"),
        )
    )


@pytest.mark.parametrize("policy", [can_edit_club, can_manage_members])
@pytest.mark.parametrize("club_status", ["suspended", "closed"])
def test_club_policy_rejects_inactive_club_even_for_owner(
    policy: Callable[[AuthPrincipal, Club, Membership | None], None],
    club_status: str,
) -> None:
    actor = principal()
    assert_forbidden(
        lambda: policy(actor, Club(owner_user_id=actor.user_id, status=club_status), None)
    )


@pytest.mark.parametrize("policy", [can_manage_event, can_confirm_cash])
@pytest.mark.parametrize(
    ("role", "is_owner", "allowed"),
    [
        (None, True, True),
        ("owner", False, True),
        ("admin", False, True),
        ("member", False, False),
        (None, False, False),
    ],
)
def test_club_event_role_action_matrix(
    policy: Callable[[AuthPrincipal, Event, Club | None, Membership | None], None],
    role: str | None,
    is_owner: bool,
    allowed: bool,
) -> None:
    actor = principal()
    club = Club(owner_user_id=actor.user_id if is_owner else OTHER_USER_ID)
    membership = Membership(role=role) if role is not None else None

    if allowed:
        assert policy(actor, Event(), club, membership) is None
    else:
        assert_forbidden(lambda: policy(actor, Event(), club, membership))


@pytest.mark.parametrize("policy", [can_manage_event, can_confirm_cash])
def test_independent_event_owner_is_scoped_to_exact_event(
    policy: Callable[[AuthPrincipal, Event, Club | None, Membership | None], None],
) -> None:
    actor = principal()
    owned_event = Event(
        ownership_type="independent",
        owner_user_id=actor.user_id,
        club_id=None,
    )
    another_organizers_event = Event(
        id=UUID("019b2345-6789-7abc-8def-0123456789b1"),
        ownership_type="independent",
        owner_user_id=OTHER_USER_ID,
        club_id=None,
    )

    assert policy(actor, owned_event, None, None) is None
    assert_forbidden(lambda: policy(actor, another_organizers_event, None, None))


@pytest.mark.parametrize("policy", [can_manage_event, can_confirm_cash])
def test_club_event_policy_rejects_cross_club_context(
    policy: Callable[[AuthPrincipal, Event, Club | None, Membership | None], None],
) -> None:
    actor = principal()
    unrelated_club = Club(id=OTHER_CLUB_ID, owner_user_id=actor.user_id)
    assert_forbidden(lambda: policy(actor, Event(), unrelated_club, None))
    assert_forbidden(
        lambda: policy(
            actor,
            Event(),
            Club(),
            Membership(club_id=OTHER_CLUB_ID, role="admin"),
        )
    )


@pytest.mark.parametrize("policy", [can_manage_event, can_confirm_cash])
def test_event_policy_rejects_suspended_event_even_for_owner(
    policy: Callable[[AuthPrincipal, Event, Club | None, Membership | None], None],
) -> None:
    actor = principal()
    event = Event(
        ownership_type="independent",
        owner_user_id=actor.user_id,
        club_id=None,
        status="suspended",
    )
    assert_forbidden(lambda: policy(actor, event, None, None))


def test_admin_policy_requires_active_platform_admin_and_mfa_for_actions() -> None:
    admin = principal(is_platform_admin=True)
    member = principal()

    assert can_access_admin(admin) is None
    assert can_perform_admin_action(admin, has_active_mfa=True) is None
    assert can_moderate(admin, has_active_mfa=True) is None
    assert_forbidden(lambda: can_access_admin(member))
    assert_forbidden(lambda: can_perform_admin_action(member, has_active_mfa=True))
    assert_forbidden(lambda: can_moderate(admin, has_active_mfa=False), code="admin_mfa_required")


INACTIVE_POLICY_CALLS: tuple[Callable[[AuthPrincipal], None], ...] = (
    lambda actor: can_edit_club(actor, Club(owner_user_id=ACTOR_ID), None),
    lambda actor: can_manage_members(actor, Club(owner_user_id=ACTOR_ID), None),
    lambda actor: can_manage_event(
        actor,
        Event(ownership_type="independent", owner_user_id=ACTOR_ID, club_id=None),
        None,
        None,
    ),
    lambda actor: can_confirm_cash(
        actor,
        Event(ownership_type="independent", owner_user_id=ACTOR_ID, club_id=None),
        None,
        None,
    ),
    lambda actor: can_access_admin(actor),
    lambda actor: can_perform_admin_action(actor, has_active_mfa=True),
    lambda actor: can_moderate(actor, has_active_mfa=True),
)


@pytest.mark.parametrize(
    "policy_call",
    INACTIVE_POLICY_CALLS,
)
@pytest.mark.parametrize("status", ["suspended", "deleted"])
def test_every_policy_rejects_inactive_actor(
    policy_call: Callable[[AuthPrincipal], None],
    status: str,
) -> None:
    assert_forbidden(lambda: policy_call(principal(status=status, is_platform_admin=True)))
