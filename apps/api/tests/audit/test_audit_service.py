from __future__ import annotations

import ipaddress
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from talaqi.audit.models import AuditEvent, NewAuditEvent
from talaqi.audit.service import AuditService


class FakeAuditRepository:
    def __init__(self) -> None:
        self.recorded: list[NewAuditEvent] = []

    async def create_audit_event(self, event: NewAuditEvent) -> AuditEvent:
        self.recorded.append(event)
        return AuditEvent(
            id=event.id,
            actor_user_id=event.actor_user_id,
            actor_kind=event.actor_kind,
            action=event.action,
            target_type=event.target_type,
            target_id=event.target_id,
            reason=event.reason,
            safe_before=event.safe_before,
            safe_after=event.safe_after,
            request_id=event.request_id,
            ip_prefix=event.ip_prefix,
            created_at=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_audit_service_records_event_with_parsed_ip() -> None:
    repo = FakeAuditRepository()
    service = AuditService(repo)
    user_id = uuid4()
    target_id = uuid4()
    request_id = uuid4()

    event = await service.record(
        actor_user_id=user_id,
        actor_kind="member",
        action="update_club",
        target_type="club",
        target_id=target_id,
        reason="  Admin fix  ",
        safe_before={"status": "draft"},
        safe_after={"status": "published"},
        request_id=request_id,
        ip_prefix="192.168.1.1/32",
    )

    assert len(repo.recorded) == 1
    recorded = repo.recorded[0]
    assert recorded.actor_user_id == user_id
    assert recorded.actor_kind == "member"
    assert recorded.action == "update_club"
    assert recorded.target_type == "club"
    assert recorded.target_id == target_id
    assert recorded.reason == "Admin fix"
    assert recorded.safe_before == {"status": "draft"}
    assert recorded.safe_after == {"status": "published"}
    assert recorded.request_id == request_id
    assert recorded.ip_prefix == ipaddress.ip_network("192.168.1.1/32")
    assert event.created_at is not None


@pytest.mark.asyncio
async def test_audit_service_snapshots_safe_metadata() -> None:
    repo = FakeAuditRepository()
    service = AuditService(repo)
    before: dict[str, Any] = {"status": "draft", "fields": ["name"]}

    await service.record(
        actor_user_id=uuid4(),
        actor_kind="organizer",
        action="club.update",
        target_type="club",
        target_id=uuid4(),
        safe_before=before,
    )
    before["status"] = "suspended"
    before["fields"].append("private_email")

    assert repo.recorded[0].safe_before == {"status": "draft", "fields": ["name"]}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unsafe_metadata",
    [
        {"password": "not-safe"},  # pragma: allowlist secret
        {"nested": {"refresh_token": "not-safe"}},  # pragma: allowlist secret
        {"items": [{"authorization": "not-safe"}]},  # pragma: allowlist secret
        {"profile": {"email": "private@example.test"}},
    ],
)
async def test_audit_service_rejects_sensitive_metadata(
    unsafe_metadata: dict[str, Any],
) -> None:
    service = AuditService(FakeAuditRepository())

    with pytest.raises(ValueError, match="sensitive"):
        await service.record(
            actor_user_id=uuid4(),
            actor_kind="member",
            action="club.update",
            target_type="club",
            safe_after=unsafe_metadata,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"action": "Club Update"}, "action"),
        ({"target_type": "club.event"}, "target_type"),
        ({"actor_kind": "system", "actor_user_id": uuid4()}, "system"),
        ({"actor_kind": "admin", "actor_user_id": None}, "actor_user_id"),
        ({"safe_after": {"created_at": datetime.now(UTC)}}, "JSON"),
    ],
)
async def test_audit_service_rejects_invalid_event_shape(
    overrides: dict[str, Any],
    message: str,
) -> None:
    values: dict[str, Any] = {
        "actor_user_id": uuid4(),
        "actor_kind": "member",
        "action": "club.update",
        "target_type": "club",
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=message):
        await AuditService(FakeAuditRepository()).record(**values)


def test_audit_event_is_application_immutable() -> None:
    event = AuditEvent(
        id=uuid4(),
        actor_user_id=None,
        actor_kind="system",
        action="system.start",
        target_type="service",
        target_id=None,
        reason=None,
        safe_before=None,
        safe_after={"state": "ready"},
        request_id=uuid4(),
        ip_prefix=None,
        created_at=datetime.now(UTC),
    )

    with pytest.raises(FrozenInstanceError):
        event.action = "system.stop"  # type: ignore[misc]
