from decimal import ROUND_HALF_UP
from decimal import Decimal
from hmac import compare_digest
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.events.repository import (
    apply_event_registration_payment_state,
    mark_event_registration_paid,
    register_user_for_event,
)
from app.core.security import CurrentUser
from app.modules.events.schemas import EventDetail
from app.modules.payments.repository import (
    get_admin_payment,
    list_admin_payments,
    mark_payment_refunded,
    record_payment_admin_action,
    record_payment_webhook_audit,
    upsert_event_payment,
)
from app.modules.payments.schemas import (
    EventCheckoutSession,
    MoyasarWebhookPayload,
    MoyasarWebhookResult,
    PaymentAdminActionResult,
    PaymentAdminRecord,
    PaymentDisputeRequest,
    PaymentRefundRequest,
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
    zero_decimal_currencies = {
        "BIF",
        "CLP",
        "DJF",
        "GNF",
        "JPY",
        "KMF",
        "KRW",
        "MGA",
        "PYG",
        "RWF",
        "UGX",
        "VND",
        "VUV",
        "XAF",
        "XOF",
        "XPF",
    }
    multiplier = (
        Decimal("1") if currency.upper() in zero_decimal_currencies else Decimal("100")
    )
    return int((amount * multiplier).quantize(Decimal("1")))


def minor_units_to_amount(amount: int, currency: str) -> Decimal:
    zero_decimal_currencies = {
        "BIF",
        "CLP",
        "DJF",
        "GNF",
        "JPY",
        "KMF",
        "KRW",
        "MGA",
        "PYG",
        "RWF",
        "UGX",
        "VND",
        "VUV",
        "XAF",
        "XOF",
        "XPF",
    }
    if currency.upper() in zero_decimal_currencies:
        return Decimal(amount)
    return (Decimal(amount) / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def safe_return_path(return_path: str | None, fallback: str) -> str:
    if not return_path:
        return fallback
    if not return_path.startswith("/") or return_path.startswith("//"):
        return fallback
    return return_path


def normalize_idempotency_key(idempotency_key: str | None) -> str | None:
    if idempotency_key is None:
        return None
    normalized = idempotency_key.strip()
    if not normalized:
        return None
    return normalized[:160]


async def ensure_payment_pending_registration(
    session: AsyncSession,
    *,
    event_id: str,
    user_id: str,
    checkout_id: str | None,
    idempotency_key: str | None,
) -> None:
    await register_user_for_event(session, user_id=user_id, event_id=event_id)
    await apply_event_registration_payment_state(
        session,
        user_id=user_id,
        event_id=event_id,
        payment_status="pending",
        checkout_id=checkout_id,
        idempotency_key=normalize_idempotency_key(idempotency_key),
    )


async def create_event_checkout(
    session: AsyncSession,
    event: EventDetail,
    *,
    user_id: str,
    return_path: str | None = None,
    idempotency_key: str | None = None,
) -> EventCheckoutSession:
    if event.price_amount <= 0:
        raise CheckoutNotRequiredError

    checkout_return_path = safe_return_path(return_path, f"/explore/{event.id}")
    success_url = f"{settings.normalized_web_base_url}{checkout_return_path}?checkout=paid&event={event.id}"
    back_url = f"{settings.normalized_web_base_url}{checkout_return_path}?checkout=cancelled&event={event.id}"
    amount_minor = amount_to_minor_units(event.price_amount, event.currency)

    if not settings.moyasar_secret_key:
        checkout_id = f"dev-{uuid4()}"
        try:
            await ensure_payment_pending_registration(
                session,
                event_id=event.id,
                user_id=user_id,
                checkout_id=checkout_id,
                idempotency_key=idempotency_key,
            )
            await session.commit()
        except SQLAlchemyError as exc:
            await session.rollback()
            raise CheckoutProviderError(str(exc)) from exc

        return EventCheckoutSession(
            event_id=event.id,
            provider=settings.payment_provider,
            checkout_id=checkout_id,
            checkout_url=None,
            amount=event.price_amount,
            currency=event.currency,
            status="payment_pending",
            mode="development",
            message="Moyasar is not configured. Registration is waiting for payment confirmation.",
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
            "idempotency_key": normalize_idempotency_key(idempotency_key),
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
        raise CheckoutProviderError(
            "Moyasar invoice response did not include a checkout URL."
        )

    checkout_id = str(body.get("id") or uuid4())
    try:
        await ensure_payment_pending_registration(
            session,
            event_id=event.id,
            user_id=user_id,
            checkout_id=checkout_id,
            idempotency_key=idempotency_key,
        )
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise CheckoutProviderError(str(exc)) from exc

    return EventCheckoutSession(
        event_id=event.id,
        provider=settings.payment_provider,
        checkout_id=checkout_id,
        checkout_url=str(checkout_url),
        amount=event.price_amount,
        currency=event.currency,
        status=str(body.get("status") or "payment_pending"),
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

    data = payload.data
    metadata = read_metadata(data)
    event_id = str(metadata.get("event_id") or "").strip() or None
    user_id = str(metadata.get("user_id") or "").strip() or None
    provider_payment_id = str(data.get("id") or payload.id).strip()

    if payload.type != "payment_paid":
        try:
            await record_payment_webhook_audit(
                session,
                webhook_id=payload.id,
                event_type=payload.type,
                provider_payment_id=provider_payment_id,
                event_id=event_id,
                user_id=user_id,
                processing_status="ignored",
                raw_payload=payload.model_dump(mode="json"),
            )
            await session.commit()
        except SQLAlchemyError as exc:
            await session.rollback()
            raise WebhookProcessingError(str(exc)) from exc
        return MoyasarWebhookResult(
            received=True,
            event_type=payload.type,
            processed=False,
            message="Webhook event ignored.",
        )

    status = str(data.get("status") or "").lower()
    if status != "paid":
        try:
            await record_payment_webhook_audit(
                session,
                webhook_id=payload.id,
                event_type=payload.type,
                provider_payment_id=provider_payment_id,
                event_id=event_id,
                user_id=user_id,
                processing_status="ignored",
                raw_payload=payload.model_dump(mode="json"),
                error_message="Payment is not paid.",
            )
            await session.commit()
        except SQLAlchemyError as exc:
            await session.rollback()
            raise WebhookProcessingError(str(exc)) from exc
        return MoyasarWebhookResult(
            received=True,
            event_type=payload.type,
            processed=False,
            message="Payment is not paid.",
        )

    if not event_id or not user_id:
        try:
            await record_payment_webhook_audit(
                session,
                webhook_id=payload.id,
                event_type=payload.type,
                provider_payment_id=provider_payment_id,
                event_id=event_id,
                user_id=user_id,
                processing_status="failed",
                raw_payload=payload.model_dump(mode="json"),
                error_message="Missing event_id or user_id metadata.",
            )
            await session.commit()
        except SQLAlchemyError as exc:
            await session.rollback()
            raise WebhookProcessingError(str(exc)) from exc
        raise WebhookProcessingError(
            "Webhook payment metadata is missing event_id or user_id."
        )

    provider_invoice_id = data.get("invoice_id")
    currency = str(data.get("currency") or "SAR").upper()
    amount_minor = int(data.get("amount") or 0)
    amount = minor_units_to_amount(amount_minor, currency)
    idempotency_key = str(metadata.get("idempotency_key") or "").strip() or None

    try:
        payment_id = await upsert_event_payment(
            session,
            event_id=event_id,
            user_id=user_id,
            provider_payment_id=provider_payment_id,
            provider_invoice_id=str(provider_invoice_id)
            if provider_invoice_id
            else None,
            amount=amount,
            currency=currency,
            status=status,
            raw_payload=payload.model_dump(mode="json"),
        )
        await register_user_for_event(
            session,
            user_id=user_id,
            event_id=event_id,
        )
        registration = await mark_event_registration_paid(
            session,
            user_id=user_id,
            event_id=event_id,
            payment_id=payment_id,
            idempotency_key=normalize_idempotency_key(idempotency_key),
        )
        await record_payment_webhook_audit(
            session,
            webhook_id=payload.id,
            event_type=payload.type,
            provider_payment_id=provider_payment_id,
            event_id=event_id,
            user_id=user_id,
            processing_status="processed",
            raw_payload=payload.model_dump(mode="json"),
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


class AdminRequiredError(Exception):
    pass


class PaymentNotFoundError(Exception):
    pass


class PaymentAdminActionError(Exception):
    pass


def require_payment_admin(current_user: CurrentUser) -> None:
    if current_user.platform_role != "admin":
        raise AdminRequiredError


def normalize_admin_text(value: str | None, *, max_length: int = 1000) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized[:max_length]


async def list_admin_payment_records(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
    status_filter: str | None,
    limit: int,
    offset: int,
) -> list[PaymentAdminRecord]:
    require_payment_admin(current_user)
    rows = await list_admin_payments(
        session,
        status_filter=normalize_admin_text(status_filter, max_length=40),
        limit=limit,
        offset=offset,
    )
    return [PaymentAdminRecord.model_validate(row) for row in rows]


async def refund_admin_payment(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
    payment_id: str,
    payload: PaymentRefundRequest,
) -> PaymentAdminActionResult:
    require_payment_admin(current_user)
    payment = await get_admin_payment(session, payment_id=payment_id)
    if payment is None:
        raise PaymentNotFoundError
    if str(payment["status"]) == "refunded":
        raise PaymentAdminActionError("Payment is already refunded.")

    refund_amount = payload.amount or payment["amount"]
    try:
        action_id = await record_payment_admin_action(
            session,
            payment_id=payment_id,
            action_type="refund",
            status="processed",
            created_by=current_user.id,
            amount=refund_amount,
            currency=str(payment["currency"]),
            reason=normalize_admin_text(payload.reason),
            notes=normalize_admin_text(payload.notes),
            provider_reference=normalize_admin_text(
                payload.provider_reference, max_length=255
            ),
            raw_payload={
                "mode": "manual_admin_refund",
                "provider": payment["provider"],
                "provider_payment_id": payment["provider_payment_id"],
            },
        )
        states = await mark_payment_refunded(session, payment_id=payment_id)
        await session.commit()
    except (SQLAlchemyError, ValueError) as exc:
        await session.rollback()
        raise PaymentAdminActionError(str(exc)) from exc

    return PaymentAdminActionResult(
        action_id=action_id,
        payment_id=payment_id,
        action_type="refund",
        status="processed",
        payment_status=states["payment_status"] or "refunded",
        registration_payment_status=states["registration_payment_status"],
        message="Refund recorded and registration marked as refunded.",
    )


async def record_admin_payment_dispute(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
    payment_id: str,
    payload: PaymentDisputeRequest,
) -> PaymentAdminActionResult:
    require_payment_admin(current_user)
    payment = await get_admin_payment(session, payment_id=payment_id)
    if payment is None:
        raise PaymentNotFoundError

    try:
        action_id = await record_payment_admin_action(
            session,
            payment_id=payment_id,
            action_type="dispute",
            status="recorded",
            created_by=current_user.id,
            amount=None,
            currency=str(payment["currency"]),
            reason=normalize_admin_text(payload.reason),
            notes=normalize_admin_text(payload.notes),
            provider_reference=normalize_admin_text(
                payload.provider_reference, max_length=255
            ),
            raw_payload={
                "mode": "manual_admin_dispute",
                "provider": payment["provider"],
                "provider_payment_id": payment["provider_payment_id"],
            },
        )
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise PaymentAdminActionError(str(exc)) from exc

    return PaymentAdminActionResult(
        action_id=action_id,
        payment_id=payment_id,
        action_type="dispute",
        status="recorded",
        payment_status=str(payment["status"]),
        registration_payment_status=payment.get("registration_payment_status"),
        message="Dispute recorded for admin follow-up.",
    )
