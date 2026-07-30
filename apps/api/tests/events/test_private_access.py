from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.events.access_rate_limits import LazyEventAccessRateLimiter
from talaqi.events.access_tokens import PrivateLinkTokenCodec
from talaqi.main import create_app
from talaqi.moderation.repository import ModerationRepository
from talaqi.platform import ApiError
from talaqi.security import InMemoryRateLimiter, RateLimitDecision, RateLimitPolicy

from .fixtures import (
    AuthenticatedUser,
    add_club_member,
    app_for,
    complete_event_body,
    create_club,
    create_user,
    event_settings,
)


async def _create_event(
    client: httpx.AsyncClient,
    owner: AuthenticatedUser,
    *,
    visibility: str = "private_link",
    exact_venue_is_public: bool = False,
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/events",
        json=complete_event_body(
            visibility=visibility,
            exact_venue_is_public=exact_venue_is_public,
        ),
        headers=owner.headers(idempotency_key=f"private-event-{owner.user_id}"),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _issue(
    client: httpx.AsyncClient,
    owner: AuthenticatedUser,
    event_id: object,
    *,
    rotate: bool = False,
) -> httpx.Response:
    suffix = "/rotate" if rotate else ""
    return await client.post(
        f"/api/v1/events/{event_id}/private-link{suffix}",
        json={"expires_in_days": 30},
        headers=owner.headers(),
    )


@pytest.mark.asyncio
async def test_private_link_lifecycle_is_hash_only_generic_and_never_public(
    event_engine: AsyncEngine,
    capfd: pytest.CaptureFixture[str],
) -> None:
    owner = await create_user(event_engine)
    outsider = await create_user(event_engine)
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        event = await _create_event(client, owner)
        event_id = event["id"]
        public_fetch = await client.get(f"/api/v1/events/{event_id}")
        no_csrf = await client.post(
            f"/api/v1/events/{event_id}/private-link",
            json={"expires_in_days": 30},
            headers={"cookie": owner.cookie},
        )
        denied = await _issue(client, outsider, event_id)
        issued = await _issue(client, owner, event_id)
        raw = issued.json()["copy_value"]
        denied_rotate = await _issue(client, outsider, event_id, rotate=True)
        denied_revoke = await client.delete(
            f"/api/v1/events/{event_id}/private-link",
            headers=outsider.headers(),
        )
        no_csrf_rotate = await client.post(
            f"/api/v1/events/{event_id}/private-link/rotate",
            json={"expires_in_days": 30},
            headers={"cookie": owner.cookie},
        )
        no_csrf_revoke = await client.delete(
            f"/api/v1/events/{event_id}/private-link",
            headers={"cookie": owner.cookie},
        )
        body_resolve = await client.post(
            "/api/v1/event-access/resolve",
            json={"private_link": raw},
        )
        header_resolve = await client.post(
            "/api/v1/event-access/resolve",
            headers={"Authorization": f"PrivateLink {raw}"},
        )
        query_rejected = await client.post(
            "/api/v1/event-access/resolve",
            params={"private_link": raw},
        )
        rotated = await _issue(client, owner, event_id, rotate=True)
        rotated_raw = rotated.json()["copy_value"]
        old_after_rotation = await client.post(
            "/api/v1/event-access/resolve",
            json={"private_link": raw},
        )
        new_after_rotation = await client.post(
            "/api/v1/event-access/resolve",
            json={"private_link": rotated_raw},
        )
        revoked = await client.delete(
            f"/api/v1/events/{event_id}/private-link",
            headers=owner.headers(),
        )
        after_revoke = await client.post(
            "/api/v1/event-access/resolve",
            json={"private_link": rotated_raw},
        )
        invalid = await client.post(
            "/api/v1/event-access/resolve",
            json={"private_link": "not-a-private-link"},
        )

    assert public_fetch.status_code == 404
    assert no_csrf.status_code == denied.status_code == 403
    assert issued.status_code == 201
    assert len(raw) == 43
    assert len(base64.urlsafe_b64decode(raw + "=")) == 32

    assert denied_rotate.status_code == denied_revoke.status_code == 403
    assert no_csrf_rotate.status_code == no_csrf_revoke.status_code == 403
    assert body_resolve.status_code == header_resolve.status_code == 200
    assert body_resolve.json()["exact_address"] is None
    assert body_resolve.json()["latitude"] is None
    assert body_resolve.json()["longitude"] is None
    assert body_resolve.headers["Cache-Control"] == "private, no-store"
    assert body_resolve.headers["Referrer-Policy"] == "no-referrer"
    assert query_rejected.status_code == 404
    assert rotated.status_code == 200
    assert rotated_raw != raw
    assert old_after_rotation.status_code == 404
    assert new_after_rotation.status_code == 200
    assert revoked.status_code == 204
    assert after_revoke.status_code == invalid.status_code == 404
    for response in (after_revoke, invalid):
        error = response.json()["error"]
        assert error["code"] == "not_found"
        assert error["message_key"] == "errors.not_found"
        assert error["field_errors"] == []

    captured_logs = capfd.readouterr()
    async with event_engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT token_hash, revoked_at
                        FROM talaqi.event_invite_tokens
                        WHERE event_id = :event_id
                        ORDER BY created_at
                        """
                    ),
                    {"event_id": UUID(str(event_id))},
                )
            )
            .mappings()
            .all()
        )
        audit = await connection.scalar(
            text(
                """
                SELECT coalesce(string_agg(safe_after::text, ' '), '')
                FROM talaqi.audit_events
                WHERE target_id = :event_id
                """
            ),
            {"event_id": UUID(str(event_id))},
        )
        idempotency = await connection.scalar(
            text(
                """
                SELECT coalesce(string_agg(coalesce(response_body::text, ''), ' '), '')
                FROM talaqi.idempotency_keys
                WHERE user_id = :owner
                """
            ),
            {"owner": owner.user_id},
        )
    assert len(rows) == 2
    assert all(len(row["token_hash"]) == 32 for row in rows)
    assert all(row["revoked_at"] is not None for row in rows)
    assert raw not in str(audit)
    assert rotated_raw not in str(audit)
    assert raw not in str(idempotency)
    assert rotated_raw not in str(idempotency)
    assert raw not in captured_logs.out
    assert raw not in captured_logs.err
    assert rotated_raw not in captured_logs.out
    assert rotated_raw not in captured_logs.err
    assert raw not in repr(after_revoke.json())
    assert rotated_raw not in repr(after_revoke.json())


@pytest.mark.asyncio
async def test_exact_venue_projection_obeys_complete_audience_matrix(
    event_engine: AsyncEngine,
) -> None:
    owner = await create_user(event_engine)
    ordinary = await create_user(event_engine)
    confirmed = await create_user(event_engine)
    cash_valid = await create_user(event_engine)
    cash_expired = await create_user(event_engine)
    cancelled = await create_user(event_engine)
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        event = await _create_event(client, owner, visibility="public")
        event_id = UUID(str(event["id"]))
        now = datetime.now(UTC)
        async with event_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    INSERT INTO talaqi.registrations (
                        id, event_id, user_id, method, state, seat_held,
                        cash_expires_at, confirmed_at, cancelled_at
                    ) VALUES
                        (uuidv7(), :event, :confirmed, 'free', 'confirmed', true,
                         NULL, :now, NULL),
                        (uuidv7(), :event, :cash_valid, 'cash_organizer_confirmed',
                         'cash_pending', true, :future, NULL, NULL),
                        (uuidv7(), :event, :cash_expired, 'cash_organizer_confirmed',
                         'cash_pending', true, :past, NULL, NULL),
                        (uuidv7(), :event, :cancelled, 'free', 'cancelled', false,
                         NULL, NULL, :now)
                    """
                ),
                {
                    "event": event_id,
                    "confirmed": confirmed.user_id,
                    "cash_valid": cash_valid.user_id,
                    "cash_expired": cash_expired.user_id,
                    "cancelled": cancelled.user_id,
                    "now": now,
                    "future": now + timedelta(hours=1),
                    "past": now - timedelta(hours=1),
                },
            )
        responses: dict[str, httpx.Response] = {
            "anonymous": await client.get(f"/api/v1/events/{event_id}"),
            "ordinary": await client.get(
                f"/api/v1/events/{event_id}", headers={"cookie": ordinary.cookie}
            ),
            "owner": await client.get(
                f"/api/v1/events/{event_id}", headers={"cookie": owner.cookie}
            ),
            "confirmed": await client.get(
                f"/api/v1/events/{event_id}", headers={"cookie": confirmed.cookie}
            ),
            "cash_valid": await client.get(
                f"/api/v1/events/{event_id}", headers={"cookie": cash_valid.cookie}
            ),
            "cash_expired": await client.get(
                f"/api/v1/events/{event_id}", headers={"cookie": cash_expired.cookie}
            ),
            "cancelled": await client.get(
                f"/api/v1/events/{event_id}", headers={"cookie": cancelled.cookie}
            ),
        }
        async with event_engine.begin() as connection:
            await connection.execute(
                text("UPDATE talaqi.events SET exact_venue_is_public = true WHERE id = :event"),
                {"event": event_id},
            )
        explicitly_public = await client.get(f"/api/v1/events/{event_id}")

    assert all(response.status_code == 200 for response in responses.values())
    exact_allowed = {"owner", "confirmed", "cash_valid"}
    for audience, response in responses.items():
        expected = "Private managed address" if audience in exact_allowed else None
        assert response.json()["exact_address"] == expected
        assert (response.json()["latitude"] is not None) is (audience in exact_allowed)
        assert (response.json()["longitude"] is not None) is (audience in exact_allowed)
    assert responses["anonymous"].headers["Cache-Control"].startswith("public")
    assert responses["owner"].headers["Cache-Control"] == "private, no-store"
    assert explicitly_public.json()["exact_address"] == "Private managed address"


@pytest.mark.asyncio
async def test_expiry_and_concurrent_rotation_leave_only_one_working_link(
    event_engine: AsyncEngine,
) -> None:
    owner = await create_user(event_engine)
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        event = await _create_event(client, owner)
        event_id = event["id"]
        first = await _issue(client, owner, event_id)
        async with event_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    UPDATE talaqi.event_invite_tokens
                    SET expires_at = clock_timestamp() - interval '1 second'
                    WHERE event_id = :event
                    """
                ),
                {"event": UUID(str(event_id))},
            )
        expired = await client.post(
            "/api/v1/event-access/resolve",
            json={"private_link": first.json()["copy_value"]},
        )
        rotations = await asyncio.gather(
            _issue(client, owner, event_id, rotate=True),
            _issue(client, owner, event_id, rotate=True),
        )
        resolution = await asyncio.gather(
            *[
                client.post(
                    "/api/v1/event-access/resolve",
                    json={"private_link": response.json()["copy_value"]},
                )
                for response in rotations
            ]
        )
    assert expired.status_code == 404
    assert [response.status_code for response in rotations] == [200, 200]
    assert sorted(response.status_code for response in resolution) == [200, 404]
    async with event_engine.connect() as connection:
        active = await connection.scalar(
            text(
                """
                SELECT count(*)
                FROM talaqi.event_invite_tokens
                WHERE event_id = :event AND revoked_at IS NULL
                  AND expires_at > clock_timestamp()
                """
            ),
            {"event": UUID(str(event_id))},
        )
    assert active == 1


class _TokenPrefixDenyingLimiter:
    def __init__(self) -> None:
        self.buckets: list[str] = []

    async def consume(
        self,
        bucket_id: str,
        policy: RateLimitPolicy,
    ) -> RateLimitDecision:
        self.buckets.append(bucket_id)
        denied = len(self.buckets) == 2
        return RateLimitDecision(
            allowed=not denied,
            remaining=0,
            retry_after_seconds=int(policy.window_seconds) if denied else 0,
        )


@pytest.mark.asyncio
async def test_resolver_rate_limit_uses_only_opaque_bucket_ids(
    event_engine: AsyncEngine,
) -> None:
    limiter = _TokenPrefixDenyingLimiter()
    factory = async_sessionmaker(event_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(
        event_settings(),
        session_factory=factory,
        event_access_rate_limiter=limiter,
    )
    raw = PrivateLinkTokenCodec(b"rate-limit-test-secret").issue()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        response = await client.post(
            "/api/v1/event-access/resolve",
            json={"private_link": raw},
        )
    assert response.status_code == 429
    assert len(limiter.buckets) == 2
    assert all(len(bucket) == 64 for bucket in limiter.buckets)
    assert all(raw not in bucket for bucket in limiter.buckets)


@pytest.mark.asyncio
async def test_shared_link_fanout_is_not_exhausted_by_ten_holders_and_client_abuse_is_capped() -> (
    None
):
    runtime = LazyEventAccessRateLimiter(
        event_settings,
        provider=InMemoryRateLimiter(),
    )
    raw = PrivateLinkTokenCodec(b"fanout-rate-limit-secret").issue()
    for index in range(40):
        await runtime.check(client_host=f"198.51.100.{index}", raw_token=raw)

    for _ in range(30):
        await runtime.check(client_host="203.0.113.9", raw_token=raw)
    with pytest.raises(ApiError) as denied:
        await runtime.check(client_host="203.0.113.9", raw_token=raw)
    assert denied.value.code == "rate_limited"


def test_private_link_codec_is_256_bit_domain_separated_and_openapi_is_body_or_header_only() -> (
    None
):
    secret = b"private-link-domain-separation-secret"
    codec = PrivateLinkTokenCodec(secret)
    issued = {codec.issue() for _ in range(64)}
    assert len(issued) == 64
    assert all(len(base64.urlsafe_b64decode(value + "=")) == 32 for value in issued)
    sample = next(iter(issued))
    other_domain_digest = hmac.new(
        secret,
        b"talaqi:other-capability:v1\x00" + sample.encode("ascii"),
        hashlib.sha256,
    ).digest()
    assert codec.digest(sample) != other_domain_digest

    document = create_app().openapi()
    paths = document["paths"]
    issued_schema = document["components"]["schemas"]["PrivateLinkIssuedResponse"]
    assert "fragment_url" not in issued_schema["properties"]
    assert "fragment_url" not in issued_schema["required"]
    resolver = paths["/api/v1/event-access/resolve"]["post"]
    assert resolver["requestBody"].get("required", False) is False
    assert {parameter["name"] for parameter in resolver["parameters"]} == {"authorization"}
    assert all("private_link" not in path for path in paths)


@pytest.mark.asyncio
async def test_club_private_link_mutations_enforce_every_manager_boundary(
    event_engine: AsyncEngine,
) -> None:
    owner = await create_user(event_engine)
    admin = await create_user(event_engine)
    member = await create_user(event_engine)
    other_owner = await create_user(event_engine)
    other_admin = await create_user(event_engine)
    club_id = await create_club(event_engine, owner)
    other_club_id = await create_club(event_engine, other_owner)
    await add_club_member(event_engine, club_id, admin, role="admin")
    await add_club_member(event_engine, club_id, member, role="member")
    await add_club_member(event_engine, other_club_id, other_admin, role="admin")
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        created = await client.post(
            "/api/v1/events",
            json=complete_event_body(
                ownership_type="club",
                club_id=str(club_id),
                visibility="private_link",
            ),
            headers=owner.headers(idempotency_key=f"club-private-{owner.user_id}"),
        )
        assert created.status_code == 201
        event_id = created.json()["id"]
        issued = await _issue(client, admin, event_id)
        raw = issued.json()["copy_value"]
        owner_projection = await client.post(
            "/api/v1/event-access/resolve",
            json={"private_link": raw},
            headers={"cookie": owner.cookie},
        )
        admin_projection = await client.post(
            "/api/v1/event-access/resolve",
            json={"private_link": raw},
            headers={"cookie": admin.cookie},
        )
        member_projection = await client.post(
            "/api/v1/event-access/resolve",
            json={"private_link": raw},
            headers={"cookie": member.cookie},
        )
        denied: list[httpx.Response] = []
        for actor in (member, other_admin):
            denied.extend(
                [
                    await _issue(client, actor, event_id),
                    await _issue(client, actor, event_id, rotate=True),
                    await client.delete(
                        f"/api/v1/events/{event_id}/private-link",
                        headers=actor.headers(),
                    ),
                ]
            )
        owner_rotated = await _issue(client, owner, event_id, rotate=True)
        owner_revoked = await client.delete(
            f"/api/v1/events/{event_id}/private-link",
            headers=owner.headers(),
        )
    assert issued.status_code == 201
    assert owner_projection.json()["exact_address"] == "Private managed address"
    assert admin_projection.json()["exact_address"] == "Private managed address"
    assert member_projection.json()["exact_address"] is None
    assert [response.status_code for response in denied] == [403] * 6
    assert owner_rotated.status_code == 200
    assert owner_revoked.status_code == 204


@pytest.mark.asyncio
async def test_moderation_suspend_restore_permanently_revokes_private_link(
    event_engine: AsyncEngine,
) -> None:
    owner = await create_user(event_engine)
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        event = await _create_event(client, owner)
        event_id = UUID(str(event["id"]))
        issued = await _issue(client, owner, event_id)
        raw = issued.json()["copy_value"]

        async with AsyncSession(event_engine) as session, session.begin():
            repository = ModerationRepository(session)
            target = await repository.get_target("event", event_id, for_update=True)
            assert target is not None
            suspended = await repository.apply_target_action(
                target,
                "suspend",
                reason="security_review",
                now=datetime.now(UTC),
            )
            assert suspended is not None

        async with AsyncSession(event_engine) as session, session.begin():
            repository = ModerationRepository(session)
            target = await repository.get_target("event", event_id, for_update=True)
            assert target is not None
            restored = await repository.apply_target_action(
                target,
                "restore",
                reason="security_review_complete",
                now=datetime.now(UTC),
            )
            assert restored is not None

        after_restore = await client.post(
            "/api/v1/event-access/resolve",
            json={"private_link": raw},
        )

    assert issued.status_code == 201
    assert suspended.status == "suspended"
    assert restored.status == "published"
    assert after_restore.status_code == 404
    async with event_engine.connect() as connection:
        revoked_at = await connection.scalar(
            text(
                """
                SELECT revoked_at
                FROM talaqi.event_invite_tokens
                WHERE event_id = :event
                """
            ),
            {"event": event_id},
        )
    assert revoked_at is not None


@pytest.mark.asyncio
async def test_draft_suspended_and_visibility_changed_events_cannot_resurrect_links(
    event_engine: AsyncEngine,
) -> None:
    owner = await create_user(event_engine)
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        event = await _create_event(client, owner)
        event_id = UUID(str(event["id"]))
        issued = await _issue(client, owner, event_id)
        raw = issued.json()["copy_value"]
        async with event_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    UPDATE talaqi.events
                    SET status = 'suspended', suspended_at = clock_timestamp(),
                        suspension_reason = 'security_review'
                    WHERE id = :event
                    """
                ),
                {"event": event_id},
            )
        suspended = await client.post(
            "/api/v1/event-access/resolve",
            json={"private_link": raw},
        )
        async with event_engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    UPDATE talaqi.events
                    SET status = 'draft', published_at = NULL, suspended_at = NULL,
                        suspension_reason = NULL
                    WHERE id = :event
                    """
                ),
                {"event": event_id},
            )
        draft = await client.post(
            "/api/v1/event-access/resolve",
            json={"private_link": raw},
        )
        republished = await client.patch(
            f"/api/v1/events/{event_id}",
            json={"revision": 1, "publish": True, "visibility": "private_link"},
            headers=owner.headers(),
        )
        publicized = await client.patch(
            f"/api/v1/events/{event_id}",
            json={"revision": 2, "visibility": "public"},
            headers=owner.headers(),
        )
        privatized = await client.patch(
            f"/api/v1/events/{event_id}",
            json={"revision": 3, "visibility": "private_link"},
            headers=owner.headers(),
        )
        resurrected = await client.post(
            "/api/v1/event-access/resolve",
            json={"private_link": raw},
        )
    assert issued.status_code == 201
    assert suspended.status_code == draft.status_code == 404
    assert republished.status_code == publicized.status_code == privatized.status_code == 200
    assert resurrected.status_code == 404


def test_deployed_event_access_rate_limiter_fails_closed_without_provider() -> None:
    from talaqi.events.access_rate_limits import LazyEventAccessRateLimiter

    deployed = event_settings().model_copy(update={"environment": "production"})
    runtime = LazyEventAccessRateLimiter(lambda: deployed)
    with pytest.raises(RuntimeError, match="rate limiter provider is required"):
        runtime.resolve()


@pytest.mark.asyncio
async def test_unlimited_public_event_preserves_nullable_capacity(
    event_engine: AsyncEngine,
) -> None:
    owner = await create_user(event_engine)
    app = app_for(event_engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        created = await client.post(
            "/api/v1/events",
            json=complete_event_body(visibility="public", capacity=None),
            headers=owner.headers(idempotency_key=f"unlimited-event-{owner.user_id}"),
        )
        assert created.status_code == 201, created.text
        detail = await client.get(f"/api/v1/events/{created.json()['id']}")

    assert detail.status_code == 200
    assert detail.json()["capacity"] is None
    assert detail.json()["available_places"] is None


@pytest.mark.asyncio
async def test_managed_preview_preserves_valid_incomplete_draft(
    event_engine: AsyncEngine,
) -> None:
    owner = await create_user(event_engine)
    app = app_for(event_engine)
    body = complete_event_body(
        publish=False,
        category_slug=None,
        country_code=None,
        city_slug=None,
        start_at=None,
        end_at=None,
        time_zone=None,
        capacity=None,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        created = await client.post(
            "/api/v1/events",
            json=body,
            headers=owner.headers(idempotency_key=f"incomplete-draft-{owner.user_id}"),
        )
        assert created.status_code == 201, created.text
        managed = await client.get(
            f"/api/v1/events/{created.json()['id']}/managed",
            headers={"cookie": owner.cookie},
        )
    assert managed.status_code == 200
    assert managed.json()["status"] == "draft"
    assert managed.json()["category_slug"] is None
    assert managed.json()["country_code"] is None
    assert managed.json()["city_slug"] is None
    assert managed.json()["exact_address"] == "Private managed address"
