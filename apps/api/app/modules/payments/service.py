from decimal import Decimal
from uuid import uuid4

import httpx

from app.core.config import settings
from app.modules.events.schemas import EventDetail
from app.modules.payments.schemas import EventCheckoutSession


class CheckoutNotRequiredError(Exception):
    pass


class CheckoutProviderError(Exception):
    pass


def amount_to_minor_units(amount: Decimal, currency: str) -> int:
    zero_decimal_currencies = {"BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"}
    multiplier = Decimal("1") if currency.upper() in zero_decimal_currencies else Decimal("100")
    return int((amount * multiplier).quantize(Decimal("1")))


def safe_return_path(return_path: str | None, fallback: str) -> str:
    if not return_path:
        return fallback
    if not return_path.startswith("/") or return_path.startswith("//"):
        return fallback
    return return_path


async def create_event_checkout(event: EventDetail, *, return_path: str | None = None) -> EventCheckoutSession:
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
