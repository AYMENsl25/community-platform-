from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.security import CurrentUser
from app.main import app
from app.modules.recommendations import service
from app.modules.recommendations.schemas import (
    RecommendationEventCreate,
    RecommendationEventState,
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


@pytest.mark.asyncio
async def test_track_recommendation_event_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = make_user()
    payload = RecommendationEventCreate(
        event_id="22222222-2222-2222-2222-222222222222",
        source="hybrid",
        score=Decimal("0.75"),
        action="click",
    )
    state = RecommendationEventState(
        id="33333333-3333-3333-3333-333333333333",
        user_id=current_user.id,
        event_id=payload.event_id,
        source=payload.source,
        score=payload.score,
        action=payload.action,
        created_at=datetime.now(UTC),
    )

    async def fake_event_exists(*args: object, **kwargs: object) -> bool:
        return True

    async def fake_insert_recommendation_event(
        *args: object, **kwargs: object
    ) -> RecommendationEventState:
        return state

    monkeypatch.setattr(service, "event_exists", fake_event_exists)
    monkeypatch.setattr(
        service, "insert_recommendation_event", fake_insert_recommendation_event
    )

    result = await service.track_recommendation_event(
        fake_session,  # type: ignore[arg-type]
        current_user=current_user,
        payload=payload,
    )

    assert result == state
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_track_recommendation_event_rejects_missing_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    current_user = make_user()

    async def fake_event_exists(*args: object, **kwargs: object) -> bool:
        return False

    monkeypatch.setattr(service, "event_exists", fake_event_exists)

    with pytest.raises(service.RecommendationEventNotFoundError):
        await service.track_recommendation_event(
            fake_session,  # type: ignore[arg-type]
            current_user=current_user,
            payload=RecommendationEventCreate(
                event_id="22222222-2222-2222-2222-222222222222"
            ),
        )

    assert fake_session.committed is False
    assert fake_session.rolled_back is False


def test_openapi_includes_recommendation_event_route() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/recommendations/events" in response.json()["paths"]
