from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from talaqi.audit import AuditRepository, AuditService


@pytest.mark.asyncio
async def test_repository_records_database_timestamp_and_complete_shape(
    audit_session: AsyncSession,
) -> None:
    event = await AuditService(AuditRepository(audit_session)).record(
        actor_user_id=None,
        actor_kind="system",
        action="system.health_check",
        target_type="api",
        target_id=None,
        reason="readiness transition",
        safe_before={"ready": False},
        safe_after={"ready": True},
        request_id=uuid4(),
        ip_prefix="10.20.30.0/24",
    )

    stored = (
        (
            await audit_session.execute(
                text(
                    """
                    SELECT actor_kind, action, target_type, reason, safe_before, safe_after,
                           request_id, ip_prefix::text, created_at
                    FROM talaqi.audit_events
                    WHERE id = :event_id
                    """
                ),
                {"event_id": event.id},
            )
        )
        .mappings()
        .one()
    )
    assert stored["actor_kind"] == "system"
    assert stored["action"] == "system.health_check"
    assert stored["target_type"] == "api"
    assert stored["reason"] == "readiness transition"
    assert stored["safe_before"] == {"ready": False}
    assert stored["safe_after"] == {"ready": True}
    assert stored["request_id"] == event.request_id
    assert stored["ip_prefix"] == "10.20.30.0/24"
    assert stored["created_at"] == event.created_at


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE talaqi.audit_events SET reason = 'tampered' WHERE id = :event_id",
        "DELETE FROM talaqi.audit_events WHERE id = :event_id",
    ],
)
async def test_database_rejects_audit_update_and_delete(
    audit_session: AsyncSession,
    statement: str,
) -> None:
    event = await AuditService(AuditRepository(audit_session)).record(
        actor_user_id=None,
        actor_kind="system",
        action="system.health_check",
        target_type="api",
    )
    savepoint = await audit_session.begin_nested()
    with pytest.raises(DBAPIError, match="append-only"):
        await audit_session.execute(text(statement), {"event_id": event.id})
    await savepoint.rollback()

    count = (
        await audit_session.execute(
            text("SELECT count(*) FROM talaqi.audit_events WHERE id = :event_id"),
            {"event_id": event.id},
        )
    ).scalar_one()
    assert count == 1


def test_repository_exposes_append_only_interface() -> None:
    assert not hasattr(AuditRepository, "update_audit_event")
    assert not hasattr(AuditRepository, "delete_audit_event")
