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
