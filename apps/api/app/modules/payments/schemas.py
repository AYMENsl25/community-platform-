from decimal import Decimal

from pydantic import BaseModel


class EventCheckoutRequest(BaseModel):
    return_path: str | None = None


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
