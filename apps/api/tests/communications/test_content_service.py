from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import pytest
from talaqi.communications.content_schemas import ClubAnnouncementRequest
from talaqi.communications.content_service import OrganizerCommunicationsService
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError

USER_ID = UUID("01900000-0000-7000-8000-000000000411")
SESSION_ID = UUID("01900000-0000-7000-8000-000000000412")
CLUB_ID = UUID("01900000-0000-7000-8000-000000000413")


class FakeRepository:
    def __init__(self) -> None:
        self.created = False

    async def create_club_announcement(self, **_: object) -> object:
        self.created = True
        raise AssertionError("disabled feature must not write")


class FakeClubAccess:
    def __init__(self) -> None:
        self.authorized = False

    async def require_event_manager(self, *_: object, **__: object) -> None:
        self.authorized = True


class FakeEventAccess:
    pass


@dataclass
class DisabledFlags:
    async def require_enabled(self, key: str) -> None:
        assert key == "features.organizer_announcements_enabled"
        raise ApiError(
            code="feature_disabled",
            message_key="errors.feature_disabled",
            status_code=403,
        )


@pytest.mark.asyncio
async def test_disabled_announcement_flag_checks_object_access_before_blocking_writes() -> None:
    repository = FakeRepository()
    access = FakeClubAccess()
    service = OrganizerCommunicationsService(
        repository,  # type: ignore[arg-type]
        access,  # type: ignore[arg-type]
        FakeEventAccess(),  # type: ignore[arg-type]
        DisabledFlags(),  # type: ignore[arg-type]
    )
    principal = AuthPrincipal(USER_ID, SESSION_ID, True, "active", False)
    body = ClubAnnouncementRequest(
        title="Operational notice",
        body="A sufficiently detailed organizer announcement.",
        audience="all_members",
    )
    with pytest.raises(ApiError) as error:
        await service.create_club(principal, CLUB_ID, body, "announcement-idempotency-key")
    assert error.value.code == "feature_disabled"
    assert access.authorized is True
    assert repository.created is False
