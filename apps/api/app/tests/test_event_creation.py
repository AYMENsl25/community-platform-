from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.security import CurrentUser
from app.modules.events import service
from app.modules.events.policies import can_manage_club
from app.modules.events.schemas import EventCreate, EventDetail


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def make_payload() -> EventCreate:
    return EventCreate(
        club_id="33333333-3333-3333-3333-333333333333",
        title="Organizer Planning Night",
        starts_at=datetime.now(UTC) + timedelta(days=3),
        price_amount=Decimal("0"),
    )


def test_can_manage_club_allows_owner_admin_and_platform_admin() -> None:
    owner = CurrentUser(
        id="user-owner",
        clerk_user_id="clerk-owner",
        email="owner@example.com",
    )
    admin_member = CurrentUser(
        id="user-admin-member",
        clerk_user_id="clerk-admin-member",
        email="admin-member@example.com",
    )
    platform_admin = CurrentUser(
        id="platform-admin",
        clerk_user_id="clerk-platform-admin",
        email="platform-admin@example.com",
        platform_role="admin",
    )

    assert can_manage_club(owner, owner_id="user-owner") is True
    assert (
        can_manage_club(
            admin_member,
            owner_id="someone-else",
            member_role="admin",
            member_status="active",
        )
        is True
    )
    assert can_manage_club(platform_admin, owner_id="someone-else") is True


def test_can_manage_club_rejects_regular_member() -> None:
    member = CurrentUser(
        id="user-member",
        clerk_user_id="clerk-member",
        email="member@example.com",
    )

    assert (
        can_manage_club(
            member,
            owner_id="someone-else",
            member_role="member",
            member_status="active",
        )
        is False
    )


@pytest.mark.asyncio
async def test_create_event_action_commits_for_club_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_organizer_1",
        email="organizer@communiti.local",
    )
    payload = make_payload()
    event = EventDetail(
        id="22222222-2222-2222-2222-222222222222",
        club_id=payload.club_id,
        created_by=current_user.id,
        club_name="COMMUNITI AI Lab",
        title=payload.title,
        slug="organizer-planning-night",
        description=None,
        event_type=payload.event_type,
        starts_at=payload.starts_at,
        ends_at=None,
        timezone=payload.timezone,
        city=payload.city,
        country=payload.country,
        location_name=None,
        capacity=None,
        registered_count=0,
        waitlist_count=0,
        price_amount=payload.price_amount,
        currency=payload.currency,
        status="draft",
        requires_approval=False,
        club_slug="communiti-ai-lab",
        organizer_name="COMMUNITI Organizer",
        is_full=False,
    )

    async def fake_get_club_management_context(
        *args: object, **kwargs: object
    ) -> dict[str, str | None]:
        return {
            "owner_id": current_user.id,
            "member_role": "owner",
            "member_status": "active",
        }

    async def fake_insert_event(*args: object, **kwargs: object) -> str:
        return event.id

    async def fake_get_event_by_id(*args: object, **kwargs: object) -> EventDetail:
        return event

    monkeypatch.setattr(
        service, "get_club_management_context", fake_get_club_management_context
    )
    monkeypatch.setattr(service, "insert_event", fake_insert_event)
    monkeypatch.setattr(service, "get_event_by_id", fake_get_event_by_id)

    result = await service.create_event_action(
        fake_session,  # type: ignore[arg-type]
        payload=payload,
        current_user=current_user,
    )

    assert result == event
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_create_event_action_rejects_regular_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_member_1",
        email="member@communiti.local",
    )

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

    with pytest.raises(service.EventForbiddenError):
        await service.create_event_action(
            fake_session,  # type: ignore[arg-type]
            payload=make_payload(),
            current_user=current_user,
        )

    assert fake_session.committed is False
    assert fake_session.rolled_back is False
