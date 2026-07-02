from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.modules.events.schemas import EventDetail
from app.modules.payments import service
from app.core.security import CurrentUser
from app.modules.payments.schemas import (
    MoyasarWebhookPayload,
    PaymentDisputeRequest,
    PaymentRefundRequest,
)


class FakeSession:
    committed = False
    rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def make_event(
    *, price: Decimal = Decimal("25.00"), currency: str = "SAR"
) -> EventDetail:
    return EventDetail(
        id="33333333-3333-3333-3333-333333333333",
        club_id="44444444-4444-4444-4444-444444444444",
        created_by="11111111-1111-1111-1111-111111111111",
        title="AI Builders Night",
        slug="ai-builders-night",
        description="A paid event.",
        event_type="technology",
        starts_at=datetime(2026, 7, 10, 18, 0, tzinfo=UTC),
        ends_at=None,
        club_name="COMMUNITI AI Lab",
        city="Riyadh",
        country="Saudi Arabia",
        location_name="Innovation Hub",
        capacity=30,
        registered_count=0,
        waitlist_count=0,
        price_amount=price,
        currency=currency,
        cover_image_url=None,
        category_name="Technology",
        timezone="Asia/Riyadh",
        address=None,
        lat=None,
        lng=None,
        status="published",
        requires_approval=False,
        club_slug="communiti-ai-lab",
        club_logo_url=None,
        organizer_name="COMMUNITI Organizer",
        organizer_avatar_url=None,
        is_full=False,
    )


def make_paid_webhook() -> MoyasarWebhookPayload:
    return MoyasarWebhookPayload(
        id="evt_1",
        type="payment_paid",
        secret_token="secret",
        data={
            "id": "pay_1",
            "status": "paid",
            "amount": 2500,
            "currency": "SAR",
            "invoice_id": "inv_1",
            "metadata": {
                "event_id": "33333333-3333-3333-3333-333333333333",
                "user_id": "11111111-1111-1111-1111-111111111111",
                "idempotency_key": "idem-1",
            },
        },
    )


def test_amount_to_minor_units_for_sar() -> None:
    assert service.amount_to_minor_units(Decimal("25.50"), "SAR") == 2550


def test_return_path_rejects_absolute_urls() -> None:
    assert (
        service.safe_return_path("https://evil.example", "/explore/1") == "/explore/1"
    )
    assert service.safe_return_path("//evil.example", "/explore/1") == "/explore/1"
    assert service.safe_return_path("/explore/1", "/fallback") == "/explore/1"


@pytest.mark.asyncio
async def test_checkout_uses_development_pending_state_without_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service.settings, "moyasar_secret_key", None)
    calls: list[dict[str, object]] = []

    async def fake_ensure_payment_pending_registration(
        *args: object, **kwargs: object
    ) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(
        service,
        "ensure_payment_pending_registration",
        fake_ensure_payment_pending_registration,
    )

    fake_session = FakeSession()
    checkout = await service.create_event_checkout(
        fake_session,  # type: ignore[arg-type]
        make_event(),
        user_id="11111111-1111-1111-1111-111111111111",
        idempotency_key="idem-1",
    )

    assert checkout.mode == "development"
    assert checkout.status == "payment_pending"
    assert checkout.checkout_id is not None
    assert checkout.checkout_url is None
    assert fake_session.committed is True
    assert calls[0]["idempotency_key"] == "idem-1"


@pytest.mark.asyncio
async def test_free_event_does_not_need_checkout() -> None:
    with pytest.raises(service.CheckoutNotRequiredError):
        await service.create_event_checkout(
            FakeSession(),  # type: ignore[arg-type]
            make_event(price=Decimal("0")),
            user_id="11111111-1111-1111-1111-111111111111",
        )


def test_webhook_secret_uses_constant_time_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service.settings, "moyasar_webhook_secret", "secret")
    assert service.is_webhook_secret_valid("secret") is True
    assert service.is_webhook_secret_valid("wrong") is False


@pytest.mark.asyncio
async def test_paid_webhook_records_payment_and_confirms_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service.settings, "moyasar_webhook_secret", "secret")
    calls: dict[str, object] = {}

    async def fake_upsert_event_payment(*args: object, **kwargs: object) -> str:
        calls["payment"] = kwargs
        return "22222222-2222-2222-2222-222222222222"

    async def fake_register_user_for_event(*args: object, **kwargs: object) -> object:
        calls["registration"] = kwargs
        return object()

    async def fake_mark_event_registration_paid(
        *args: object, **kwargs: object
    ) -> object:
        calls["paid_registration"] = kwargs

        class Registration:
            status = "confirmed"

        return Registration()

    async def fake_record_payment_webhook_audit(*args: object, **kwargs: object) -> str:
        calls["audit"] = kwargs
        return "audit-id"

    monkeypatch.setattr(service, "upsert_event_payment", fake_upsert_event_payment)
    monkeypatch.setattr(
        service, "register_user_for_event", fake_register_user_for_event
    )
    monkeypatch.setattr(
        service, "mark_event_registration_paid", fake_mark_event_registration_paid
    )
    monkeypatch.setattr(
        service, "record_payment_webhook_audit", fake_record_payment_webhook_audit
    )

    fake_session = FakeSession()
    result = await service.process_moyasar_webhook(fake_session, make_paid_webhook())  # type: ignore[arg-type]

    assert result.processed is True
    assert result.registration_status == "confirmed"
    assert fake_session.committed is True
    assert calls["payment"]
    assert calls["registration"] == {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "event_id": "33333333-3333-3333-3333-333333333333",
    }
    assert calls["paid_registration"] == {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "event_id": "33333333-3333-3333-3333-333333333333",
        "payment_id": "22222222-2222-2222-2222-222222222222",
        "idempotency_key": "idem-1",
    }
    assert calls["audit"]


@pytest.mark.asyncio
async def test_duplicate_paid_webhook_delivery_uses_idempotent_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service.settings, "moyasar_webhook_secret", "secret")
    call_counts = {"payment": 0, "audit": 0, "paid_registration": 0}

    async def fake_upsert_event_payment(*args: object, **kwargs: object) -> str:
        call_counts["payment"] += 1
        return "22222222-2222-2222-2222-222222222222"

    async def fake_register_user_for_event(*args: object, **kwargs: object) -> object:
        return object()

    async def fake_mark_event_registration_paid(
        *args: object, **kwargs: object
    ) -> object:
        call_counts["paid_registration"] += 1

        class Registration:
            status = "confirmed"

        return Registration()

    async def fake_record_payment_webhook_audit(*args: object, **kwargs: object) -> str:
        call_counts["audit"] += 1
        return "audit-id"

    monkeypatch.setattr(service, "upsert_event_payment", fake_upsert_event_payment)
    monkeypatch.setattr(
        service, "register_user_for_event", fake_register_user_for_event
    )
    monkeypatch.setattr(
        service, "mark_event_registration_paid", fake_mark_event_registration_paid
    )
    monkeypatch.setattr(
        service, "record_payment_webhook_audit", fake_record_payment_webhook_audit
    )

    first = await service.process_moyasar_webhook(FakeSession(), make_paid_webhook())  # type: ignore[arg-type]
    second = await service.process_moyasar_webhook(FakeSession(), make_paid_webhook())  # type: ignore[arg-type]

    assert first.processed is True
    assert second.processed is True
    assert first.payment_id == second.payment_id
    assert call_counts == {"payment": 2, "audit": 2, "paid_registration": 2}


def make_admin() -> CurrentUser:
    return CurrentUser(
        id="99999999-9999-9999-9999-999999999999",
        clerk_user_id="clerk-admin",
        email="admin@example.com",
        platform_role="admin",
    )


@pytest.mark.asyncio
async def test_list_admin_payment_records_requires_admin() -> None:
    regular_user = CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        clerk_user_id="clerk-user",
        email="member@example.com",
    )

    with pytest.raises(service.AdminRequiredError):
        await service.list_admin_payment_records(
            FakeSession(),  # type: ignore[arg-type]
            current_user=regular_user,
            status_filter=None,
            limit=10,
            offset=0,
        )


@pytest.mark.asyncio
async def test_refund_admin_payment_records_action_and_marks_refunded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    async def fake_get_admin_payment(
        *args: object, **kwargs: object
    ) -> dict[str, object]:
        return {
            "id": "payment-id",
            "amount": Decimal("25.00"),
            "currency": "SAR",
            "status": "paid",
            "provider": "moyasar",
            "provider_payment_id": "pay_1",
            "registration_payment_status": "paid",
        }

    async def fake_record_payment_admin_action(*args: object, **kwargs: object) -> str:
        calls["action"] = kwargs
        return "action-id"

    async def fake_mark_payment_refunded(
        *args: object, **kwargs: object
    ) -> dict[str, str]:
        calls["refund"] = kwargs
        return {
            "payment_status": "refunded",
            "registration_payment_status": "refunded",
        }

    monkeypatch.setattr(service, "get_admin_payment", fake_get_admin_payment)
    monkeypatch.setattr(
        service, "record_payment_admin_action", fake_record_payment_admin_action
    )
    monkeypatch.setattr(service, "mark_payment_refunded", fake_mark_payment_refunded)

    fake_session = FakeSession()
    result = await service.refund_admin_payment(
        fake_session,  # type: ignore[arg-type]
        current_user=make_admin(),
        payment_id="payment-id",
        payload=PaymentRefundRequest(reason="customer request"),
    )

    assert result.payment_status == "refunded"
    assert result.registration_payment_status == "refunded"
    assert fake_session.committed is True
    assert calls["action"]
    assert calls["refund"] == {"payment_id": "payment-id"}


@pytest.mark.asyncio
async def test_record_admin_payment_dispute_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    async def fake_get_admin_payment(
        *args: object, **kwargs: object
    ) -> dict[str, object]:
        return {
            "id": "payment-id",
            "amount": Decimal("25.00"),
            "currency": "SAR",
            "status": "paid",
            "provider": "moyasar",
            "provider_payment_id": "pay_1",
            "registration_payment_status": "paid",
        }

    async def fake_record_payment_admin_action(*args: object, **kwargs: object) -> str:
        calls["action"] = kwargs
        return "action-id"

    monkeypatch.setattr(service, "get_admin_payment", fake_get_admin_payment)
    monkeypatch.setattr(
        service, "record_payment_admin_action", fake_record_payment_admin_action
    )

    fake_session = FakeSession()
    result = await service.record_admin_payment_dispute(
        fake_session,  # type: ignore[arg-type]
        current_user=make_admin(),
        payment_id="payment-id",
        payload=PaymentDisputeRequest(reason="chargeback opened"),
    )

    assert result.action_type == "dispute"
    assert result.status == "recorded"
    assert fake_session.committed is True
    assert calls["action"]
