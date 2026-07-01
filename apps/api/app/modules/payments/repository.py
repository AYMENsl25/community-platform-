from collections.abc import Mapping
from decimal import Decimal
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def upsert_event_payment(
    session: AsyncSession,
    *,
    event_id: str,
    user_id: str,
    provider_payment_id: str,
    provider_invoice_id: str | None,
    amount: Decimal,
    currency: str,
    status: str,
    raw_payload: Mapping[str, Any],
) -> str:
    result = await session.execute(
        text(
            """
            INSERT INTO event_payments (
              event_id,
              user_id,
              provider,
              provider_payment_id,
              provider_invoice_id,
              amount,
              currency,
              status,
              raw_payload,
              paid_at
            )
            VALUES (
              CAST(:event_id AS uuid),
              CAST(:user_id AS uuid),
              'moyasar',
              :provider_payment_id,
              :provider_invoice_id,
              :amount,
              :currency,
              :status,
              CAST(:raw_payload AS jsonb),
              CASE WHEN :status = 'paid' THEN now() ELSE NULL END
            )
            ON CONFLICT (provider, provider_payment_id)
            DO UPDATE SET
              provider_invoice_id = EXCLUDED.provider_invoice_id,
              amount = EXCLUDED.amount,
              currency = EXCLUDED.currency,
              status = EXCLUDED.status,
              raw_payload = EXCLUDED.raw_payload,
              paid_at = CASE
                WHEN EXCLUDED.status = 'paid' THEN COALESCE(event_payments.paid_at, now())
                ELSE event_payments.paid_at
              END,
              updated_at = now()
            RETURNING id::text AS id
            """
        ),
        {
            "event_id": event_id,
            "user_id": user_id,
            "provider_payment_id": provider_payment_id,
            "provider_invoice_id": provider_invoice_id,
            "amount": amount,
            "currency": currency,
            "status": status,
            "raw_payload": json.dumps(raw_payload),
        },
    )
    return str(result.one()._mapping["id"])
