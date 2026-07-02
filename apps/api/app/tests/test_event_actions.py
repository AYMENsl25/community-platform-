from datetime import UTC, datetime

import pytest

from app.core.security import CurrentUser
from app.modules.events import service
from app.modules.events.schemas import EventRegistrationState, SavedEventState


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@pytest.mark.asyncio
async def test_register_for_event_action_commits_database_function_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_member_1",
        email="member@communiti.local",
    )
    registration = EventRegistrationState(
        id="22222222-2222-2222-2222-222222222222",
        event_id="33333333-3333-3333-3333-333333333333",
        user_id=current_user.id,
        status="confirmed",
        registered_at=datetime.now(UTC),
    )

    async def fake_get_event_by_id(*args: object, **kwargs: object) -> object:
        return object()

    async def fake_register_user_for_event(
        *args: object, **kwargs: object
    ) -> EventRegistrationState:
        return registration

    async def fake_apply_event_registration_payment_state(
        *args: object, **kwargs: object
    ) -> EventRegistrationState:
        return registration

    monkeypatch.setattr(service, "get_event_by_id", fake_get_event_by_id)
    monkeypatch.setattr(
        service, "register_user_for_event", fake_register_user_for_event
    )
    monkeypatch.setattr(
        service,
        "apply_event_registration_payment_state",
        fake_apply_event_registration_payment_state,
    )
    result = await service.register_for_event_action(
        fake_session,  # type: ignore[arg-type]
        event_id=registration.event_id,
        current_user=current_user,
    )

    assert result == registration
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_save_event_action_is_idempotent_from_service_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_member_1",
        email="member@communiti.local",
    )
    saved_event = SavedEventState(
        user_id=current_user.id,
        event_id="33333333-3333-3333-3333-333333333333",
        saved=True,
        created_at=datetime.now(UTC),
    )

    async def fake_get_event_by_id(*args: object, **kwargs: object) -> object:
        return object()

    async def fake_save_event_for_user(
        *args: object, **kwargs: object
    ) -> SavedEventState:
        return saved_event

    monkeypatch.setattr(service, "get_event_by_id", fake_get_event_by_id)
    monkeypatch.setattr(service, "save_event_for_user", fake_save_event_for_user)

    result = await service.save_event_action(
        fake_session,  # type: ignore[arg-type]
        event_id=saved_event.event_id,
        current_user=current_user,
    )

    assert result == saved_event
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_cancel_registration_action_rolls_back_when_registration_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_member_1",
        email="member@communiti.local",
    )

    async def fake_get_event_by_id(*args: object, **kwargs: object) -> object:
        return object()

    async def fake_cancel_user_event_registration(
        *args: object, **kwargs: object
    ) -> None:
        return None

    async def fake_get_user_event_registration(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(service, "get_event_by_id", fake_get_event_by_id)
    monkeypatch.setattr(
        service, "cancel_user_event_registration", fake_cancel_user_event_registration
    )
    monkeypatch.setattr(
        service, "get_user_event_registration", fake_get_user_event_registration
    )

    with pytest.raises(service.EventRegistrationNotFoundError):
        await service.cancel_registration_action(
            fake_session,  # type: ignore[arg-type]
            event_id="33333333-3333-3333-3333-333333333333",
            current_user=current_user,
        )

    assert fake_session.committed is False
    assert fake_session.rolled_back is True
