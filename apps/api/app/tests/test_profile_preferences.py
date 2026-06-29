import pytest
from fastapi.testclient import TestClient

from app.core.security import CurrentUser
from app.main import app
from app.modules.me import service
from app.modules.me.schemas import (
    MyPreferences,
    MyPreferencesUpdate,
    MyProfile,
    MyProfileUpdate,
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


def make_profile(current_user: CurrentUser) -> MyProfile:
    return MyProfile(
        id=current_user.id,
        clerk_user_id=current_user.clerk_user_id,
        email=current_user.email,
        username="seed_member",
        display_name="COMMUNITI Member",
        city="Riyadh",
        country="Saudi Arabia",
        platform_role="user",
        is_onboarded=True,
    )


@pytest.mark.asyncio
async def test_update_my_profile_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = FakeSession()
    current_user = make_user()
    profile = make_profile(current_user)

    async def fake_update_user_profile(*args: object, **kwargs: object) -> MyProfile:
        return profile

    monkeypatch.setattr(service, "update_user_profile", fake_update_user_profile)

    result = await service.update_my_profile(
        fake_session,  # type: ignore[arg-type]
        current_user,
        payload=MyProfileUpdate(display_name="COMMUNITI Member"),
    )

    assert result == profile
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_update_my_preferences_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = FakeSession()
    current_user = make_user()
    preferences = MyPreferences(
        interest_categories=["Technology"],
        interest_tags=["networking"],
        preferred_city="Riyadh",
        max_distance_km=25,
        notify_email=True,
        notify_push=False,
    )

    async def fake_update_user_preferences(
        *args: object, **kwargs: object
    ) -> MyPreferences:
        return preferences

    monkeypatch.setattr(
        service, "update_user_preferences", fake_update_user_preferences
    )

    result = await service.update_my_preferences(
        fake_session,  # type: ignore[arg-type]
        current_user,
        payload=MyPreferencesUpdate(notify_push=False),
    )

    assert result == preferences
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


def test_openapi_includes_profile_and_preferences_routes() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/me/profile" in paths
    assert "/api/v1/me/preferences" in paths
