from __future__ import annotations

import asyncio
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


async def create_club(
    client: httpx.AsyncClient,
    owner: AuthenticatedUser,
    *,
    policy: str = "open",
) -> UUID:
    body = complete_club_body(slug("membership"))
    body["membership_policy"] = policy
    response = await client.post(
        "/api/v1/clubs",
        json=body,
        headers=owner.headers(idempotency_key=f"create-{generate_uuid7()}"),
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


async def join(
    client: httpx.AsyncClient,
    club_id: UUID,
    user: AuthenticatedUser,
    *,
    message: str | None = None,
) -> httpx.Response:
    return await client.post(
        f"/api/v1/clubs/{club_id}/join",
        json={"message": message},
        headers=user.headers(),
    )


@pytest.mark.asyncio
async def test_open_join_is_concurrency_safe_and_leave_is_idempotency_guarded(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    member = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_id = await create_club(client, owner)
        first, second = await asyncio.gather(
            join(client, club_id, member),
            join(client, club_id, member),
        )
        left = await client.delete(
            f"/api/v1/clubs/{club_id}/membership",
            headers=member.headers(),
        )
        missing = await client.delete(
            f"/api/v1/clubs/{club_id}/membership",
            headers=member.headers(),
        )

    assert {first.status_code, second.status_code} == {200}
    assert first.json()["state"] == second.json()["state"] == "member"
    assert first.json()["membership_id"] == second.json()["membership_id"]
    assert left.status_code == 200
    assert missing.status_code == 404
    async with club_engine.connect() as connection:
        count = await connection.scalar(
            text(
                """
                SELECT count(*) FROM talaqi.club_memberships
                WHERE club_id = :club_id AND user_id = :user_id
                """
            ),
            {"club_id": club_id, "user_id": member.user_id},
        )
    assert count == 0


@pytest.mark.asyncio
async def test_approval_requests_and_duplicate_approval_are_idempotent(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    applicant = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_id = await create_club(client, owner, policy="approval_required")
        first = await join(client, club_id, applicant, message="Please add me")
        second = await join(client, club_id, applicant, message="Changed message")
        request_id = first.json()["join_request_id"]
        queue = await client.get(
            f"/api/v1/clubs/{club_id}/join-requests",
            headers=owner.headers(),
        )
        approved, duplicate = await asyncio.gather(
            client.post(
                f"/api/v1/clubs/{club_id}/join-requests/{request_id}/approve",
                json={"reason": "Profile reviewed"},
                headers=owner.headers(),
            ),
            client.post(
                f"/api/v1/clubs/{club_id}/join-requests/{request_id}/approve",
                json={"reason": "Safe retry"},
                headers=owner.headers(),
            ),
        )

    assert first.status_code == second.status_code == 200
    assert first.json()["join_request_id"] == second.json()["join_request_id"]
    assert queue.status_code == 200
    assert len(queue.json()["items"]) == 1
    assert queue.json()["items"][0]["message"] == "Please add me"
    assert approved.status_code == duplicate.status_code == 200
    async with club_engine.connect() as connection:
        membership_count = await connection.scalar(
            text(
                """
                SELECT count(*) FROM talaqi.club_memberships
                WHERE club_id = :club_id AND user_id = :user_id
                """
            ),
            {"club_id": club_id, "user_id": applicant.user_id},
        )
        approval_audits = await connection.scalar(
            text(
                """
                SELECT count(*) FROM talaqi.audit_events
                WHERE action = 'club.join_request.approve'
                  AND target_id = :request_id
                """
            ),
            {"request_id": UUID(request_id)},
        )
        notification_events = (
            (
                await connection.execute(
                    text(
                        """
                    SELECT event_type, payload ->> 'recipient_user_id'
                    FROM talaqi.outbox_events
                    WHERE aggregate_id = :request_id
                    ORDER BY event_type
                    """
                    ),
                    {"request_id": UUID(request_id)},
                )
            )
            .tuples()
            .all()
        )
    assert membership_count == 1
    assert approval_audits == 1
    assert notification_events == [
        ("membership.approved", str(applicant.user_id)),
        ("membership.requested", str(owner.user_id)),
    ]


@pytest.mark.asyncio
async def test_managers_can_see_member_data_but_members_and_other_clubs_cannot(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    other_owner = await create_user(club_engine)
    member = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_id = await create_club(client, owner)
        other_club_id = await create_club(client, other_owner)
        assert (await join(client, club_id, member)).status_code == 200
        owner_view = await client.get(f"/api/v1/clubs/{club_id}/members", headers=owner.headers())
        member_view = await client.get(f"/api/v1/clubs/{club_id}/members", headers=member.headers())
        cross_club = await client.get(
            f"/api/v1/clubs/{other_club_id}/members", headers=owner.headers()
        )
        async with club_engine.connect() as connection:
            public_slug = await connection.scalar(
                text("SELECT slug FROM talaqi.clubs WHERE id = :club_id"),
                {"club_id": club_id},
            )
        public_view = await client.get(f"/api/v1/clubs/{public_slug}")

    assert owner_view.status_code == 200
    assert len(owner_view.json()["items"]) == 2
    assert all(item["email"] for item in owner_view.json()["items"])
    assert member_view.status_code == 403
    assert cross_club.status_code == 403
    assert public_view.status_code == 200
    assert public_view.json()["member_count"] == 2
    assert "email" not in public_view.text
    assert "user_id" not in public_view.text


@pytest.mark.asyncio
async def test_only_owner_can_change_roles_and_admin_cannot_escalate(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    admin = await create_user(club_engine)
    member = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_id = await create_club(client, owner)
        assert (await join(client, club_id, admin)).status_code == 200
        assert (await join(client, club_id, member)).status_code == 200
        promoted = await client.patch(
            f"/api/v1/clubs/{club_id}/members/{admin.user_id}/role",
            json={"role": "admin", "reason": "Help manage this club"},
            headers=owner.headers(),
        )
        escalation = await client.patch(
            f"/api/v1/clubs/{club_id}/members/{member.user_id}/role",
            json={"role": "admin", "reason": "Attempt escalation"},
            headers=admin.headers(),
        )
        queue = await client.get(f"/api/v1/clubs/{club_id}/join-requests", headers=admin.headers())

    assert promoted.status_code == 200
    assert escalation.status_code == 403
    assert queue.status_code == 200


@pytest.mark.asyncio
async def test_cross_club_request_decision_is_denied(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    other_owner = await create_user(club_engine)
    applicant = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_id = await create_club(client, owner, policy="approval_required")
        other_club_id = await create_club(client, other_owner, policy="approval_required")
        request_id = (await join(client, club_id, applicant)).json()["join_request_id"]
        denied = await client.post(
            f"/api/v1/clubs/{other_club_id}/join-requests/{request_id}/approve",
            json={"reason": "Cross club attempt"},
            headers=other_owner.headers(),
        )

    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_ownership_transfer_protects_the_new_sole_owner(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    successor = await create_user(club_engine)
    ineligible = await create_user(club_engine, profile_complete=False)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_id = await create_club(client, owner)
        assert (await join(client, club_id, successor)).status_code == 200
        assert (await join(client, club_id, ineligible)).status_code == 200
        owner_exit = await client.delete(
            f"/api/v1/clubs/{club_id}/membership", headers=owner.headers()
        )
        denied_transfer = await client.post(
            f"/api/v1/clubs/{club_id}/ownership-transfer",
            json={"target_user_id": str(ineligible.user_id), "reason": "Unsafe handover"},
            headers=owner.headers(),
        )
        transferred = await client.post(
            f"/api/v1/clubs/{club_id}/ownership-transfer",
            json={"target_user_id": str(successor.user_id), "reason": "Planned handover"},
            headers=owner.headers(),
        )
        old_owner_exit = await client.delete(
            f"/api/v1/clubs/{club_id}/membership", headers=owner.headers()
        )
        new_owner_exit = await client.delete(
            f"/api/v1/clubs/{club_id}/membership", headers=successor.headers()
        )

    assert owner_exit.status_code == 409
    assert denied_transfer.status_code == 403
    assert transferred.status_code == 200
    assert old_owner_exit.status_code == 200
    assert new_owner_exit.status_code == 409
    async with club_engine.connect() as connection:
        owner_row = (
            await connection.execute(
                text(
                    """
                    SELECT club.owner_user_id, membership.role::text
                    FROM talaqi.clubs AS club
                    JOIN talaqi.club_memberships AS membership
                      ON membership.club_id = club.id
                     AND membership.user_id = club.owner_user_id
                    WHERE club.id = :club_id
                    """
                ),
                {"club_id": club_id},
            )
        ).one()
    assert owner_row == (successor.user_id, "owner")


@pytest.mark.asyncio
async def test_reject_is_idempotent_and_requires_reason(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    applicant = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_id = await create_club(client, owner, policy="approval_required")
        request_id = (await join(client, club_id, applicant)).json()["join_request_id"]
        missing_reason = await client.post(
            f"/api/v1/clubs/{club_id}/join-requests/{request_id}/reject",
            json={},
            headers=owner.headers(),
        )
        rejected = await client.post(
            f"/api/v1/clubs/{club_id}/join-requests/{request_id}/reject",
            json={"reason": "Profile does not meet club rules"},
            headers=owner.headers(),
        )
        duplicate = await client.post(
            f"/api/v1/clubs/{club_id}/join-requests/{request_id}/reject",
            json={"reason": "Safe retry"},
            headers=owner.headers(),
        )

    assert missing_reason.status_code == 422
    assert rejected.status_code == duplicate.status_code == 200


@pytest.mark.asyncio
async def test_closed_and_suspended_clubs_deny_membership_operations(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    applicant = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        closed_id = await create_club(client, owner)
        closed = await client.post(
            f"/api/v1/clubs/{closed_id}/close",
            json={"reason": "Club is ending operations"},
            headers=owner.headers(),
        )
        closed_join = await join(client, closed_id, applicant)

    suspended_owner = await create_user(club_engine)
    suspended_id: UUID
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        suspended_id = await create_club(client, suspended_owner)
    async with club_engine.begin() as connection:
        await connection.execute(
            text(
                """
                UPDATE talaqi.clubs
                SET status = 'suspended', suspended_at = clock_timestamp(),
                    suspension_reason = 'Safety review'
                WHERE id = :club_id
                """
            ),
            {"club_id": suspended_id},
        )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        suspended_join = await join(client, suspended_id, applicant)
        suspended_members = await client.get(
            f"/api/v1/clubs/{suspended_id}/members",
            headers=suspended_owner.headers(),
        )

    assert closed.status_code == 200
    assert closed_join.status_code == 403
    assert suspended_join.status_code == 403
    assert suspended_members.status_code == 403


@pytest.mark.asyncio
async def test_unverified_user_cannot_join_and_mutations_require_csrf(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    unverified = await create_user(club_engine, verified=False)
    member = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_id = await create_club(client, owner)
        denied = await join(client, club_id, unverified)
        no_csrf = await client.post(
            f"/api/v1/clubs/{club_id}/join",
            json={"message": None},
            headers={"cookie": member.cookie},
        )

    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "email_verification_required"
    assert no_csrf.status_code == 403


@pytest.mark.asyncio
async def test_suspended_club_denies_every_membership_manager_mutation(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    member = await create_user(club_engine)
    applicant = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_id = await create_club(client, owner, policy="approval_required")
        member_request = (await join(client, club_id, member)).json()["join_request_id"]
        approved = await client.post(
            f"/api/v1/clubs/{club_id}/join-requests/{member_request}/approve",
            json={"reason": "Approved before suspension"},
            headers=owner.headers(),
        )
        assert approved.status_code == 200
        pending_request = (await join(client, club_id, applicant)).json()["join_request_id"]

    async with club_engine.begin() as connection:
        await connection.execute(
            text(
                """
                UPDATE talaqi.clubs
                SET status = 'suspended', suspended_at = clock_timestamp(),
                    suspension_reason = 'Safety review'
                WHERE id = :club_id
                """
            ),
            {"club_id": club_id},
        )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        denied = [
            await client.post(
                f"/api/v1/clubs/{club_id}/join-requests/{pending_request}/approve",
                json={"reason": "Should remain blocked"},
                headers=owner.headers(),
            ),
            await client.patch(
                f"/api/v1/clubs/{club_id}/members/{member.user_id}/role",
                json={"role": "admin", "reason": "Should remain blocked"},
                headers=owner.headers(),
            ),
            await client.post(
                f"/api/v1/clubs/{club_id}/ownership-transfer",
                json={"target_user_id": str(member.user_id), "reason": "Blocked"},
                headers=owner.headers(),
            ),
            await client.post(
                f"/api/v1/clubs/{club_id}/close",
                json={"reason": "Should remain blocked"},
                headers=owner.headers(),
            ),
            await client.delete(f"/api/v1/clubs/{club_id}/membership", headers=member.headers()),
        ]

    assert {response.status_code for response in denied} == {403}


@pytest.mark.asyncio
async def test_role_transfer_and_close_emit_reasoned_audit_events(
    club_engine: AsyncEngine,
) -> None:
    owner = await create_user(club_engine)
    successor = await create_user(club_engine)
    app = app_for(club_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_id = await create_club(client, owner)
        assert (await join(client, club_id, successor)).status_code == 200
        promoted = await client.patch(
            f"/api/v1/clubs/{club_id}/members/{successor.user_id}/role",
            json={"role": "admin", "reason": "  Trusted organizer  "},
            headers=owner.headers(),
        )
        transferred = await client.post(
            f"/api/v1/clubs/{club_id}/ownership-transfer",
            json={
                "target_user_id": str(successor.user_id),
                "reason": "  Planned ownership handover  ",
            },
            headers=owner.headers(),
        )
        closed = await client.post(
            f"/api/v1/clubs/{club_id}/close",
            json={"reason": "  Community operations ended  "},
            headers=successor.headers(),
        )

    assert promoted.status_code == transferred.status_code == closed.status_code == 200
    async with club_engine.connect() as connection:
        audit_rows = (
            (
                await connection.execute(
                    text(
                        """
                    SELECT action, actor_user_id, reason, request_id,
                           safe_before, safe_after
                    FROM talaqi.audit_events
                    WHERE (target_id = :club_id AND action IN (
                              'club.ownership.transfer', 'club.close'
                          ))
                       OR (action = 'club.member.role_change'
                           AND safe_after ->> 'club_id' = CAST(:club_id AS text))
                    ORDER BY created_at, id
                    """
                    ),
                    {"club_id": club_id},
                )
            )
            .mappings()
            .all()
        )

    by_action = {row["action"]: row for row in audit_rows}
    assert by_action["club.member.role_change"]["actor_user_id"] == owner.user_id
    assert by_action["club.member.role_change"]["reason"] == "Trusted organizer"
    assert by_action["club.member.role_change"]["safe_before"]["role"] == "member"
    assert by_action["club.member.role_change"]["safe_after"]["role"] == "admin"
    assert by_action["club.ownership.transfer"]["actor_user_id"] == owner.user_id
    assert by_action["club.ownership.transfer"]["reason"] == "Planned ownership handover"
    assert by_action["club.close"]["actor_user_id"] == successor.user_id
    assert by_action["club.close"]["reason"] == "Community operations ended"
    assert all(
        by_action[action]["request_id"] is not None
        for action in (
            "club.member.role_change",
            "club.ownership.transfer",
            "club.close",
        )
    )
