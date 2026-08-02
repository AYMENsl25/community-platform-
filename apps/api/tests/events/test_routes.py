from __future__ import annotations

import asyncio
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.db.identifiers import generate_uuid7

from .fixtures import (
    add_club_member,
    app_for,
    complete_event_body,
    create_club,
    create_media,
    create_user,
)


@pytest.mark.asyncio
async def test_independent_create_is_private_idempotent_and_audited(
    event_engine: AsyncEngine,
) -> None:
    owner = await create_user(event_engine)
    key = f"event-create-{generate_uuid7()}"
    body = complete_event_body()
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        first = await client.post(
            "/api/v1/events", json=body, headers=owner.headers(idempotency_key=key)
        )
        replay = await client.post(
            "/api/v1/events", json=body, headers=owner.headers(idempotency_key=key)
        )
        managed = await client.get(
            f"/api/v1/events/{first.json()['id']}/managed",
            headers={"cookie": owner.cookie},
        )

    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert first.headers["cache-control"] == "private, no-store"
    assert first.headers["vary"] == "Cookie"
    event = first.json()
    assert event["status"] == "published"
    assert event["owner_user_id"] == str(owner.user_id)
    assert event["capacity"] is None
    assert event["cancellation_cutoff_minutes"] == 1440
    assert managed.status_code == 200
    assert managed.json()["exact_address"] == "Private managed address"

    async with event_engine.connect() as connection:
        actions = (
            (
                await connection.execute(
                    text(
                        """
                    SELECT action FROM talaqi.audit_events
                    WHERE target_id = :event_id ORDER BY created_at, id
                    """
                    ),
                    {"event_id": UUID(event["id"])},
                )
            )
            .scalars()
            .all()
        )
    assert actions == ["event.create", "event.publish"]


@pytest.mark.asyncio
async def test_club_owner_and_admin_can_create_but_member_and_outsider_cannot(
    event_engine: AsyncEngine,
) -> None:
    owner = await create_user(event_engine)
    admin = await create_user(event_engine)
    member = await create_user(event_engine)
    outsider = await create_user(event_engine)
    other_club_owner = await create_user(event_engine)
    other_club_admin = await create_user(event_engine)
    club_id = await create_club(event_engine, owner)
    other_club_id = await create_club(event_engine, other_club_owner)
    await add_club_member(event_engine, club_id, admin, role="admin")
    await add_club_member(event_engine, club_id, member, role="member")
    await add_club_member(event_engine, other_club_id, other_club_admin, role="admin")
    body = complete_event_body(ownership_type="club", club_id=str(club_id), publish=False)
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        responses: list[httpx.Response] = []
        for actor in (owner, admin, member, outsider, other_club_admin):
            responses.append(  # noqa: PERF401
                await client.post(
                    "/api/v1/events",
                    json=body,
                    headers=actor.headers(idempotency_key=f"club-event-{generate_uuid7()}"),
                )
            )
        event_id = responses[0].json()["id"]
        admin_update = await client.patch(
            f"/api/v1/events/{event_id}",
            json={"revision": 1, "title": "Updated by another club manager"},
            headers=admin.headers(),
        )
        denied: list[httpx.Response] = []
        for actor in (member, outsider, other_club_admin):
            denied.extend(
                [
                    await client.patch(
                        f"/api/v1/events/{event_id}",
                        json={"revision": 2, "title": "Unauthorized update"},
                        headers=actor.headers(),
                    ),
                    await client.post(
                        f"/api/v1/events/{event_id}/cancel",
                        json={"revision": 2},
                        headers=actor.headers(),
                    ),
                    await client.post(
                        f"/api/v1/events/{event_id}/complete",
                        json={"revision": 2},
                        headers=actor.headers(),
                    ),
                    await client.post(
                        f"/api/v1/events/{event_id}/duplicate",
                        headers=actor.headers(
                            idempotency_key=f"unauthorized-duplicate-{generate_uuid7()}"
                        ),
                    ),
                    await client.request(
                        "DELETE",
                        f"/api/v1/events/{event_id}",
                        json={"revision": 2},
                        headers=actor.headers(),
                    ),
                ]
            )
        managed_lists = [
            await client.get("/api/v1/events/managed", headers={"cookie": actor.cookie})
            for actor in (owner, admin, member, outsider)
        ]

    assert [response.status_code for response in responses] == [201, 201, 403, 403, 403]
    assert admin_update.status_code == 200
    assert admin_update.json()["title"] == "Updated by another club manager"
    assert [response.status_code for response in denied] == [403] * 15
    assert [response.status_code for response in managed_lists] == [200] * 4
    assert [len(response.json()["items"]) for response in managed_lists] == [2, 2, 0, 0]
    assert managed_lists[0].headers["cache-control"] == "private, no-store"
    assert managed_lists[1].json()["items"][0]["capabilities"]
    assert responses[0].json()["club_id"] == str(club_id)
    assert responses[0].json()["owner_user_id"] is None
    assert responses[2].json()["error"]["code"] == "forbidden"
    assert responses[3].json()["error"]["code"] == "forbidden"


@pytest.mark.asyncio
async def test_revision_lifecycle_duplicate_delete_and_cross_owner_denial(
    event_engine: AsyncEngine,
) -> None:
    owner = await create_user(event_engine)
    outsider = await create_user(event_engine)
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        created = await client.post(
            "/api/v1/events",
            json=complete_event_body(),
            headers=owner.headers(idempotency_key=f"create-{generate_uuid7()}"),
        )
        event_id = created.json()["id"]
        second_created = await client.post(
            "/api/v1/events",
            json=complete_event_body(title="Second source event", publish=False),
            headers=owner.headers(idempotency_key=f"create-{generate_uuid7()}"),
        )
        second_event_id = second_created.json()["id"]
        updated = await client.patch(
            f"/api/v1/events/{event_id}",
            json={"revision": 1, "title": "Updated Talaqi Event"},
            headers=owner.headers(),
        )
        stale = await client.patch(
            f"/api/v1/events/{event_id}",
            json={"revision": 1, "title": "Stale Event"},
            headers=owner.headers(),
        )
        outsider_get = await client.get(
            f"/api/v1/events/{event_id}/managed",
            headers={"cookie": outsider.cookie},
        )
        outsider_denied = [
            await client.patch(
                f"/api/v1/events/{event_id}",
                json={"revision": 2, "title": "Cross-owner update"},
                headers=outsider.headers(),
            ),
            await client.post(
                f"/api/v1/events/{event_id}/cancel",
                json={"revision": 2},
                headers=outsider.headers(),
            ),
            await client.post(
                f"/api/v1/events/{event_id}/complete",
                json={"revision": 2},
                headers=outsider.headers(),
            ),
            await client.post(
                f"/api/v1/events/{event_id}/duplicate",
                headers=outsider.headers(
                    idempotency_key=f"cross-owner-duplicate-{generate_uuid7()}"
                ),
            ),
            await client.request(
                "DELETE",
                f"/api/v1/events/{event_id}",
                json={"revision": 2},
                headers=outsider.headers(),
            ),
        ]
        cancelled = await client.post(
            f"/api/v1/events/{event_id}/cancel",
            json={"revision": 2},
            headers=owner.headers(),
        )
        invalid_complete = await client.post(
            f"/api/v1/events/{event_id}/complete",
            json={"revision": 3},
            headers=owner.headers(),
        )
        duplicate_key = f"duplicate-{generate_uuid7()}"
        duplicate = await client.post(
            f"/api/v1/events/{event_id}/duplicate",
            headers=owner.headers(idempotency_key=duplicate_key),
        )
        duplicate_replay = await client.post(
            f"/api/v1/events/{event_id}/duplicate",
            headers=owner.headers(idempotency_key=duplicate_key),
        )
        cross_event_duplicate = await client.post(
            f"/api/v1/events/{second_event_id}/duplicate",
            headers=owner.headers(idempotency_key=duplicate_key),
        )
        deleted = await client.request(
            "DELETE",
            f"/api/v1/events/{duplicate.json()['id']}",
            json={"revision": 1},
            headers=owner.headers(),
        )
        completable = await client.post(
            "/api/v1/events",
            json=complete_event_body(title="Completed event"),
            headers=owner.headers(idempotency_key=f"complete-{generate_uuid7()}"),
        )
        completable_id = UUID(completable.json()["id"])
        async with event_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    UPDATE talaqi.events
                    SET start_at = clock_timestamp() - interval '2 hours',
                        end_at = clock_timestamp() - interval '1 hour'
                    WHERE id = :event_id
                    """
                ),
                {"event_id": completable_id},
            )
        completed = await client.post(
            f"/api/v1/events/{completable_id}/complete",
            json={"revision": 1},
            headers=owner.headers(),
        )

    async with event_engine.connect() as connection:
        lifecycle_actions = {
            event_id: list(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT action FROM talaqi.audit_events
                            WHERE target_id = :event_id ORDER BY created_at, id
                            """
                        ),
                        {"event_id": UUID(event_id)},
                    )
                ).scalars()
            ),
            str(completable_id): list(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT action FROM talaqi.audit_events
                            WHERE target_id = :event_id ORDER BY created_at, id
                            """
                        ),
                        {"event_id": completable_id},
                    )
                ).scalars()
            ),
        }

    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "stale_revision"
    assert outsider_get.status_code == 403
    assert [response.status_code for response in outsider_denied] == [403] * 5
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert invalid_complete.status_code == 409
    assert invalid_complete.json()["error"]["code"] == "invalid_event_transition"
    assert duplicate.status_code == duplicate_replay.status_code == 201
    assert duplicate.json() == duplicate_replay.json()
    assert duplicate.json()["status"] == "draft"
    assert duplicate.json()["published_at"] is None
    assert cross_event_duplicate.status_code == 409
    assert cross_event_duplicate.json()["error"]["code"] == "idempotency_conflict"
    assert deleted.status_code == 204
    assert completable.status_code == 201
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert "event.cancelled" in lifecycle_actions[event_id]
    assert lifecycle_actions[str(completable_id)] == [
        "event.create",
        "event.publish",
        "event.completed",
    ]


@pytest.mark.asyncio
async def test_idempotency_replay_rechecks_current_authorization(
    event_engine: AsyncEngine,
) -> None:
    club_owner = await create_user(event_engine)
    club_admin = await create_user(event_engine)
    independent_owner = await create_user(event_engine)
    club_id = await create_club(event_engine, club_owner)
    await add_club_member(event_engine, club_id, club_admin, role="admin")
    club_body = complete_event_body(
        ownership_type="club",
        club_id=str(club_id),
        title="Revoked club replay",
        publish=False,
    )
    club_key = f"club-replay-{generate_uuid7()}"
    independent_body = complete_event_body(title="Suspended event replay")
    independent_key = f"event-replay-{generate_uuid7()}"
    source_body = complete_event_body(title="Duplicate source")
    duplicate_key = f"duplicate-replay-{generate_uuid7()}"
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_created = await client.post(
            "/api/v1/events",
            json=club_body,
            headers=club_admin.headers(idempotency_key=club_key),
        )
        independent_created = await client.post(
            "/api/v1/events",
            json=independent_body,
            headers=independent_owner.headers(idempotency_key=independent_key),
        )
        source_created = await client.post(
            "/api/v1/events",
            json=source_body,
            headers=independent_owner.headers(idempotency_key=f"source-{generate_uuid7()}"),
        )
        duplicated = await client.post(
            f"/api/v1/events/{source_created.json()['id']}/duplicate",
            headers=independent_owner.headers(idempotency_key=duplicate_key),
        )
        async with event_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    UPDATE talaqi.club_memberships
                    SET role = 'member'
                    WHERE club_id = :club_id AND user_id = :user_id
                    """
                ),
                {"club_id": club_id, "user_id": club_admin.user_id},
            )
            await connection.execute(
                text(
                    """
                    UPDATE talaqi.events
                    SET status = 'suspended', suspended_at = clock_timestamp(),
                        suspension_reason = 'safety_review'
                    WHERE id IN (:independent_id, :duplicate_id)
                    """
                ),
                {
                    "independent_id": UUID(independent_created.json()["id"]),
                    "duplicate_id": UUID(duplicated.json()["id"]),
                },
            )
        club_replay = await client.post(
            "/api/v1/events",
            json=club_body,
            headers=club_admin.headers(idempotency_key=club_key),
        )
        independent_replay = await client.post(
            "/api/v1/events",
            json=independent_body,
            headers=independent_owner.headers(idempotency_key=independent_key),
        )
        duplicate_replay = await client.post(
            f"/api/v1/events/{source_created.json()['id']}/duplicate",
            headers=independent_owner.headers(idempotency_key=duplicate_key),
        )

    assert club_created.status_code == 201
    assert independent_created.status_code == 201
    assert source_created.status_code == 201
    assert duplicated.status_code == 201
    assert [
        club_replay.status_code,
        independent_replay.status_code,
        duplicate_replay.status_code,
    ] == [
        403,
        403,
        403,
    ]


@pytest.mark.asyncio
async def test_revocation_and_source_suspension_serialize_with_event_mutations(
    event_engine: AsyncEngine,
) -> None:
    club_owner = await create_user(event_engine)
    club_admin = await create_user(event_engine)
    independent_owner = await create_user(event_engine)
    club_id = await create_club(event_engine, club_owner)
    await add_club_member(event_engine, club_id, club_admin, role="admin")
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        club_event = await client.post(
            "/api/v1/events",
            json=complete_event_body(
                ownership_type="club",
                club_id=str(club_id),
                title="Revocation race",
                publish=False,
            ),
            headers=club_admin.headers(idempotency_key=f"race-club-{generate_uuid7()}"),
        )
        membership_connection = await event_engine.connect()
        membership_transaction = await membership_connection.begin()
        try:
            await membership_connection.execute(
                text(
                    """
                    UPDATE talaqi.club_memberships
                    SET role = 'member'
                    WHERE club_id = :club_id AND user_id = :user_id
                    """
                ),
                {"club_id": club_id, "user_id": club_admin.user_id},
            )
            update_task = asyncio.create_task(
                client.patch(
                    f"/api/v1/events/{club_event.json()['id']}",
                    json={"revision": 1, "title": "Must wait for revocation"},
                    headers=club_admin.headers(),
                )
            )
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(update_task), timeout=0.25)
            await membership_transaction.commit()
            revoked_update = await asyncio.wait_for(update_task, timeout=5)
        finally:
            if membership_transaction.is_active:
                await membership_transaction.rollback()
            await membership_connection.close()

        source = await client.post(
            "/api/v1/events",
            json=complete_event_body(title="Suspension race source"),
            headers=independent_owner.headers(idempotency_key=f"race-source-{generate_uuid7()}"),
        )
        source_id = UUID(source.json()["id"])
        event_connection = await event_engine.connect()
        event_transaction = await event_connection.begin()
        try:
            await event_connection.execute(
                text(
                    """
                    UPDATE talaqi.events
                    SET status = 'suspended', suspended_at = clock_timestamp(),
                        suspension_reason = 'safety_review'
                    WHERE id = :event_id
                    """
                ),
                {"event_id": source_id},
            )
            duplicate_task = asyncio.create_task(
                client.post(
                    f"/api/v1/events/{source_id}/duplicate",
                    headers=independent_owner.headers(
                        idempotency_key=f"race-duplicate-{generate_uuid7()}"
                    ),
                )
            )
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(duplicate_task), timeout=0.25)
            await event_transaction.commit()
            suspended_duplicate = await asyncio.wait_for(duplicate_task, timeout=5)
        finally:
            if event_transaction.is_active:
                await event_transaction.rollback()
            await event_connection.close()

    assert club_event.status_code == 201
    assert revoked_update.status_code == 403
    assert source.status_code == 201
    assert suspended_duplicate.status_code == 403


@pytest.mark.asyncio
async def test_csrf_eligibility_suspension_and_independent_limit_fail_closed(
    event_engine: AsyncEngine,
) -> None:
    owner = await create_user(event_engine)
    unverified = await create_user(event_engine, verified=False)
    suspended_user = await create_user(event_engine, status="suspended")
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        missing_csrf = await client.post(
            "/api/v1/events",
            json=complete_event_body(publish=False),
            headers={
                "cookie": owner.cookie,
                "Idempotency-Key": f"csrf-{generate_uuid7()}",
            },
        )
        blocked = await client.post(
            "/api/v1/events",
            json=complete_event_body(publish=False),
            headers=unverified.headers(idempotency_key=f"unverified-{generate_uuid7()}"),
        )
        suspended_account = await client.post(
            "/api/v1/events",
            json=complete_event_body(publish=False),
            headers=suspended_user.headers(idempotency_key=f"suspended-account-{generate_uuid7()}"),
        )
        created = await asyncio.gather(
            *(
                client.post(
                    "/api/v1/events",
                    json=complete_event_body(title=f"Independent draft {index}", publish=False),
                    headers=owner.headers(idempotency_key=f"limit-{index}-{generate_uuid7()}"),
                )
                for index in range(4)
            )
        )
        event_id = next(response for response in created if response.status_code == 201).json()[
            "id"
        ]
        async with event_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    UPDATE talaqi.events
                    SET status = 'suspended', suspended_at = clock_timestamp(),
                        suspension_reason = 'safety_review',
                        cancellation_cutoff_minutes = 1440
                    WHERE id = :event_id
                    """
                ),
                {"event_id": UUID(event_id)},
            )
        suspended = await client.patch(
            f"/api/v1/events/{event_id}",
            json={"revision": 1, "title": "Cannot mutate"},
            headers=owner.headers(),
        )

    assert missing_csrf.status_code == 403
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "email_verification_required"
    assert suspended_account.status_code == 401
    assert sorted(response.status_code for response in created) == [201, 201, 201, 403]
    denied = next(response for response in created if response.status_code == 403)
    assert denied.json()["error"]["code"] == "independent_event_limit_reached"
    assert suspended.status_code == 403


@pytest.mark.asyncio
async def test_media_and_invalid_policy_inputs_fail_closed(event_engine: AsyncEngine) -> None:
    owner = await create_user(event_engine)
    other = await create_user(event_engine)
    owned_media = await create_media(event_engine, owner)
    foreign_media = await create_media(event_engine, other)
    pending_media = await create_media(event_engine, owner, status="pending")
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        accepted = await client.post(
            "/api/v1/events",
            json=complete_event_body(cover_media_id=str(owned_media), publish=False),
            headers=owner.headers(idempotency_key=f"owned-{generate_uuid7()}"),
        )
        foreign = await client.post(
            "/api/v1/events",
            json=complete_event_body(cover_media_id=str(foreign_media), publish=False),
            headers=owner.headers(idempotency_key=f"foreign-{generate_uuid7()}"),
        )
        pending = await client.post(
            "/api/v1/events",
            json=complete_event_body(cover_media_id=str(pending_media), publish=False),
            headers=owner.headers(idempotency_key=f"pending-{generate_uuid7()}"),
        )
        invalid_zone = await client.post(
            "/api/v1/events",
            json=complete_event_body(time_zone="Europe/Not-A-Zone"),
            headers=owner.headers(idempotency_key=f"zone-{generate_uuid7()}"),
        )
        unpaired_coordinates = await client.post(
            "/api/v1/events",
            json=complete_event_body(longitude=None),
            headers=owner.headers(idempotency_key=f"coords-{generate_uuid7()}"),
        )
        invalid_deadline = await client.post(
            "/api/v1/events",
            json=complete_event_body(
                registration_method="cash_organizer_confirmed",
                cash_expiry_minutes=60,
            ),
            headers=owner.headers(idempotency_key=f"deadline-{generate_uuid7()}"),
        )

    assert accepted.status_code == 201
    assert accepted.json()["cover_media_id"] == str(owned_media)
    assert foreign.status_code == 404
    assert pending.status_code == 404
    assert invalid_zone.status_code == 422
    assert invalid_zone.json()["error"]["code"] == "invalid_event"
    assert unpaired_coordinates.status_code == 422
    assert unpaired_coordinates.json()["error"]["code"] == "invalid_event"
    assert invalid_deadline.status_code == 422
    assert invalid_deadline.json()["error"]["code"] == "invalid_event_deadline"
