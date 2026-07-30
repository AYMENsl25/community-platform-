from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from talaqi.events.models import Event, EventPatch, EventReferences, NewEvent
from talaqi.events.service import EventService
from talaqi.identity.models import AuthPrincipal
from talaqi.platform import ApiError
from talaqi.profiles.schemas import Capabilities
from talaqi.regions.models import RegionPolicy

NOW = datetime(2026, 8, 1, 12, tzinfo=UTC)
USER_ID = UUID("01900000-0000-7000-8000-000000000311")
SESSION_ID = UUID("01900000-0000-7000-8000-000000000312")
CLUB_ID = UUID("01900000-0000-7000-8000-000000000313")
REQUEST_ID = UUID("01900000-0000-7000-8000-000000000314")


def principal(*, status: str = "active") -> AuthPrincipal:
    return AuthPrincipal(USER_ID, SESSION_ID, True, status, False)  # type: ignore[arg-type]


def capabilities(*, independent: bool = True, save: bool = True) -> Capabilities:
    return Capabilities(
        create_club=False,
        create_independent_event=independent,
        save_event=save,
        register_event=save,
        access_admin=False,
        blockers=() if independent and save else ("independent_event_limit_reached",),
    )


def region_policy() -> RegionPolicy:
    return RegionPolicy(
        country_code="TR",
        default_locale="tr",
        default_currency="TRY",
        allowed_registration_methods=("free", "cash_organizer_confirmed"),
        cash_default_minutes=1440,
        cash_bounds=(120, 4320),
        cancellation_default_minutes=1440,
        cancellation_bounds=(0, 10080),
        club_limit=1,
        independent_event_limit=3,
        exact_venue_public_by_default=False,
        revision=1,
    )


def new_event(
    *, ownership_type: str = "independent", club_id: UUID | None = None, publish: bool = True
) -> NewEvent:
    return NewEvent(
        ownership_type=ownership_type,  # type: ignore[arg-type]
        club_id=club_id,
        title="Talaqi Event",
        description="A complete event description.",
        category_slug="sports",
        country_code="TR",
        city_slug="istanbul",
        start_at=NOW + timedelta(days=2),
        end_at=NOW + timedelta(days=2, hours=2),
        time_zone="Europe/Istanbul",
        visibility="public",
        registration_method="free",
        cancellation_cutoff_minutes=None,
        publish=publish,
    )


class FakeRepository:
    def __init__(self) -> None:
        self.events: dict[UUID, Event] = {}
        self.locked: list[UUID] = []
        self.revoked_invite_tokens: list[tuple[UUID, datetime]] = []

    async def lock_creation(self, user_id: UUID) -> None:
        self.locked.append(user_id)

    async def resolve_references(self, **_: object) -> EventReferences:
        return EventReferences(
            category_id=UUID("01900000-0000-7000-8000-000000000321"),
            country_id=UUID("01900000-0000-7000-8000-000000000322"),
            city_id=UUID("01900000-0000-7000-8000-000000000323"),
        )

    async def create(self, event: Event, *, references: EventReferences) -> Event:
        del references
        self.events[event.id] = event
        return event

    async def get(self, event_id: UUID, *, for_update: bool = False) -> Event | None:
        del for_update
        return self.events.get(event_id)

    async def update(
        self, event: Event, *, references: EventReferences, expected_revision: int
    ) -> Event:
        del references
        current = self.events[event.id]
        if current.revision != expected_revision:
            raise ApiError(code="stale_revision", message_key="errors.conflict", status_code=409)
        updated = replace(event, revision=expected_revision + 1, updated_at=NOW)
        self.events[event.id] = updated
        return updated

    async def transition(
        self, event_id: UUID, *, expected_revision: int, status: str, occurred_at: datetime
    ) -> Event:
        event = self.events[event_id]
        values: dict[str, object] = {"status": status, "revision": expected_revision + 1}
        values[f"{status}_at"] = occurred_at
        updated = replace(event, **values)
        self.events[event_id] = updated
        return updated

    async def revoke_invite_tokens(self, event_id: UUID, *, occurred_at: datetime) -> None:
        self.revoked_invite_tokens.append((event_id, occurred_at))

    async def delete_draft(self, event_id: UUID, *, expected_revision: int) -> bool:
        event = self.events[event_id]
        if event.status != "draft" or event.revision != expected_revision:
            return False
        del self.events[event_id]
        return True


@dataclass
class FakeEligibility:
    value: Capabilities

    async def evaluate(self, principal: AuthPrincipal) -> Capabilities:
        return self.value


class FakeRegions:
    async def get(self, country_code: str) -> RegionPolicy:
        return region_policy()


class FakeClubs:
    def __init__(self) -> None:
        self.calls: list[UUID] = []

    async def require_event_manager(
        self,
        principal: AuthPrincipal,
        club_id: UUID,
        *,
        for_update: bool = False,
    ) -> None:
        del principal, for_update
        self.calls.append(club_id)


class FakeMedia:
    async def require_verified_owned(self, asset_id: UUID, owner_user_id: UUID) -> object:
        return {"asset_id": asset_id, "owner_user_id": owner_user_id}


class FakeAudit:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def record(self, **values: Any) -> object:
        self.actions.append(values["action"])
        return values


def service(repo: FakeRepository, *, allowed: bool = True) -> EventService:
    return EventService(
        repo,
        FakeEligibility(capabilities(independent=allowed, save=allowed)),
        FakeRegions(),
        FakeClubs(),
        FakeMedia(),
        FakeAudit(),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_create_applies_policy_defaults_and_publishes() -> None:
    repo = FakeRepository()
    audit = FakeAudit()
    events = EventService(
        repo,
        FakeEligibility(capabilities()),
        FakeRegions(),
        FakeClubs(),
        FakeMedia(),
        audit,  # type: ignore[arg-type]
    )
    created = await events.create(principal(), new_event(), request_id=REQUEST_ID, now=NOW)
    assert created.status == "published"
    assert created.owner_user_id == USER_ID
    assert created.club_id is None
    assert created.capacity is None
    assert created.cancellation_cutoff_minutes == 1440
    assert repo.locked == [USER_ID]
    assert audit.actions == ["event.create", "event.publish"]


@pytest.mark.asyncio
async def test_independent_limit_and_club_manager_policy_are_enforced() -> None:
    repo = FakeRepository()
    with pytest.raises(ApiError, match="independent_event_limit_reached"):
        await service(repo, allowed=False).create(
            principal(), new_event(), request_id=REQUEST_ID, now=NOW
        )

    clubs = FakeClubs()
    events = EventService(
        repo,
        FakeEligibility(capabilities()),
        FakeRegions(),
        clubs,
        FakeMedia(),
        FakeAudit(),  # type: ignore[arg-type]
    )
    await events.create(
        principal(),
        new_event(ownership_type="club", club_id=CLUB_ID, publish=False),
        request_id=REQUEST_ID,
        now=NOW,
    )
    assert clubs.calls == [CLUB_ID]


@pytest.mark.asyncio
async def test_running_published_event_remains_editable() -> None:
    repo = FakeRepository()
    events = service(repo)
    published = await events.create(principal(), new_event(), request_id=REQUEST_ID, now=NOW)
    repo.events[published.id] = replace(
        published,
        start_at=NOW - timedelta(hours=1),
        end_at=NOW + timedelta(hours=1),
    )
    updated = await events.update(
        principal(),
        published.id,
        EventPatch(
            revision=1,
            changed_fields=frozenset({"title"}),
            title="Running event update",
        ),
        request_id=REQUEST_ID,
        now=NOW,
    )

    assert updated.title == "Running event update"
    assert updated.status == "published"
    assert updated.revision == 2


@pytest.mark.asyncio
async def test_upcoming_published_event_cannot_be_rescheduled_into_the_past() -> None:
    repo = FakeRepository()
    events = service(repo)
    published = await events.create(principal(), new_event(), request_id=REQUEST_ID, now=NOW)

    with pytest.raises(ApiError, match="event_not_publishable"):
        await events.update(
            principal(),
            published.id,
            EventPatch(
                revision=1,
                changed_fields=frozenset({"start_at"}),
                start_at=NOW - timedelta(minutes=1),
            ),
            request_id=REQUEST_ID,
            now=NOW,
        )


@pytest.mark.asyncio
async def test_cancel_complete_delete_and_duplicate_have_safe_lifecycle() -> None:
    repo = FakeRepository()
    events = service(repo)
    published = await events.create(principal(), new_event(), request_id=REQUEST_ID, now=NOW)
    cancelled = await events.cancel(
        principal(), published.id, revision=1, request_id=REQUEST_ID, now=NOW
    )
    assert cancelled.status == "cancelled"
    with pytest.raises(ApiError, match="invalid_event_transition"):
        await events.complete(principal(), published.id, revision=2, request_id=REQUEST_ID, now=NOW)

    duplicate = await events.duplicate(principal(), published.id, request_id=REQUEST_ID, now=NOW)
    assert duplicate.id != published.id
    assert duplicate.status == "draft"
    assert duplicate.revision == 1
    assert duplicate.published_at is None

    await events.delete_draft(principal(), duplicate.id, revision=1, request_id=REQUEST_ID)
    assert duplicate.id not in repo.events
