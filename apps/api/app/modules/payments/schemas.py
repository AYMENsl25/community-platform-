from decimal import Decimal

from pydantic import BaseModel


class EventCheckoutRequest(BaseModel):
    return_path: str | None = None
    idempotency_key: str | None = None


class EventCheckoutSession(BaseModel):
    event_id: str
    provider: str
    checkout_id: str | None = None
    checkout_url: str | None = None
    amount: Decimal
    currency: str
    status: str
    mode: str
    message: str | None = None


class MoyasarWebhookPayload(BaseModel):
    id: str
    type: str
    created_at: str | None = None
    secret_token: str | None = None
    account_name: str | None = None
    live: bool | None = None
    data: dict


class MoyasarWebhookResult(BaseModel):
    received: bool
    event_type: str
    processed: bool
    payment_id: str | None = None
    registration_status: str | None = None
    message: str | None = None


class PaymentAdminRecord(BaseModel):
    id: str
    event_id: str
    event_title: str
    user_id: str
    user_email: str
    provider: str
    provider_payment_id: str
    provider_invoice_id: str | None = None
    amount: Decimal
    currency: str
    status: str
    paid_at: str | None = None
    created_at: str
    updated_at: str
    registration_status: str | None = None
    registration_payment_status: str | None = None


class PaymentRefundRequest(BaseModel):
    amount: Decimal | None = None
    reason: str | None = None
    notes: str | None = None
    provider_reference: str | None = None


class PaymentDisputeRequest(BaseModel):
    reason: str
    notes: str | None = None
    provider_reference: str | None = None


class PaymentAdminActionResult(BaseModel):
    action_id: str
    payment_id: str
    action_type: str
    status: str
    payment_status: str
    registration_payment_status: str | None = None
    message: str
