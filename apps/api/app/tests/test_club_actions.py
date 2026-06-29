from datetime import UTC, datetime

import pytest

from app.core.security import CurrentUser
from app.modules.clubs import service
from app.modules.clubs.schemas import ClubMembershipState


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@pytest.mark.asyncio
async def test_join_club_action_commits_database_function_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_member_1",
        email="member@communiti.local",
    )
    membership = ClubMembershipState(
        id="22222222-2222-2222-2222-222222222222",
        club_id="33333333-3333-3333-3333-333333333333",
        user_id=current_user.id,
        role="member",
        status="active",
        joined_at=datetime.now(UTC),
    )

    async def fake_get_club_by_id(*args: object, **kwargs: object) -> object:
        return object()

    async def fake_join_club_for_user(
        *args: object, **kwargs: object
    ) -> ClubMembershipState:
        return membership

    monkeypatch.setattr(service, "get_club_by_id", fake_get_club_by_id)
    monkeypatch.setattr(service, "join_club_for_user", fake_join_club_for_user)

    result = await service.join_club_action(
        fake_session,  # type: ignore[arg-type]
        club_id=membership.club_id,
        current_user=current_user,
    )

    assert result == membership
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_leave_club_action_returns_left_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_member_1",
        email="member@communiti.local",
    )
    membership = ClubMembershipState(
        id="22222222-2222-2222-2222-222222222222",
        club_id="33333333-3333-3333-3333-333333333333",
        user_id=current_user.id,
        role="member",
        status="left",
        joined_at=datetime.now(UTC),
        left_at=datetime.now(UTC),
    )

    async def fake_get_club_by_id(*args: object, **kwargs: object) -> object:
        return object()

    async def fake_leave_club_for_user(*args: object, **kwargs: object) -> None:
        return None

    async def fake_get_user_club_membership(
        *args: object, **kwargs: object
    ) -> ClubMembershipState:
        return membership

    monkeypatch.setattr(service, "get_club_by_id", fake_get_club_by_id)
    monkeypatch.setattr(service, "leave_club_for_user", fake_leave_club_for_user)
    monkeypatch.setattr(
        service, "get_user_club_membership", fake_get_user_club_membership
    )

    result = await service.leave_club_action(
        fake_session,  # type: ignore[arg-type]
        club_id=membership.club_id,
        current_user=current_user,
    )

    assert result.status == "left"
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_join_club_action_raises_when_club_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_member_1",
        email="member@communiti.local",
    )

    async def fake_get_club_by_id(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(service, "get_club_by_id", fake_get_club_by_id)

    with pytest.raises(service.ClubNotFoundError):
        await service.join_club_action(
            fake_session,  # type: ignore[arg-type]
            club_id="33333333-3333-3333-3333-333333333333",
            current_user=current_user,
        )

    assert fake_session.committed is False
    assert fake_session.rolled_back is False
