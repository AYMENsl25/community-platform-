from __future__ import annotations

# ruff: noqa: RUF001 -- exact localized snapshot strings are intentional.
import asyncio
import smtplib
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.db.engine import build_session_factory
from talaqi.db.identifiers import generate_uuid7
from talaqi.outbox import OutboxRepository
from talaqi_worker.email import (
    SUPPORTED_LOCALES,
    ConsoleEmailProvider,
    EmailDeliveryWorker,
    EmailMessageRequest,
    ProductionEmailProvider,
    render_email,
    template_for,
)
from talaqi_worker.notifications import build_notification_worker

from apps.api.tests.events.fixtures import create_user

TEMPLATES = (
    "email_verification",
    "password_reset",
    "security",
    "membership",
    "registration",
    "cash_expiry",
    "promotion",
    "cancellation",
    "event_change",
)


def test_all_email_templates_have_four_locale_text_html_parity_and_private_venue_safety() -> None:
    forbidden = "Private managed address"
    for locale in SUPPORTED_LOCALES:
        for template in TEMPLATES:
            rendered = render_email(template, locale, action_url="https://talaqi.test/events/1")
            assert rendered.subject
            assert "https://talaqi.test/events/1" in rendered.text
            assert f'lang="{locale}"' in rendered.html
            assert ('dir="rtl"' in rendered.html) is (locale == "ar")
            assert forbidden not in rendered.text
            assert forbidden not in rendered.html
    assert render_email("email_verification", "en").subject == "Verify your Talaqi email"
    assert render_email("email_verification", "fr").subject == "Vérifiez votre e-mail Talaqi"
    assert render_email("email_verification", "tr").subject == "Talaqi e-postanızı doğrulayın"
    assert render_email("email_verification", "ar").subject == "تحقق من بريدك في تلاقي"
    assert render_email("security", "unsupported").subject == "Talaqi security notice"


@pytest.mark.asyncio
async def test_console_provider_contract_is_idempotency_keyed() -> None:
    provider = ConsoleEmailProvider()
    rendered = render_email("security", "en")
    request = EmailMessageRequest("person@example.test", rendered, "delivery-1")
    assert await provider.send(request) == "console:delivery-1"
    assert provider.messages == [request]
    assert await provider.send(request) == "console:delivery-1"
    assert provider.messages == [request]


class RecordingApiTransport:
    def __init__(self) -> None:
        self.keys: list[str] = []

    async def deliver(self, **values: str) -> str:
        self.keys.append(values["idempotency_key"])
        return "provider-message-42"


@pytest.mark.asyncio
async def test_production_provider_forwards_idempotency_key_and_provider_id() -> None:
    transport = RecordingApiTransport()
    provider = ProductionEmailProvider(transport)
    request = EmailMessageRequest(
        "person@example.test", render_email("security", "en"), "stable-key"
    )
    assert await provider.send(request) == "provider-message-42"
    assert transport.keys == ["stable-key"]


def test_registration_confirmation_and_waitlist_promotion_are_distinct() -> None:
    assert template_for("registration.confirmed", {}) == "registration"
    assert template_for("registration.confirmed", {"previous_state": "waitlisted"}) == "promotion"
    assert (
        template_for("registration.cash_pending", {"previous_state": "waitlisted"}) == "promotion"
    )


class FlakyProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def send(self, message: EmailMessageRequest) -> str:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary provider outage")
        return f"provider:{message.idempotency_key}"


class FencedCrashProvider:
    def __init__(self, engine: AsyncEngine, now: datetime) -> None:
        self._engine = engine
        self._now = now
        self.messages: list[EmailMessageRequest] = []
        self._seen: set[str] = set()

    async def send(self, message: EmailMessageRequest) -> str:
        if message.idempotency_key not in self._seen:
            self._seen.add(message.idempotency_key)
            self.messages.append(message)
            delivery_id = UUID(message.idempotency_key.rsplit(":", 1)[-1])
            async with self._engine.begin() as connection:
                await connection.execute(
                    text(
                        """
                        UPDATE talaqi.notification_deliveries
                        SET attempt_count = attempt_count + 1,
                            processing_started_at = :expired
                        WHERE id = :delivery_id
                        """
                    ),
                    {
                        "delivery_id": delivery_id,
                        "expired": self._now - timedelta(minutes=10),
                    },
                )
        return f"provider:{message.idempotency_key}"


class PermanentFailureProvider:
    async def send(self, message: EmailMessageRequest) -> str:
        del message
        raise smtplib.SMTPResponseException(550, b"recipient rejected SECRET_TOKEN Private body")


@pytest.mark.asyncio
async def test_email_worker_delivers_logs_provider_id_and_enforces_quota(
    worker_engine: AsyncEngine,
) -> None:
    user = await create_user(worker_engine)
    now = datetime.now(UTC)
    factory = build_session_factory(worker_engine)
    async with factory() as session, session.begin():
        await OutboxRepository(session).enqueue(
            aggregate_type="registration",
            aggregate_id=generate_uuid7(),
            event_type="registration.confirmed",
            payload={
                "user_id": str(user.user_id),
                "event_id": str(generate_uuid7()),
                "exact_address": "Private managed address",
                "latitude": 41.1,
                "directions": "Private directions",
                "private_body": "Private body",
            },
            deduplication_key="email:test:delivered",
            available_at=now,
        )
    notifications = build_notification_worker(factory, worker_id="notification-email-test")
    assert await notifications.run_once(now=now) == 1
    async with worker_engine.connect() as connection:
        intent_count = await connection.scalar(
            text(
                """
                SELECT count(*) FROM talaqi.email_delivery_intents AS intent
                JOIN talaqi.notification_deliveries AS delivery
                  ON delivery.id = intent.delivery_id
                WHERE delivery.status = 'pending'
                """
            )
        )
        assert intent_count == 1

    provider = ConsoleEmailProvider()
    worker = EmailDeliveryWorker(
        factory,
        provider,
        session_secret="email-worker-test-secret",  # pragma: allowlist secret
        web_public_url="https://talaqi.test",
    )
    result = await worker.run_once(now=now)
    async with worker_engine.connect() as connection:
        diagnostic = (
            await connection.execute(
                text(
                    """
                    SELECT delivery.status::text, delivery.attempt_count,
                           delivery.last_error_code,
                           count(reservation.delivery_id)
                    FROM talaqi.notification_deliveries AS delivery
                    LEFT JOIN talaqi.email_quota_reservations AS reservation
                      ON reservation.delivery_id = delivery.id
                    WHERE delivery.channel = 'email'
                    GROUP BY delivery.id
                    """
                )
            )
        ).one()
    assert (result, len(provider.messages), diagnostic) == (
        1,
        1,
        ("delivered", 1, None, 1),
    )
    assert "Private managed address" not in provider.messages[0].rendered.text

    async with worker_engine.connect() as connection:
        delivery = (
            await connection.execute(
                text(
                    """
                    SELECT status::text, attempt_count, provider_message_id,
                           last_error_code, delivered_at IS NOT NULL
                    FROM talaqi.notification_deliveries
                    WHERE channel = 'email'
                    """
                )
            )
        ).one()
        stored_parameters = await connection.scalar(
            text("SELECT parameters FROM talaqi.notifications LIMIT 1")
        )
    assert delivery == (
        "delivered",
        1,
        f"console:{provider.messages[0].idempotency_key}",
        None,
        True,
    )
    assert "Private managed address" not in repr(stored_parameters)
    assert "Private directions" not in repr(stored_parameters)
    assert "Private body" not in repr(stored_parameters)

    second = await create_user(worker_engine)
    async with factory() as session, session.begin():
        await OutboxRepository(session).enqueue(
            aggregate_type="registration",
            aggregate_id=generate_uuid7(),
            event_type="registration.waitlisted",
            payload={"user_id": str(second.user_id), "event_id": str(generate_uuid7())},
            deduplication_key="email:test:quota",
            available_at=now,
        )
    assert await notifications.run_once(now=now) == 1
    quota_worker = EmailDeliveryWorker(
        factory,
        provider,
        session_secret="email-worker-test-secret",
        web_public_url="https://talaqi.test",
        daily_recipient_quota=0,
    )
    assert await quota_worker.run_once(now=now) == 0
    async with worker_engine.connect() as connection:
        quota_status = await connection.execute(
            text(
                """
                SELECT delivery.status::text, delivery.last_error_code
                FROM talaqi.notification_deliveries AS delivery
                JOIN talaqi.notifications AS notification
                  ON notification.id = delivery.notification_id
                WHERE notification.recipient_user_id = :user_id
                  AND delivery.channel = 'email'
                """
            ),
            {"user_id": second.user_id},
        )
        assert quota_status.one() == ("retryable_failed", "daily_recipient_quota")
    next_day_worker = EmailDeliveryWorker(
        factory,
        provider,
        session_secret="email-worker-test-secret",
        web_public_url="https://talaqi.test",
        daily_recipient_quota=1,
    )
    assert await next_day_worker.run_once(now=now + timedelta(days=1, minutes=1)) == 1


@pytest.mark.asyncio
async def test_email_worker_classifies_retryable_provider_failure(
    worker_engine: AsyncEngine,
) -> None:
    user = await create_user(worker_engine)
    now = datetime.now(UTC)
    factory = build_session_factory(worker_engine)
    async with factory() as session, session.begin():
        await OutboxRepository(session).enqueue(
            aggregate_type="membership",
            aggregate_id=generate_uuid7(),
            event_type="membership.approved",
            payload={"user_id": str(user.user_id), "club_id": str(generate_uuid7())},
            deduplication_key="email:test:retry",
            available_at=now,
        )
    notifications = build_notification_worker(factory, worker_id="notification-email-retry")
    assert await notifications.run_once(now=now) == 1
    provider = FlakyProvider()
    worker = EmailDeliveryWorker(
        factory,
        provider,
        session_secret="email-worker-test-secret",
        web_public_url="https://talaqi.test",
    )
    assert await worker.run_once(now=now) == 0
    async with worker_engine.connect() as connection:
        failed = await connection.execute(
            text(
                "SELECT status::text, attempt_count, last_error_code "
                "FROM talaqi.notification_deliveries WHERE channel = 'email'"
            )
        )
        assert failed.one() == ("retryable_failed", 1, "runtimeerror")
    assert await worker.run_once(now=now + timedelta(minutes=3)) == 1
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_recovery_intent_survives_outbox_cleanup_and_uses_requested_locale(
    worker_engine: AsyncEngine,
) -> None:
    user = await create_user(worker_engine, profile_complete=False)
    now = datetime.now(UTC)
    token_id = generate_uuid7()
    factory = build_session_factory(worker_engine)
    async with factory() as session, session.begin():
        await OutboxRepository(session).enqueue(
            aggregate_type="user",
            aggregate_id=user.user_id,
            event_type="identity.email_verification_requested",
            payload={
                "user_id": str(user.user_id),
                "auth_token_id": str(token_id),
                "locale_hint": "ar",
                "template": "email_verification",
            },
            deduplication_key="email:test:recovery-retention",
            available_at=now,
        )
    notifications = build_notification_worker(factory, worker_id="notification-recovery")
    assert await notifications.run_once(now=now) == 1
    assert await notifications.cleanup_delivered(before=now + timedelta(days=1)) == 1

    provider = ConsoleEmailProvider()
    email_worker = EmailDeliveryWorker(
        factory,
        provider,
        session_secret="email-worker-test-secret",
        web_public_url="https://talaqi.test",
    )
    assert await email_worker.run_once(now=now) == 1
    assert len(provider.messages) == 1
    rendered = provider.messages[0].rendered
    assert 'lang="ar" dir="rtl"' in rendered.html
    assert "/verify-email?token=" in rendered.text
    async with worker_engine.connect() as connection:
        logged = await connection.execute(
            text(
                "SELECT provider_message_id, last_error_code "
                "FROM talaqi.notification_deliveries WHERE channel = 'email'"
            )
        )
        provider_id, error_code = logged.one()
    assert str(token_id) not in provider_id
    assert error_code is None


@pytest.mark.asyncio
async def test_concurrent_workers_reserve_only_one_last_daily_quota_slot(
    worker_engine: AsyncEngine,
) -> None:
    user = await create_user(worker_engine)
    now = datetime.now(UTC)
    factory = build_session_factory(worker_engine)
    async with factory() as session, session.begin():
        for index in range(2):
            await OutboxRepository(session).enqueue(
                aggregate_type="registration",
                aggregate_id=generate_uuid7(),
                event_type="registration.waitlisted",
                payload={"user_id": str(user.user_id), "event_id": str(generate_uuid7())},
                deduplication_key=f"email:test:concurrent-quota:{index}",
                available_at=now,
            )
    notifications = build_notification_worker(factory, worker_id="notification-quota-race")
    assert await notifications.run_once(now=now) == 2
    first_provider = ConsoleEmailProvider()
    second_provider = ConsoleEmailProvider()
    workers = [
        EmailDeliveryWorker(
            factory,
            provider,
            session_secret="email-worker-test-secret",
            web_public_url="https://talaqi.test",
            daily_recipient_quota=1,
        )
        for provider in (first_provider, second_provider)
    ]
    results = await asyncio.gather(
        workers[0].run_once(now=now, limit=1),
        workers[1].run_once(now=now, limit=1),
    )
    assert sum(results) == 1
    assert len(first_provider.messages) + len(second_provider.messages) == 1
    async with worker_engine.connect() as connection:
        states = list(
            (
                await connection.execute(
                    text(
                        "SELECT status::text FROM talaqi.notification_deliveries "
                        "WHERE channel = 'email' ORDER BY status::text"
                    )
                )
            ).scalars()
        )
        reservations = await connection.scalar(
            text("SELECT count(*) FROM talaqi.email_quota_reservations")
        )
    assert states == ["delivered", "retryable_failed"]
    assert reservations == 1


@pytest.mark.asyncio
async def test_stale_claim_replay_uses_provider_idempotency_and_fencing(
    worker_engine: AsyncEngine,
) -> None:
    user = await create_user(worker_engine)
    now = datetime.now(UTC)
    factory = build_session_factory(worker_engine)
    async with factory() as session, session.begin():
        await OutboxRepository(session).enqueue(
            aggregate_type="membership",
            aggregate_id=generate_uuid7(),
            event_type="membership.approved",
            payload={"user_id": str(user.user_id), "club_id": str(generate_uuid7())},
            deduplication_key="email:test:fenced-crash",
            available_at=now,
        )
    notifications = build_notification_worker(factory, worker_id="notification-fenced-email")
    assert await notifications.run_once(now=now) == 1
    provider = FencedCrashProvider(worker_engine, now)
    worker = EmailDeliveryWorker(
        factory,
        provider,
        session_secret="email-worker-test-secret",
        web_public_url="https://talaqi.test",
    )
    assert await worker.run_once(now=now) == 0
    assert await worker.run_once(now=now + timedelta(minutes=6)) == 1
    assert len(provider.messages) == 1


@pytest.mark.asyncio
async def test_smtp_5xx_is_permanent_without_logging_body(
    worker_engine: AsyncEngine, caplog: pytest.LogCaptureFixture
) -> None:
    user = await create_user(worker_engine)
    now = datetime.now(UTC)
    factory = build_session_factory(worker_engine)
    async with factory() as session, session.begin():
        await OutboxRepository(session).enqueue(
            aggregate_type="membership",
            aggregate_id=generate_uuid7(),
            event_type="membership.rejected",
            payload={"user_id": str(user.user_id), "club_id": str(generate_uuid7())},
            deduplication_key="email:test:permanent",
            available_at=now,
        )
    notifications = build_notification_worker(factory, worker_id="notification-permanent-email")
    assert await notifications.run_once(now=now) == 1
    worker = EmailDeliveryWorker(
        factory,
        PermanentFailureProvider(),
        session_secret="email-worker-test-secret",
        web_public_url="https://talaqi.test",
    )
    assert await worker.run_once(now=now) == 0
    async with worker_engine.connect() as connection:
        state = await connection.execute(
            text(
                "SELECT status::text, last_error_code, provider_message_id "
                "FROM talaqi.notification_deliveries WHERE channel = 'email'"
            )
        )
        assert state.one() == ("permanent_failed", "smtpresponseexception", None)
    assert "SECRET_TOKEN" not in caplog.text
    assert "Private body" not in caplog.text
