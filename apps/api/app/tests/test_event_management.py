from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.security import CurrentUser
from app.modules.events import service
from app.modules.events.schemas import (
    EventDetail,
    EventRegistrationAttendee,
    EventUpdate,
)


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def make_event(current_user: CurrentUser) -> EventDetail:
    return EventDetail(
        id="22222222-2222-2222-2222-222222222222",
        club_id="33333333-3333-3333-3333-333333333333",
        created_by=current_user.id,
        club_name="COMMUNITI AI Lab",
        title="Updated Organizer Night",
        slug="updated-organizer-night",
        description=None,
        event_type="community",
        starts_at=datetime.now(UTC) + timedelta(days=3),
        ends_at=None,
        timezone="Asia/Riyadh",
        city="Riyadh",
        country="Saudi Arabia",
        location_name=None,
        capacity=None,
        registered_count=0,
        waitlist_count=0,
        price_amount=Decimal("0"),
        currency="SAR",
        status="draft",
        requires_approval=False,
        club_slug="communiti-ai-lab",
        organizer_name="COMMUNITI Organizer",
        is_full=False,
    )


@pytest.mark.asyncio
async def test_update_event_action_commits_for_club_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_organizer_1",
        email="organizer@communiti.local",
    )
    event = make_event(current_user)

    async def fake_get_event_management_context(
        *args: object, **kwargs: object
    ) -> dict[str, str | None]:
        return {
            "owner_id": current_user.id,
            "member_role": "owner",
            "member_status": "active",
        }

    async def fake_update_event_by_id(*args: object, **kwargs: object) -> None:
        return None

    async def fake_get_event_by_id(*args: object, **kwargs: object) -> EventDetail:
        return event

    monkeypatch.setattr(
        service, "get_event_management_context", fake_get_event_management_context
    )
    monkeypatch.setattr(service, "update_event_by_id", fake_update_event_by_id)
    monkeypatch.setattr(service, "get_event_by_id", fake_get_event_by_id)

    result = await service.update_event_action(
        fake_session,  # type: ignore[arg-type]
        event_id=event.id,
        payload=EventUpdate(title=event.title),
        current_user=current_user,
    )

    assert result == event
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_update_event_action_rejects_regular_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_member_1",
        email="member@communiti.local",
    )

    async def fake_get_event_management_context(
        *args: object, **kwargs: object
    ) -> dict[str, str | None]:
        return {
            "owner_id": "someone-else",
            "member_role": "member",
            "member_status": "active",
        }

    monkeypatch.setattr(
        service, "get_event_management_context", fake_get_event_management_context
    )

    with pytest.raises(service.EventForbiddenError):
        await service.update_event_action(
            fake_session,  # type: ignore[arg-type]
            event_id="22222222-2222-2222-2222-222222222222",
            payload=EventUpdate(title="Nope"),
            current_user=current_user,
        )

    assert fake_session.committed is False
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_delete_event_action_soft_deletes_for_club_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_organizer_1",
        email="organizer@communiti.local",
    )
    event_id = "22222222-2222-2222-2222-222222222222"

    async def fake_get_event_management_context(
        *args: object, **kwargs: object
    ) -> dict[str, str | None]:
        return {
            "owner_id": current_user.id,
            "member_role": "owner",
            "member_status": "active",
        }

    async def fake_soft_delete_event_by_id(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        service, "get_event_management_context", fake_get_event_management_context
    )
    monkeypatch.setattr(
        service, "soft_delete_event_by_id", fake_soft_delete_event_by_id
    )

    result = await service.delete_event_action(
        fake_session,  # type: ignore[arg-type]
        event_id=event_id,
        current_user=current_user,
    )

    assert result.event_id == event_id
    assert result.deleted is True
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_list_event_attendees_action_requires_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_member_1",
        email="member@communiti.local",
    )

    async def fake_get_event_management_context(
        *args: object, **kwargs: object
    ) -> dict[str, str | None]:
        return {
            "owner_id": "someone-else",
            "member_role": "member",
            "member_status": "active",
        }

    monkeypatch.setattr(
        service, "get_event_management_context", fake_get_event_management_context
    )

    with pytest.raises(service.EventForbiddenError):
        await service.list_event_attendees_action(
            fake_session,  # type: ignore[arg-type]
            event_id="22222222-2222-2222-2222-222222222222",
            current_user=current_user,
        )


@pytest.mark.asyncio
async def test_list_event_attendees_action_returns_payment_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_organizer_1",
        email="organizer@communiti.local",
    )
    attendees = [
        EventRegistrationAttendee(
            registration_id="22222222-2222-2222-2222-222222222222",
            event_id="33333333-3333-3333-3333-333333333333",
            user_id="44444444-4444-4444-4444-444444444444",
            display_name="Member One",
            email="member@communiti.local",
            registration_status="confirmed",
            payment_required=True,
            payment_status="paid",
            amount=Decimal("25.00"),
            currency="SAR",
            registered_at=datetime.now(UTC),
        )
    ]

    async def fake_get_event_management_context(
        *args: object, **kwargs: object
    ) -> dict[str, str | None]:
        return {
            "owner_id": current_user.id,
            "member_role": "owner",
            "member_status": "active",
        }

    async def fake_list_event_registration_attendees(
        *args: object, **kwargs: object
    ) -> list[EventRegistrationAttendee]:
        return attendees

    monkeypatch.setattr(
        service, "get_event_management_context", fake_get_event_management_context
    )
    monkeypatch.setattr(
        service,
        "list_event_registration_attendees",
        fake_list_event_registration_attendees,
    )

    result = await service.list_event_attendees_action(
        fake_session,  # type: ignore[arg-type]
        event_id="33333333-3333-3333-3333-333333333333",
        current_user=current_user,
    )

    assert result == attendees
    assert result[0].payment_status == "paid"
