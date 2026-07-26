from __future__ import annotations

from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.db.identifiers import generate_uuid7

from .test_routes import (
    AuthenticatedUser,
    app_for,
    complete_club_body,
    create_user,
    slug,
)


async def create_draft(
    client: httpx.AsyncClient,
    owner: AuthenticatedUser,
    *,
    name: str = "Workspace Draft",
) -> UUID:
    response = await client.post(
        "/api/v1/clubs",
        json={"slug": slug("workspace"), "name": name},
        headers=owner.headers(idempotency_key=f"workspace-{generate_uuid7()}"),
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


async def add_membership(
    engine: AsyncEngine,
    club_id: UUID,
    user_id: UUID,
    role: str,
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO talaqi.club_memberships (id, club_id, user_id, role)
                VALUES (:id, :club_id, :user_id, CAST(:role AS talaqi.club_role))
                """
            ),
            {
                "id": generate_uuid7(),
                "club_id": club_id,
                "user_id": user_id,
                "role": role,
            },
        )


@pytest.mark.asyncio
async def test_workspace_lists_only_owned_or_managed_clubs_with_server_capabilities(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    admin = await create_user(club_engine)
    member = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_id = await create_draft(client, owner)
    await add_membership(club_engine, club_id, admin.user_id, "admin")
    await add_membership(club_engine, club_id, member.user_id, "member")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        owner_view = await client.get("/api/v1/clubs/managed", headers=owner.headers())
        admin_view = await client.get("/api/v1/clubs/managed", headers=admin.headers())
        member_view = await client.get("/api/v1/clubs/managed", headers=member.headers())

    assert owner_view.status_code == admin_view.status_code == member_view.status_code == 200
    owner_item = owner_view.json()["items"][0]
    admin_item = admin_view.json()["items"][0]
    assert owner_item["id"] == admin_item["id"] == str(club_id)
    assert owner_item["role"] == "owner"
    assert set(owner_item["capabilities"]) == {
        "edit_profile",
        "manage_members",
        "change_member_roles",
        "transfer_ownership",
        "close_club",
        "preview_profile",
    }
    assert admin_item["role"] == "admin"
    assert set(admin_item["capabilities"]) == {
        "edit_profile",
        "manage_members",
        "preview_profile",
    }
    assert member_view.json() == {"items": []}


@pytest.mark.asyncio
async def test_admin_can_complete_draft_but_member_and_cross_club_admin_are_denied(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    admin = await create_user(club_engine)
    member = await create_user(club_engine)
    other_owner = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_id = await create_draft(client, owner)
        other_club_id = await create_draft(client, other_owner, name="Other Draft")
    await add_membership(club_engine, club_id, admin.user_id, "admin")
    await add_membership(club_engine, club_id, member.user_id, "member")

    patch = {
        "revision": 1,
        "description": "Completed by a scoped club administrator.",
        "category_slug": "sports",
        "country_code": "TR",
        "city_slug": "istanbul",
    }
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        admin_read = await client.get(f"/api/v1/clubs/{club_id}", headers=admin.headers())
        completed = await client.patch(
            f"/api/v1/clubs/{club_id}", json=patch, headers=admin.headers()
        )
        member_denial = await client.patch(
            f"/api/v1/clubs/{club_id}", json={**patch, "revision": 2}, headers=member.headers()
        )
        cross_denial = await client.patch(
            f"/api/v1/clubs/{other_club_id}", json=patch, headers=admin.headers()
        )

    assert admin_read.status_code == 200
    assert completed.status_code == 200
    assert completed.json()["status"] == "published"
    assert completed.json()["revision"] == 2
    assert member_denial.status_code == cross_denial.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("club_status", ["suspended", "closed"])
async def test_unavailable_club_stays_visible_without_capabilities_and_denies_profile_access(
    club_engine: AsyncEngine,
    club_status: str,
) -> None:
    owner = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        response = await client.post(
            "/api/v1/clubs",
            json=complete_club_body(slug(f"{club_status}-workspace")),
            headers=owner.headers(idempotency_key=f"workspace-{generate_uuid7()}"),
        )
        assert response.status_code == 201
        club_id = UUID(response.json()["id"])
    async with club_engine.begin() as connection:
        await connection.execute(
            text(
                """
                UPDATE talaqi.clubs
                SET status = CAST(:status AS talaqi.club_status),
                    suspended_at = CASE
                        WHEN :status = 'suspended' THEN clock_timestamp()
                        ELSE suspended_at
                    END,
                    suspension_reason = CASE
                        WHEN :status = 'suspended' THEN 'Safety investigation'
                        ELSE suspension_reason
                    END,
                    closed_at = CASE
                        WHEN :status = 'closed' THEN clock_timestamp()
                        ELSE closed_at
                    END
                WHERE id = :club_id
                """
            ),
            {"club_id": club_id, "status": club_status},
        )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        managed = await client.get("/api/v1/clubs/managed", headers=owner.headers())
        direct = await client.get(f"/api/v1/clubs/{club_id}", headers=owner.headers())
        update = await client.patch(
            f"/api/v1/clubs/{club_id}",
            json={"revision": 1, "name": "Unavailable update"},
            headers=owner.headers(),
        )

    assert managed.status_code == 200
    assert managed.json()["items"][0]["status"] == club_status
    assert managed.json()["items"][0]["capabilities"] == []
    if club_status == "suspended":
        assert managed.json()["items"][0]["suspension_reason"] == "Safety investigation"
    assert direct.status_code == update.status_code == 403


@pytest.mark.asyncio
async def test_inactive_manager_is_denied_workspace_listing_detail_and_update(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_id = await create_draft(client, owner)

    async with club_engine.begin() as connection:
        await connection.execute(
            text(
                """
                UPDATE talaqi.users
                SET status = 'suspended',
                    suspended_at = clock_timestamp(),
                    suspension_reason = 'Workspace authorization check'
                WHERE id = :user_id
                """
            ),
            {"user_id": owner.user_id},
        )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        managed = await client.get("/api/v1/clubs/managed", headers=owner.headers())
        direct = await client.get(f"/api/v1/clubs/{club_id}", headers=owner.headers())
        update = await client.patch(
            f"/api/v1/clubs/{club_id}",
            json={"revision": 1, "name": "Inactive update"},
            headers=owner.headers(),
        )

    assert managed.status_code == direct.status_code == update.status_code == 401


@pytest.mark.asyncio
async def test_workspace_capabilities_do_not_replace_membership_endpoint_authorization(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    admin = await create_user(club_engine)
    member = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_id = await create_draft(client, owner)
    await add_membership(club_engine, club_id, admin.user_id, "admin")
    await add_membership(club_engine, club_id, member.user_id, "member")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        admin_members = await client.get(
            f"/api/v1/clubs/{club_id}/members", headers=admin.headers()
        )
        admin_requests = await client.get(
            f"/api/v1/clubs/{club_id}/join-requests", headers=admin.headers()
        )
        admin_role_denial = await client.patch(
            f"/api/v1/clubs/{club_id}/members/{member.user_id}/role",
            json={"role": "admin", "reason": "Capability drift check"},
            headers=admin.headers(),
        )
        admin_transfer_denial = await client.post(
            f"/api/v1/clubs/{club_id}/ownership-transfer",
            json={"target_user_id": str(member.user_id), "reason": "Capability drift check"},
            headers=admin.headers(),
        )
        admin_close_denial = await client.post(
            f"/api/v1/clubs/{club_id}/close",
            json={"reason": "Capability drift check"},
            headers=admin.headers(),
        )
        member_members_denial = await client.get(
            f"/api/v1/clubs/{club_id}/members", headers=member.headers()
        )
        member_requests_denial = await client.get(
            f"/api/v1/clubs/{club_id}/join-requests", headers=member.headers()
        )

    assert admin_members.status_code == admin_requests.status_code == 200
    assert (
        admin_role_denial.status_code
        == admin_transfer_denial.status_code
        == admin_close_denial.status_code
        == member_members_denial.status_code
        == member_requests_denial.status_code
        == 403
    )
