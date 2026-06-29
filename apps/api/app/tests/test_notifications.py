from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.security import CurrentUser
from app.main import app
from app.modules.me import service
from app.modules.me.schemas import MyNotificationSummary, NotificationReadState


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


@pytest.mark.asyncio
async def test_get_my_notifications_uses_current_user_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_user = make_user()
    expected = [
        MyNotificationSummary(
            id="22222222-2222-2222-2222-222222222222",
            kind="system",
            title="Welcome",
            body="Welcome to COMMUNITI.",
            created_at=datetime.now(UTC),
            is_read=False,
        )
    ]
    seen: list[tuple[str, int, int, bool]] = []

    async def fake_list_user_notifications(
        *args: object,
        user_id: str,
        limit: int,
        offset: int,
        unread_only: bool,
        **kwargs: object,
    ) -> list[MyNotificationSummary]:
        seen.append((user_id, limit, offset, unread_only))
        return expected

    monkeypatch.setattr(
        service, "list_user_notifications", fake_list_user_notifications
    )

    result = await service.get_my_notifications(
        FakeSession(),  # type: ignore[arg-type]
        current_user,
        limit=10,
        offset=5,
        unread_only=True,
    )

    assert result == expected
    assert seen == [(current_user.id, 10, 5, True)]


@pytest.mark.asyncio
async def test_mark_my_notification_read_commits_owned_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = make_user()
    state = NotificationReadState(
        id="22222222-2222-2222-2222-222222222222",
        read_at=datetime.now(UTC),
    )

    async def fake_mark_user_notification_read(
        *args: object, **kwargs: object
    ) -> NotificationReadState:
        return state

    monkeypatch.setattr(
        service, "mark_user_notification_read", fake_mark_user_notification_read
    )

    result = await service.mark_my_notification_read(
        fake_session,  # type: ignore[arg-type]
        current_user,
        notification_id=state.id,
    )

    assert result == state
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_mark_my_notification_read_rolls_back_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = make_user()

    async def fake_mark_user_notification_read(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        service, "mark_user_notification_read", fake_mark_user_notification_read
    )

    with pytest.raises(service.NotificationNotFoundError):
        await service.mark_my_notification_read(
            fake_session,  # type: ignore[arg-type]
            current_user,
            notification_id="22222222-2222-2222-2222-222222222222",
        )

    assert fake_session.committed is False
    assert fake_session.rolled_back is True


def test_openapi_includes_notification_routes() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/me/notifications" in paths
    assert "/api/v1/me/notifications/read-all" in paths
    assert "/api/v1/me/notifications/{notification_id}/read" in paths
