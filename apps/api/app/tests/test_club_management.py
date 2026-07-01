import pytest

from app.core.security import CurrentUser
from app.modules.clubs import service
from app.modules.clubs.policies import can_manage_club
from app.modules.clubs.schemas import (
    ClubCreate,
    ClubDeletionState,
    ClubDetail,
    ClubUpdate,
)


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def make_user() -> CurrentUser:
    return CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_member_1",
        email="member@communiti.local",
    )


def make_club(owner: CurrentUser) -> ClubDetail:
    return ClubDetail(
        id="22222222-2222-2222-2222-222222222222",
        owner_id=owner.id,
        category_id=None,
        name="COMMUNITI Makers",
        slug="communiti-makers",
        description=None,
        logo_url=None,
        cover_image_url=None,
        city="Riyadh",
        country="Saudi Arabia",
        visibility="public",
        status="draft",
        member_count=1,
        category_name=None,
        owner_name="COMMUNITI Member",
        owner_avatar_url=None,
    )


def test_can_manage_club_allows_owner_admin_and_platform_admin() -> None:
    owner = CurrentUser(
        id="owner", clerk_user_id="clerk-owner", email="owner@example.com"
    )
    club_admin = CurrentUser(
        id="admin", clerk_user_id="clerk-admin", email="admin@example.com"
    )
    platform_admin = CurrentUser(
        id="platform-admin",
        clerk_user_id="clerk-platform-admin",
        email="platform-admin@example.com",
        platform_role="admin",
    )

    assert can_manage_club(owner, owner_id="owner") is True
    assert (
        can_manage_club(
            club_admin,
            owner_id="someone-else",
            member_role="admin",
            member_status="active",
        )
        is True
    )
    assert can_manage_club(platform_admin, owner_id="someone-else") is True


def test_can_manage_club_rejects_regular_member() -> None:
    user = CurrentUser(
        id="member", clerk_user_id="clerk-member", email="member@example.com"
    )

    assert (
        can_manage_club(
            user,
            owner_id="someone-else",
            member_role="member",
            member_status="active",
        )
        is False
    )


@pytest.mark.asyncio
async def test_create_club_action_allows_any_authenticated_user_and_commits_owner_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = make_user()
    club = make_club(current_user)

    async def fake_insert_club(*args: object, **kwargs: object) -> str:
        return club.id

    async def fake_add_club_owner_membership(*args: object, **kwargs: object) -> None:
        return None

    async def fake_get_club_by_id(*args: object, **kwargs: object) -> ClubDetail:
        return club

    monkeypatch.setattr(service, "insert_club", fake_insert_club)
    monkeypatch.setattr(
        service, "add_club_owner_membership", fake_add_club_owner_membership
    )
    monkeypatch.setattr(service, "get_club_by_id", fake_get_club_by_id)

    result = await service.create_club_action(
        fake_session,  # type: ignore[arg-type]
        payload=ClubCreate(name=club.name),
        current_user=current_user,
    )

    assert result == club
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_update_club_action_rejects_regular_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = make_user()

    async def fake_get_club_management_context(
        *args: object, **kwargs: object
    ) -> dict[str, str | None]:
        return {
            "owner_id": "someone-else",
            "member_role": "member",
            "member_status": "active",
        }

    monkeypatch.setattr(
        service, "get_club_management_context", fake_get_club_management_context
    )

    with pytest.raises(service.ClubForbiddenError):
        await service.update_club_action(
            fake_session,  # type: ignore[arg-type]
            club_id="22222222-2222-2222-2222-222222222222",
            payload=ClubUpdate(name="Nope Club"),
            current_user=current_user,
        )

    assert fake_session.committed is False
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_delete_club_action_soft_deletes_for_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = make_user()
    club_id = "22222222-2222-2222-2222-222222222222"

    async def fake_get_club_management_context(
        *args: object, **kwargs: object
    ) -> dict[str, str | None]:
        return {
            "owner_id": current_user.id,
            "member_role": "owner",
            "member_status": "active",
        }

    async def fake_soft_delete_club_by_id(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        service, "get_club_management_context", fake_get_club_management_context
    )
    monkeypatch.setattr(service, "soft_delete_club_by_id", fake_soft_delete_club_by_id)

    result = await service.delete_club_action(
        fake_session,  # type: ignore[arg-type]
        club_id=club_id,
        current_user=current_user,
    )

    assert isinstance(result, ClubDeletionState)
    assert result.club_id == club_id
    assert result.deleted is True
    assert fake_session.committed is True
    assert fake_session.rolled_back is False
