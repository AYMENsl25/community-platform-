from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from clubs.test_routes import AuthenticatedUser, app_for, create_user
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from talaqi.db.identifiers import generate_uuid7
from talaqi.discovery.fixtures import (
    PUBLIC_CLUB_IDS,
    PUBLIC_EVENT_IDS,
    seed_discovery_fixtures,
)
from talaqi.moderation.models import REPORT_CATEGORIES, ModerationCase, ModerationTarget
from talaqi.moderation.repository import ModerationRepository
from talaqi.moderation.service import acknowledgement_deadline, capabilities, response_breached


async def make_admin(engine: AsyncEngine, *, mfa: bool) -> AuthenticatedUser:
    user = await create_user(engine)
    async with engine.begin() as connection:
        await connection.execute(
            text("UPDATE talaqi.users SET is_platform_admin = true WHERE id = :id"),
            {"id": user.user_id},
        )
        if mfa:
            await connection.execute(
                text(
                    """
                    INSERT INTO talaqi.user_mfa_factors (
                        id, user_id, factor_type, secret_ciphertext, verified_at
                    ) VALUES (:id, :user_id, 'totp', :secret, clock_timestamp())
                    """
                ),
                {"id": generate_uuid7(), "user_id": user.user_id, "secret": b"test"},
            )
    return user


async def make_case(
    engine: AsyncEngine,
    target_id: UUID,
    *,
    target_type: str = "user",
    category: str = "safety",
    priority: str = "emergency",
    description: str = "Private report evidence must not leave the API.",
    created_at: datetime | None = None,
) -> UUID:
    case_id = generate_uuid7()
    target_column = {
        "user": "target_user_id",
        "club": "target_club_id",
        "event": "target_event_id",
    }[target_type]
    async with engine.begin() as connection:
        await connection.execute(
            text(
                f"""
                INSERT INTO talaqi.moderation_cases (
                    id, target_type, {target_column}, category,
                    description, priority, created_at
                ) VALUES (
                    :id, CAST(:target_type AS talaqi.moderation_target_type),
                    :target_id, :category, :description,
                    CAST(:priority AS talaqi.moderation_priority),
                    coalesce(CAST(:created_at AS timestamptz), clock_timestamp())
                )
                """
            ),
            {
                "id": case_id,
                "target_type": target_type,
                "target_id": target_id,
                "category": category,
                "priority": priority,
                "description": description,
                "created_at": created_at,
            },
        )
    return case_id


@pytest.mark.asyncio
async def test_locked_user_target_only_locks_primary_table(
    moderation_engine: AsyncEngine,
) -> None:
    user = await create_user(moderation_engine)
    async with AsyncSession(moderation_engine) as session, session.begin():
        target = await ModerationRepository(session).get_target(
            "user", user.user_id, for_update=True
        )
    assert target is not None
    assert target.id == user.user_id
    assert target.secondary_label is not None
    assert "@" not in target.secondary_label


def test_launch_report_categories_are_exactly_the_approved_set() -> None:
    assert REPORT_CATEGORIES == (
        "safety",
        "harassment",
        "fraud",
        "illegal_content",
        "privacy",
        "spam",
        "other",
    )


def _sla_case(
    *,
    priority: str,
    created_at: datetime,
    acknowledged_at: datetime | None = None,
) -> ModerationCase:
    identifier = generate_uuid7()
    return ModerationCase(
        id=identifier,
        reporter_user_id=None,
        target_type="user",
        target_id=identifier,
        category="spam",
        description="Private evidence stays outside admin queue responses.",
        status="open",
        priority=priority,  # type: ignore[arg-type]
        assigned_admin_user_id=None,
        resolution_reason=None,
        acknowledged_at=acknowledged_at,
        resolved_at=None,
        created_at=created_at,
        updated_at=created_at,
    )


def test_moderation_acknowledgement_deadlines_and_breach_indicators() -> None:
    friday = datetime(2026, 8, 14, 12, tzinfo=UTC)
    high = _sla_case(priority="high", created_at=friday)
    emergency = _sla_case(priority="emergency", created_at=friday)
    standard = _sla_case(priority="standard", created_at=friday)

    assert acknowledgement_deadline(high) == datetime(2026, 8, 14, 16, tzinfo=UTC)
    assert acknowledgement_deadline(emergency) == datetime(2026, 8, 14, 16, tzinfo=UTC)
    assert acknowledgement_deadline(standard) == datetime(2026, 8, 18, 12, tzinfo=UTC)
    assert response_breached(high, now=datetime(2026, 8, 14, 16, 0, 1, tzinfo=UTC)) is True
    assert (
        response_breached(
            _sla_case(
                priority="high",
                created_at=friday,
                acknowledged_at=datetime(2026, 8, 14, 15, tzinfo=UTC),
            ),
            now=datetime(2026, 8, 14, 20, tzinfo=UTC),
        )
        is False
    )
    assert (
        response_breached(
            _sla_case(
                priority="standard",
                created_at=friday,
                acknowledged_at=datetime(2026, 8, 18, 12, 0, 1, tzinfo=UTC),
            ),
            now=datetime(2026, 8, 18, 12, 0, 1, tzinfo=UTC),
        )
        is True
    )


@pytest.mark.asyncio
async def test_safety_cases_must_enter_the_emergency_priority_queue(
    moderation_engine: AsyncEngine,
) -> None:
    target = await create_user(moderation_engine)

    with pytest.raises(DBAPIError, match="ck_moderation_safety_priority"):
        await make_case(
            moderation_engine,
            target.user_id,
            category="safety",
            priority="standard",
        )


@pytest.mark.asyncio
async def test_case_queue_orders_priority_first_and_cursor_stays_stable(
    moderation_engine: AsyncEngine,
) -> None:
    admin = await make_admin(moderation_engine, mfa=False)
    emergency_target = await create_user(moderation_engine)
    high_target = await create_user(moderation_engine)
    second_high_target = await create_user(moderation_engine)
    standard_target = await create_user(moderation_engine)
    emergency_id = await make_case(
        moderation_engine,
        emergency_target.user_id,
        created_at=datetime(2099, 1, 1, 1, tzinfo=UTC),
    )
    high_id = await make_case(
        moderation_engine,
        high_target.user_id,
        category="fraud",
        priority="high",
        created_at=datetime(2099, 1, 1, 3, tzinfo=UTC),
    )
    second_high_id = await make_case(
        moderation_engine,
        second_high_target.user_id,
        category="privacy",
        priority="high",
        created_at=datetime(2099, 1, 1, 2, tzinfo=UTC),
    )
    standard_id = await make_case(
        moderation_engine,
        standard_target.user_id,
        category="spam",
        priority="standard",
        created_at=datetime(2099, 1, 1, 4, tzinfo=UTC),
    )

    async with AsyncSession(moderation_engine) as session:
        ordered = await ModerationRepository(session).list_cases(
            status=None,
            priority=None,
            target_type=None,
            limit=1_000,
        )
    positions = {case.id: index for index, case in enumerate(ordered)}
    assert positions[emergency_id] < positions[high_id] < positions[standard_id]

    app = app_for(moderation_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        first = await client.get(
            "/api/v1/admin/moderation/cases",
            params={"priority": "high", "limit": 1},
            headers=admin.headers(),
        )
        assert first.status_code == 200
        assert first.json()["items"][0]["id"] == str(high_id)
        cursor = first.json()["next_cursor"]
        assert cursor is not None
        second = await client.get(
            "/api/v1/admin/moderation/cases",
            params={"priority": "high", "limit": 1, "cursor": cursor},
            headers=admin.headers(),
        )
    assert second.status_code == 200
    assert second.json()["items"][0]["id"] == str(second_high_id)


def test_action_capabilities_are_an_explicit_target_state_matrix() -> None:
    identifier = generate_uuid7()
    assert capabilities(ModerationTarget("user", identifier, "u", None, "active")) == ("suspend",)
    assert capabilities(ModerationTarget("club", identifier, "c", None, "published")) == (
        "suspend",
        "unpublish",
    )
    assert capabilities(ModerationTarget("event", identifier, "e", None, "published")) == (
        "suspend",
    )
    assert capabilities(ModerationTarget("event", identifier, "e", None, "draft")) == ()


@pytest.mark.asyncio
async def test_admin_reads_are_private_and_report_evidence_is_not_serialized(
    moderation_engine: AsyncEngine,
) -> None:
    admin = await make_admin(moderation_engine, mfa=False)
    member = await create_user(moderation_engine)
    target = await create_user(moderation_engine)
    case_id = await make_case(moderation_engine, target.user_id)
    app = app_for(moderation_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        denied = await client.get("/api/v1/admin/moderation/cases", headers=member.headers())
        detail = await client.get(
            f"/api/v1/admin/moderation/cases/{case_id}", headers=admin.headers()
        )
        invalid = await client.get(
            "/api/v1/admin/moderation/cases?status=invalid", headers=admin.headers()
        )
    assert denied.status_code == 403
    assert invalid.status_code == 422
    assert detail.status_code == 200, detail.text
    assert detail.headers["cache-control"] == "private, no-store"
    serialized = detail.text
    assert "Private report evidence" not in serialized
    assert "reporter_user_id" not in serialized
    assert "@example.test" not in serialized
    assert detail.json()["case"]["emergency_notice"] is True
    assert detail.json()["case"]["response_due_at"] is not None
    assert detail.json()["case"]["response_breached"] is False
    assert detail.json()["case"]["available_actions"] == ["suspend"]


@pytest.mark.asyncio
async def test_action_requires_mfa_and_is_idempotent_per_case(
    moderation_engine: AsyncEngine,
) -> None:
    no_mfa = await make_admin(moderation_engine, mfa=False)
    admin = await make_admin(moderation_engine, mfa=True)
    first_target = await create_user(moderation_engine)
    second_target = await create_user(moderation_engine)
    first_case = await make_case(moderation_engine, first_target.user_id)
    second_case = await make_case(moderation_engine, second_target.user_id)
    body = {"action": "suspend", "reason": "Immediate safety review"}
    key = f"moderation-{generate_uuid7()}"
    app = app_for(moderation_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        denied = await client.post(
            f"/api/v1/admin/moderation/cases/{first_case}/actions",
            json=body,
            headers=no_mfa.headers(idempotency_key=f"no-mfa-{generate_uuid7()}"),
        )
        member = await create_user(moderation_engine)
        non_admin = await client.post(
            f"/api/v1/admin/moderation/cases/{first_case}/actions",
            json=body,
            headers=member.headers(idempotency_key=f"member-{generate_uuid7()}"),
        )
        missing_csrf = await client.post(
            f"/api/v1/admin/moderation/cases/{first_case}/actions",
            json=body,
            headers={
                "cookie": admin.cookie,
                "Idempotency-Key": f"missing-csrf-{generate_uuid7()}",
            },
        )
        first = await client.post(
            f"/api/v1/admin/moderation/cases/{first_case}/actions",
            json=body,
            headers=admin.headers(idempotency_key=key),
        )
        replay = await client.post(
            f"/api/v1/admin/moderation/cases/{first_case}/actions",
            json=body,
            headers=admin.headers(idempotency_key=key),
        )
        second = await client.post(
            f"/api/v1/admin/moderation/cases/{second_case}/actions",
            json=body,
            headers=admin.headers(idempotency_key=key),
        )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "admin_mfa_required"
    assert non_admin.status_code == missing_csrf.status_code == 403
    assert first.status_code == replay.status_code == second.status_code == 200
    assert first.json() == replay.json()
    assert first.json()["case"]["id"] == str(first_case)
    assert second.json()["case"]["id"] == str(second_case)
    assert first.json()["case"]["available_actions"] == ["restore"]
    assert len(first.json()["events"]) == 1
    async with moderation_engine.connect() as connection:
        event_count = (
            await connection.execute(
                text(
                    "SELECT count(*) FROM talaqi.moderation_case_events "
                    "WHERE moderation_case_id = :case_id"
                ),
                {"case_id": first_case},
            )
        ).scalar_one()
        audit_count = (
            await connection.execute(
                text(
                    "SELECT count(*) FROM talaqi.audit_events "
                    "WHERE target_type = 'user' AND target_id = :target_id "
                    "AND action = 'moderation.target.suspend'"
                ),
                {"target_id": first_target.user_id},
            )
        ).scalar_one()
        notification_event = (
            await connection.execute(
                text(
                    """
                    SELECT event_type, payload ->> 'recipient_user_id'
                    FROM talaqi.outbox_events
                    WHERE aggregate_id = :case_id
                    """
                ),
                {"case_id": first_case},
            )
        ).one()
    assert event_count == audit_count == 1
    assert notification_event == ("moderation.action_taken", str(first_target.user_id))


@pytest.mark.asyncio
async def test_action_rejects_cross_target_fields_and_invalid_reason_without_changes(
    moderation_engine: AsyncEngine,
) -> None:
    admin = await make_admin(moderation_engine, mfa=True)
    target = await create_user(moderation_engine)
    other = await create_user(moderation_engine)
    case_id = await make_case(moderation_engine, target.user_id)
    app = app_for(moderation_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        injected = await client.post(
            f"/api/v1/admin/moderation/cases/{case_id}/actions",
            json={
                "action": "suspend",
                "reason": "Attempt target substitution",
                "target_id": str(other.user_id),
                "target_type": "user",
            },
            headers=admin.headers(idempotency_key=f"inject-{generate_uuid7()}"),
        )
        short = await client.post(
            f"/api/v1/admin/moderation/cases/{case_id}/actions",
            json={"action": "suspend", "reason": "  "},
            headers=admin.headers(idempotency_key=f"reason-{generate_uuid7()}"),
        )
    assert injected.status_code == short.status_code == 422
    async with moderation_engine.connect() as connection:
        target_status = (
            await connection.execute(
                text("SELECT status::text FROM talaqi.users WHERE id = :id"),
                {"id": target.user_id},
            )
        ).scalar_one()
        events = (
            await connection.execute(
                text(
                    "SELECT count(*) FROM talaqi.moderation_case_events "
                    "WHERE moderation_case_id = :id"
                ),
                {"id": case_id},
            )
        ).scalar_one()
    assert target_status == "active"
    assert events == 0


@pytest.mark.asyncio
async def test_club_and_event_actions_immediately_change_public_discovery(
    moderation_engine: AsyncEngine,
) -> None:
    async with AsyncSession(moderation_engine) as session, session.begin():
        await seed_discovery_fixtures(session)
    admin = await make_admin(moderation_engine, mfa=True)
    club_id, event_id = PUBLIC_CLUB_IDS[0], PUBLIC_EVENT_IDS[0]
    club_case = await make_case(moderation_engine, club_id, target_type="club")
    event_case = await make_case(moderation_engine, event_id, target_type="event")
    async with moderation_engine.connect() as connection:
        club_slug = (
            await connection.execute(
                text("SELECT slug FROM talaqi.clubs WHERE id = :id"), {"id": club_id}
            )
        ).scalar_one()
    app = app_for(moderation_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        assert (await client.get(f"/api/v1/clubs/{club_slug}")).status_code == 200
        assert (await client.get(f"/api/v1/events/{event_id}")).status_code == 200

        async def act(case_id: UUID, action: str) -> httpx.Response:
            return await client.post(
                f"/api/v1/admin/moderation/cases/{case_id}/actions",
                json={"action": action, "reason": f"Safety action: {action}"},
                headers=admin.headers(idempotency_key=f"{action}-{generate_uuid7()}"),
            )

        assert (await act(club_case, "suspend")).status_code == 200
        assert (await client.get(f"/api/v1/clubs/{club_slug}")).status_code == 404
        assert (await act(club_case, "restore")).status_code == 200
        assert (await client.get(f"/api/v1/clubs/{club_slug}")).status_code == 200
        assert (await act(club_case, "unpublish")).status_code == 200
        assert (await client.get(f"/api/v1/clubs/{club_slug}")).status_code == 404
        assert (await act(club_case, "restore")).status_code == 200
        assert (await client.get(f"/api/v1/clubs/{club_slug}")).status_code == 200

        event_unpublish = await act(event_case, "unpublish")
        assert event_unpublish.status_code == 409
        assert (await act(event_case, "suspend")).status_code == 200
        assert (await client.get(f"/api/v1/events/{event_id}")).status_code == 404
        assert (await act(event_case, "restore")).status_code == 200
        assert (await client.get(f"/api/v1/events/{event_id}")).status_code == 200


@pytest.mark.asyncio
async def test_action_evidence_is_database_immutable(
    moderation_engine: AsyncEngine,
) -> None:
    admin = await make_admin(moderation_engine, mfa=True)
    target = await create_user(moderation_engine)
    case_id = await make_case(moderation_engine, target.user_id)
    app = app_for(moderation_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        response = await client.post(
            f"/api/v1/admin/moderation/cases/{case_id}/actions",
            json={"action": "suspend", "reason": "Preserve evidence"},
            headers=admin.headers(idempotency_key=f"immutable-{generate_uuid7()}"),
        )
    assert response.status_code == 200
    async with moderation_engine.connect() as connection:
        case_event_id = (
            await connection.execute(
                text("SELECT id FROM talaqi.moderation_case_events WHERE moderation_case_id = :id"),
                {"id": case_id},
            )
        ).scalar_one()
        audit_id = (
            await connection.execute(
                text(
                    "SELECT id FROM talaqi.audit_events WHERE target_id = :id "
                    "AND action = 'moderation.target.suspend'"
                ),
                {"id": target.user_id},
            )
        ).scalar_one()
    with pytest.raises(DBAPIError, match="append-only"):
        async with moderation_engine.begin() as connection:
            await connection.execute(
                text("UPDATE talaqi.audit_events SET reason = 'changed' WHERE id = :id"),
                {"id": audit_id},
            )
    with pytest.raises(DBAPIError, match="append-only"):
        async with moderation_engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM talaqi.moderation_case_events WHERE id = :id"),
                {"id": case_event_id},
            )
