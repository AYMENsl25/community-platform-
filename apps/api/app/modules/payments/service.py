from decimal import ROUND_HALF_UP
from decimal import Decimal
from hmac import compare_digest
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.events.repository import register_user_for_event
from app.modules.events.schemas import EventDetail
from app.modules.payments.repository import upsert_event_payment
from app.modules.payments.schemas import (
    EventCheckoutSession,
    MoyasarWebhookPayload,
    MoyasarWebhookResult,
)


class CheckoutNotRequiredError(Exception):
    pass


class CheckoutProviderError(Exception):
    pass


class InvalidWebhookSecretError(Exception):
    pass


class WebhookProcessingError(Exception):
    pass


def amount_to_minor_units(amount: Decimal, currency: str) -> int:
    zero_decimal_currencies = {"BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"}
    multiplier = Decimal("1") if currency.upper() in zero_decimal_currencies else Decimal("100")
    return int((amount * multiplier).quantize(Decimal("1")))


def minor_units_to_amount(amount: int, currency: str) -> Decimal:
    zero_decimal_currencies = {"BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"}
    if currency.upper() in zero_decimal_currencies:
        return Decimal(amount)
    return (Decimal(amount) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def safe_return_path(return_path: str | None, fallback: str) -> str:
    if not return_path:
        return fallback
    if not return_path.startswith("/") or return_path.startswith("//"):
        return fallback
    return return_path


async def create_event_checkout(
    event: EventDetail,
    *,
    user_id: str,
    return_path: str | None = None,
) -> EventCheckoutSession:
    if event.price_amount <= 0:
        raise CheckoutNotRequiredError

    checkout_return_path = safe_return_path(return_path, f"/explore/{event.id}")
    success_url = f"{settings.normalized_web_base_url}{checkout_return_path}?checkout=paid&event={event.id}"
    back_url = f"{settings.normalized_web_base_url}{checkout_return_path}?checkout=cancelled&event={event.id}"
    amount_minor = amount_to_minor_units(event.price_amount, event.currency)

    if not settings.moyasar_secret_key:
        return EventCheckoutSession(
            event_id=event.id,
            provider=settings.payment_provider,
            checkout_id=None,
            checkout_url=None,
            amount=event.price_amount,
            currency=event.currency,
            status="development_fallback",
            mode="development",
            message="Moyasar is not configured. Local checkout can be simulated.",
        )

    payload = {
        "amount": amount_minor,
        "currency": event.currency,
        "description": f"COMMUNITI event: {event.title}",
        "success_url": success_url,
        "back_url": back_url,
        "metadata": {
            "event_id": event.id,
            "club_id": event.club_id,
            "user_id": user_id,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{settings.moyasar_api_base_url.rstrip('/')}/invoices",
                auth=(settings.moyasar_secret_key, ""),
                json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise CheckoutProviderError(str(exc)) from exc

    body = response.json()
    checkout_url = body.get("url")
    if not checkout_url:
        raise CheckoutProviderError("Moyasar invoice response did not include a checkout URL.")

    return EventCheckoutSession(
        event_id=event.id,
        provider=settings.payment_provider,
        checkout_id=str(body.get("id") or uuid4()),
        checkout_url=str(checkout_url),
        amount=event.price_amount,
        currency=event.currency,
        status=str(body.get("status") or "initiated"),
        mode="live",
    )


def is_webhook_secret_valid(payload_secret: str | None) -> bool:
    if not settings.moyasar_webhook_secret:
        return settings.environment == "development"
    if not payload_secret:
        return False
    return compare_digest(payload_secret, settings.moyasar_webhook_secret)


def read_metadata(data: dict[str, Any]) -> dict[str, Any]:
    metadata = data.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


async def process_moyasar_webhook(
    session: AsyncSession,
    payload: MoyasarWebhookPayload,
) -> MoyasarWebhookResult:
    if not is_webhook_secret_valid(payload.secret_token):
        raise InvalidWebhookSecretError

    if payload.type != "payment_paid":
        return MoyasarWebhookResult(
            received=True,
            event_type=payload.type,
            processed=False,
            message="Webhook event ignored.",
        )

    data = payload.data
    status = str(data.get("status") or "").lower()
    if status != "paid":
        return MoyasarWebhookResult(
            received=True,
            event_type=payload.type,
            processed=False,
            message="Payment is not paid.",
        )

    metadata = read_metadata(data)
    event_id = str(metadata.get("event_id") or "").strip()
    user_id = str(metadata.get("user_id") or "").strip()
    if not event_id or not user_id:
        raise WebhookProcessingError("Webhook payment metadata is missing event_id or user_id.")

    provider_payment_id = str(data.get("id") or payload.id).strip()
    provider_invoice_id = data.get("invoice_id")
    currency = str(data.get("currency") or "SAR").upper()
    amount_minor = int(data.get("amount") or 0)
    amount = minor_units_to_amount(amount_minor, currency)

    try:
        payment_id = await upsert_event_payment(
            session,
            event_id=event_id,
            user_id=user_id,
            provider_payment_id=provider_payment_id,
            provider_invoice_id=str(provider_invoice_id) if provider_invoice_id else None,
            amount=amount,
            currency=currency,
            status=status,
            raw_payload=payload.model_dump(mode="json"),
        )
        registration = await register_user_for_event(
            session,
            user_id=user_id,
            event_id=event_id,
        )
        await session.commit()
    except (SQLAlchemyError, ValueError) as exc:
        await session.rollback()
        raise WebhookProcessingError(str(exc)) from exc

    return MoyasarWebhookResult(
        received=True,
        event_type=payload.type,
        processed=True,
        payment_id=payment_id,
        registration_status=registration.status,
    )
