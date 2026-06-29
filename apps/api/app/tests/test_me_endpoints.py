from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.security import CurrentUser
from app.main import app
from app.modules.me import service
from app.modules.me.schemas import MyClubSummary, MyEventSummary


class FakeSession:
    pass


def make_user() -> CurrentUser:
    return CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_member_1",
        email="member@communiti.local",
    )


@pytest.mark.asyncio
async def test_get_my_clubs_uses_current_user_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_user = make_user()
    expected = [
        MyClubSummary(
            id="22222222-2222-2222-2222-222222222222",
            name="COMMUNITI Makers",
            slug="communiti-makers",
            member_count=1,
            visibility="public",
            status="published",
            member_role="owner",
            member_status="active",
        )
    ]
    seen_user_ids: list[str] = []

    async def fake_list_user_clubs(
        *args: object, user_id: str, **kwargs: object
    ) -> list[MyClubSummary]:
        seen_user_ids.append(user_id)
        return expected

    monkeypatch.setattr(service, "list_user_clubs", fake_list_user_clubs)

    result = await service.get_my_clubs(FakeSession(), current_user)  # type: ignore[arg-type]

    assert result == expected
    assert seen_user_ids == [current_user.id]


@pytest.mark.asyncio
async def test_get_my_events_uses_current_user_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_user = make_user()
    expected = [
        MyEventSummary(
            id="33333333-3333-3333-3333-333333333333",
            club_id="22222222-2222-2222-2222-222222222222",
            club_name="COMMUNITI Makers",
            title="Maker Night",
            slug="maker-night",
            event_type="community",
            starts_at=datetime.now(UTC),
            status="draft",
            registered_count=0,
            waitlist_count=0,
            price_amount=Decimal("0"),
            currency="SAR",
        )
    ]
    seen_user_ids: list[str] = []

    async def fake_list_user_managed_events(
        *args: object,
        user_id: str,
        **kwargs: object,
    ) -> list[MyEventSummary]:
        seen_user_ids.append(user_id)
        return expected

    monkeypatch.setattr(
        service, "list_user_managed_events", fake_list_user_managed_events
    )

    result = await service.get_my_events(FakeSession(), current_user)  # type: ignore[arg-type]

    assert result == expected
    assert seen_user_ids == [current_user.id]


def test_openapi_includes_me_routes() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/me/clubs" in paths
    assert "/api/v1/me/events" in paths
    assert "/api/v1/me/registrations" in paths
    assert "/api/v1/me/saved-events" in paths
