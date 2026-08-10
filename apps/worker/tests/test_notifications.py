from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.communications.service import NotificationProjectionHandler
from talaqi.db.engine import build_session_factory
from talaqi.db.identifiers import generate_uuid7
from talaqi.outbox import OutboxEvent, OutboxRepository
from talaqi_worker.notifications import build_notification_worker
from talaqi_worker.outbox import TransactionalOutboxWorker

from apps.api.tests.events.fixtures import app_for, create_user


async def enqueue_event(
    engine: AsyncEngine,
    *,
    event_type: str,
    user_id: UUID,
    key: str,
    now: datetime,
) -> None:
    factory = build_session_factory(engine)
    async with factory() as session, session.begin():
        await OutboxRepository(session).enqueue(
            aggregate_type="user",
            aggregate_id=user_id,
            event_type=event_type,
            payload={
                "user_id": str(user_id),
                "event_id": str(user_id),
                "auth_token_id": str(generate_uuid7()),
            },
            deduplication_key=key,
            available_at=now,
        )


@pytest.mark.asyncio
async def test_notification_projection_preferences_isolation_pagination_read_and_replay(
    worker_engine: AsyncEngine,
) -> None:
    first = await create_user(worker_engine)
    second = await create_user(worker_engine)
    now = datetime.now(UTC)
    app = app_for(worker_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        preference = await client.patch(
            "/api/v1/me/notifications/preferences",
            json={"event_email": False, "community_email": False},
            headers=first.headers(),
        )
        assert preference.status_code == 200, preference.text
        assert preference.json() == {
            "security_email": True,
            "event_email": False,
            "community_email": False,
        }
        for method, path, payload in (
            (
                "patch",
                "/api/v1/me/notifications/preferences",
                {"event_email": True, "community_email": True},
            ),
            ("post", "/api/v1/me/notifications/read-all", None),
            ("post", f"/api/v1/me/notifications/items/{first.user_id}/read", None),
        ):
            for headers in (
                {"cookie": first.cookie},
                {"cookie": first.cookie, "X-CSRF-Token": "mismatch"},
            ):
                response = await client.request(method, path, json=payload, headers=headers)
                assert response.status_code == 403

    await enqueue_event(
        worker_engine,
        event_type="registration.confirmed",
        user_id=first.user_id,
        key="notify:first:event",
        now=now,
    )
    await enqueue_event(
        worker_engine,
        event_type="identity.password_reset_requested",
        user_id=first.user_id,
        key="notify:first:security",
        now=now,
    )
    await enqueue_event(
        worker_engine,
        event_type="registration.waitlisted",
        user_id=second.user_id,
        key="notify:second:event",
        now=now,
    )
    worker = build_notification_worker(
        build_session_factory(worker_engine), worker_id="notification-worker"
    )
    assert await worker.run_once(now=now) == 2
    assert await worker.run_once(now=now) == 1
    assert await worker.run_once(now=now) == 0

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        page = await client.get("/api/v1/me/notifications?limit=1", headers=first.headers())
        assert page.status_code == 200, page.text
        assert len(page.json()["items"]) == 1
        assert page.json()["next_cursor"] is not None
        second_page = await client.get(
            "/api/v1/me/notifications",
            params={"limit": 1, "cursor": page.json()["next_cursor"]},
            headers=first.headers(),
        )
        assert second_page.status_code == 200, second_page.text
        assert len(second_page.json()["items"]) == 1
        first_ids = {page.json()["items"][0]["id"], second_page.json()["items"][0]["id"]}

        other_page = await client.get("/api/v1/me/notifications", headers=second.headers())
        assert other_page.status_code == 200
        assert len(other_page.json()["items"]) == 1
        other_id = other_page.json()["items"][0]["id"]
        denied = await client.post(
            f"/api/v1/me/notifications/items/{other_id}/read", headers=first.headers()
        )
        assert denied.status_code == 404

        count = await client.get("/api/v1/me/notifications/unread-count", headers=first.headers())
        assert count.json() == {"unread_count": 2}
        marked = await client.post(
            f"/api/v1/me/notifications/items/{next(iter(first_ids))}/read",
            headers=first.headers(),
        )
        assert marked.status_code == 200, marked.text
        count = await client.get("/api/v1/me/notifications/unread-count", headers=first.headers())
        assert count.json() == {"unread_count": 1}
        all_read = await client.post("/api/v1/me/notifications/read-all", headers=first.headers())
        assert all_read.json() == {"marked_count": 1}

    async with worker_engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT notification.type_key, delivery.channel::text AS channel
                        FROM talaqi.notifications AS notification
                        JOIN talaqi.notification_deliveries AS delivery
                          ON delivery.notification_id = notification.id
                        WHERE notification.recipient_user_id = :user_id
                        ORDER BY notification.type_key, channel
                        """
                    ),
                    {"user_id": first.user_id},
                )
            )
            .tuples()
            .all()
        )
        parameters = await connection.scalar(
            text(
                "SELECT parameters FROM talaqi.notifications "
                "WHERE recipient_user_id = :user_id LIMIT 1"
            ),
            {"user_id": first.user_id},
        )
    assert rows == [
        ("identity.password_reset_requested", "email"),
        ("identity.password_reset_requested", "in_app"),
        ("registration.confirmed", "in_app"),
    ]
    assert "auth_token_id" not in parameters


@pytest.mark.asyncio
async def test_projection_replay_is_idempotent_and_cleanup_preserves_notification(
    worker_engine: AsyncEngine,
) -> None:
    user = await create_user(worker_engine, profile_complete=False)
    now = datetime.now(UTC)
    await enqueue_event(
        worker_engine,
        event_type="identity.password_reset_requested",
        user_id=user.user_id,
        key="notify:crash-replay",
        now=now,
    )
    factory = build_session_factory(worker_engine)
    inner = NotificationProjectionHandler(factory)

    class ExpireAfterFirstProjection:
        def __init__(self) -> None:
            self.calls = 0

        async def deliver(self, event: OutboxEvent) -> None:
            await inner.deliver(event)
            self.calls += 1
            if self.calls == 1:
                async with worker_engine.begin() as connection:
                    await connection.execute(
                        text(
                            "UPDATE talaqi.outbox_events SET locked_until = :expired "
                            "WHERE id = :event_id"
                        ),
                        {"event_id": event.id, "expired": now - timedelta(seconds=1)},
                    )

    handler = ExpireAfterFirstProjection()
    worker = TransactionalOutboxWorker(
        factory,
        {"identity.password_reset_requested": handler},
        worker_id="notification-crash-worker",
        lease_duration=timedelta(seconds=1),
        jitter=lambda _ceiling: 0,
    )
    assert await worker.run_once(now=now) == 0
    assert await worker.run_once(now=now + timedelta(seconds=2)) == 1

    async with worker_engine.connect() as connection:
        counts = (
            await connection.execute(
                text(
                    """
                    SELECT count(DISTINCT notification.id), count(delivery.id)
                    FROM talaqi.notifications AS notification
                    JOIN talaqi.notification_deliveries AS delivery
                      ON delivery.notification_id = notification.id
                    WHERE notification.recipient_user_id = :user_id
                    """
                ),
                {"user_id": user.user_id},
            )
        ).one()
    assert counts == (1, 2)

    deleted = await worker.cleanup_delivered(before=now + timedelta(days=1))
    assert deleted == 1
    async with worker_engine.connect() as connection:
        retained = await connection.execute(
            text(
                "SELECT count(*), count(outbox_event_id) FROM talaqi.notifications "
                "WHERE recipient_user_id = :user_id"
            ),
            {"user_id": user.user_id},
        )
        assert retained.one() == (1, 0)
