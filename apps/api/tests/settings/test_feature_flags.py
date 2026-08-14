from __future__ import annotations

import httpx
import pytest
from clubs.test_routes import app_for, create_user
from moderation.test_moderation import make_admin
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.db.identifiers import generate_uuid7
from talaqi.settings.models import FEATURE_FLAGS


@pytest.mark.asyncio
async def test_feature_flags_are_seeded_enabled_and_admin_reads_are_private(
    settings_engine: AsyncEngine,
) -> None:
    member = await create_user(settings_engine)
    admin = await make_admin(settings_engine, mfa=False)
    app = app_for(settings_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        unauthenticated = await client.get("/api/v1/admin/settings/feature-flags")
        forbidden = await client.get(
            "/api/v1/admin/settings/feature-flags", headers=member.headers()
        )
        response = await client.get("/api/v1/admin/settings/feature-flags", headers=admin.headers())
    assert unauthenticated.status_code == 401
    assert forbidden.status_code == 403
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Cookie"
    assert [item["key"] for item in response.json()["items"]] == sorted(FEATURE_FLAGS)
    assert all(
        item["enabled"] is True and item["revision"] == 1 for item in response.json()["items"]
    )


@pytest.mark.asyncio
async def test_feature_flag_preview_and_update_require_mfa_csrf_revision_and_reason(
    settings_engine: AsyncEngine,
) -> None:
    no_mfa = await make_admin(settings_engine, mfa=False)
    admin = await make_admin(settings_engine, mfa=True)
    key = "features.member_reports_enabled"
    path = f"/api/v1/admin/settings/feature-flags/{key}"
    body = {"enabled": False, "revision": 1, "reason": "Pause abusive submissions"}
    idempotency_key = f"feature-{generate_uuid7()}"
    app = app_for(settings_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        denied = await client.post(f"{path}/preview", json=body, headers=no_mfa.headers())
        missing_csrf = await client.patch(
            path,
            json=body,
            headers={
                "cookie": admin.cookie,
                "Idempotency-Key": f"csrf-{generate_uuid7()}",
            },
        )
        preview = await client.post(f"{path}/preview", json=body, headers=admin.headers())
        updated = await client.patch(
            path,
            json=body,
            headers=admin.headers(idempotency_key=idempotency_key),
        )
        replay = await client.patch(
            path,
            json=body,
            headers=admin.headers(idempotency_key=idempotency_key),
        )
        stale = await client.patch(
            path,
            json={**body, "reason": "Stale request"},
            headers=admin.headers(idempotency_key=f"stale-{generate_uuid7()}"),
        )
    assert denied.status_code == missing_csrf.status_code == 403
    assert preview.status_code == 200
    assert preview.json()["current"]["enabled"] is True
    assert preview.json()["proposed"] == {"key": key, "enabled": False, "revision": 2}
    assert updated.status_code == replay.status_code == 200
    assert updated.json() == replay.json()
    assert updated.json()["setting"] == {"key": key, "enabled": False, "revision": 2}
    assert stale.status_code == 409
    async with settings_engine.connect() as connection:
        audit = (
            await connection.execute(
                text(
                    """
                    SELECT action, reason, safe_before, safe_after
                    FROM talaqi.audit_events
                    WHERE action = 'settings.feature_flag.update'
                    """
                )
            )
        ).one()
    assert audit[0] == "settings.feature_flag.update"
    assert audit[1] == body["reason"]
    assert audit[2] == {"key": key, "enabled": True, "revision": 1}
    assert audit[3] == {"key": key, "enabled": False, "revision": 2}


@pytest.mark.asyncio
async def test_disabled_report_flag_blocks_before_domain_writes(
    settings_engine: AsyncEngine,
) -> None:
    reporter = await create_user(settings_engine)
    target = await create_user(settings_engine)
    async with settings_engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE talaqi.platform_settings SET value = 'false'::jsonb "
                "WHERE key = 'features.member_reports_enabled'"
            )
        )
    app = app_for(settings_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        response = await client.post(
            "/api/v1/reports",
            json={
                "target_type": "user",
                "target_id": str(target.user_id),
                "category": "other",
                "description": "A valid report that should be blocked by the feature flag.",
            },
            headers=reporter.headers(idempotency_key=f"report-{generate_uuid7()}"),
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "feature_disabled"
    async with settings_engine.connect() as connection:
        case_count = await connection.scalar(text("SELECT count(*) FROM talaqi.moderation_cases"))
        audit_count = await connection.scalar(
            text(
                "SELECT count(*) FROM talaqi.audit_events "
                "WHERE action = 'moderation.report.submitted'"
            )
        )
    assert case_count == audit_count == 0


def test_feature_flag_keys_are_the_approved_closed_beta_set() -> None:
    assert FEATURE_FLAGS == (
        "features.member_reports_enabled",
        "features.organizer_announcements_enabled",
        "features.independent_event_creation_enabled",
    )


@pytest.mark.asyncio
async def test_regional_policy_preview_update_is_mfa_revision_safe_and_audited(
    settings_engine: AsyncEngine,
) -> None:
    member = await create_user(settings_engine)
    no_mfa = await make_admin(settings_engine, mfa=False)
    admin = await make_admin(settings_engine, mfa=True)
    path = "/api/v1/admin/regions/TR/policy"
    body = {
        "revision": 1,
        "reason": "Adjust the closed beta ownership capacity",
        "club_limit": 2,
        "independent_event_limit": 4,
    }
    app = app_for(settings_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        member_read = await client.get(path, headers=member.headers())
        no_mfa_preview = await client.post(f"{path}/preview", json=body, headers=no_mfa.headers())
        preview = await client.post(f"{path}/preview", json=body, headers=admin.headers())
        key = f"region-policy-{generate_uuid7()}"
        updated = await client.patch(path, json=body, headers=admin.headers(idempotency_key=key))
        replay = await client.patch(path, json=body, headers=admin.headers(idempotency_key=key))
        stale = await client.patch(
            path,
            json={**body, "reason": "A stale regional policy update"},
            headers=admin.headers(idempotency_key=f"region-stale-{generate_uuid7()}"),
        )
    assert member_read.status_code == no_mfa_preview.status_code == 403
    assert preview.status_code == 200
    assert preview.json()["changed_fields"] == ["club_limit", "independent_event_limit"]
    assert preview.json()["proposed"]["revision"] == 2
    assert updated.status_code == replay.status_code == 200
    assert updated.json() == replay.json()
    assert updated.json()["policy"]["club_limit"] == 2
    assert updated.json()["policy"]["independent_event_limit"] == 4
    assert stale.status_code == 409
    async with settings_engine.connect() as connection:
        audit = (
            await connection.execute(
                text(
                    "SELECT action, reason, safe_before, safe_after FROM talaqi.audit_events "
                    "WHERE action = 'regions.policy.update'"
                )
            )
        ).one()
    assert audit[0] == "regions.policy.update"
    assert audit[1] == body["reason"]
    assert audit[2]["country_code"] == audit[3]["country_code"] == "TR"
    assert audit[2]["revision"] == 1
    assert audit[3]["revision"] == 2
    async with settings_engine.begin() as connection:
        await connection.execute(
            text(
                """
                UPDATE talaqi.regional_policies AS policy
                SET default_club_ownership_limit = 1,
                    default_active_independent_event_limit = 3,
                    exact_venue_public_by_default = false,
                    revision = 1
                FROM talaqi.countries AS country
                WHERE policy.country_id = country.id AND country.code = 'TR'
                """
            )
        )
