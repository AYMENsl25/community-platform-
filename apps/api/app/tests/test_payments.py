from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.modules.events.schemas import EventDetail
from app.modules.payments import service
from app.modules.payments.schemas import MoyasarWebhookPayload


def make_event(*, price: Decimal = Decimal("25.00"), currency: str = "SAR") -> EventDetail:
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


def test_amount_to_minor_units_for_sar() -> None:
    assert service.amount_to_minor_units(Decimal("25.50"), "SAR") == 2550


def test_return_path_rejects_absolute_urls() -> None:
    assert service.safe_return_path("https://evil.example", "/explore/1") == "/explore/1"
    assert service.safe_return_path("//evil.example", "/explore/1") == "/explore/1"
    assert service.safe_return_path("/explore/1", "/fallback") == "/explore/1"


@pytest.mark.asyncio
async def test_checkout_uses_development_fallback_without_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service.settings, "moyasar_secret_key", None)

    checkout = await service.create_event_checkout(
        make_event(),
        user_id="11111111-1111-1111-1111-111111111111",
    )

    assert checkout.mode == "development"
    assert checkout.status == "development_fallback"
    assert checkout.checkout_url is None


@pytest.mark.asyncio
async def test_free_event_does_not_need_checkout() -> None:
    with pytest.raises(service.CheckoutNotRequiredError):
        await service.create_event_checkout(
            make_event(price=Decimal("0")),
            user_id="11111111-1111-1111-1111-111111111111",
        )


def test_webhook_secret_uses_constant_time_comparison(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service.settings, "moyasar_webhook_secret", "secret")
    assert service.is_webhook_secret_valid("secret") is True
    assert service.is_webhook_secret_valid("wrong") is False


@pytest.mark.asyncio
async def test_paid_webhook_records_payment_and_registers_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service.settings, "moyasar_webhook_secret", "secret")
    calls: dict[str, object] = {}

    class FakeSession:
        committed = False
        rolled_back = False

        async def commit(self) -> None:
            self.committed = True

        async def rollback(self) -> None:
            self.rolled_back = True

    async def fake_upsert_event_payment(*args: object, **kwargs: object) -> str:
        calls["payment"] = kwargs
        return "payment-id"

    async def fake_register_user_for_event(*args: object, **kwargs: object) -> object:
        calls["registration"] = kwargs

        class Registration:
            status = "confirmed"

        return Registration()

    monkeypatch.setattr(service, "upsert_event_payment", fake_upsert_event_payment)
    monkeypatch.setattr(service, "register_user_for_event", fake_register_user_for_event)

    payload = MoyasarWebhookPayload(
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
            },
        },
    )

    fake_session = FakeSession()
    result = await service.process_moyasar_webhook(fake_session, payload)  # type: ignore[arg-type]

    assert result.processed is True
    assert result.registration_status == "confirmed"
    assert fake_session.committed is True
    assert calls["payment"]  # payment was recorded
    assert calls["registration"] == {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "event_id": "33333333-3333-3333-3333-333333333333",
    }
