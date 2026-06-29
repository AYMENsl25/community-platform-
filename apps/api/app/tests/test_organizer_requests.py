from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.security import CurrentUser
from app.main import app
from app.modules.organizer_requests import service
from app.modules.organizer_requests.schemas import (
    OrganizerRequestCreate,
    OrganizerRequestReview,
    OrganizerRequestState,
)


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def make_user(platform_role: str = "user") -> CurrentUser:
    return CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="seed_user_member_1",
        email="member@communiti.local",
        platform_role=platform_role,
    )


def make_request() -> OrganizerRequestState:
    now = datetime.now(UTC)
    return OrganizerRequestState(
        id="22222222-2222-2222-2222-222222222222",
        user_id="11111111-1111-1111-1111-111111111111",
        user_email="member@communiti.local",
        user_display_name="COMMUNITI Member",
        status="pending",
        reason="I want to create a student community.",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_submit_my_organizer_request_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    expected = make_request()

    async def fake_upsert_user_organizer_request(
        *args: object, **kwargs: object
    ) -> OrganizerRequestState:
        return expected

    monkeypatch.setattr(
        service, "upsert_user_organizer_request", fake_upsert_user_organizer_request
    )

    result = await service.submit_my_organizer_request(
        fake_session,  # type: ignore[arg-type]
        current_user=make_user(),
        payload=OrganizerRequestCreate(reason="I want to create a student community."),
    )

    assert result == expected
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_list_admin_organizer_requests_requires_admin() -> None:
    with pytest.raises(service.AdminRequiredError):
        await service.list_admin_organizer_requests(
            FakeSession(),  # type: ignore[arg-type]
            current_user=make_user(),
            status_filter="pending",
            limit=20,
            offset=0,
        )


@pytest.mark.asyncio
async def test_review_admin_organizer_request_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    expected = make_request().model_copy(update={"status": "approved"})

    async def fake_review_organizer_request(
        *args: object, **kwargs: object
    ) -> OrganizerRequestState:
        return expected

    monkeypatch.setattr(
        service, "review_organizer_request", fake_review_organizer_request
    )

    result = await service.review_admin_organizer_request(
        fake_session,  # type: ignore[arg-type]
        current_user=make_user(platform_role="admin"),
        request_id=expected.id,
        review_status="approved",
        payload=OrganizerRequestReview(admin_note="Approved."),
    )

    assert result.status == "approved"
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


def test_openapi_includes_organizer_request_routes() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/me/organizer-request" in paths
    assert "/api/v1/admin/organizer-requests" in paths
    assert "/api/v1/admin/organizer-requests/{request_id}/approve" in paths
    assert "/api/v1/admin/organizer-requests/{request_id}/reject" in paths
