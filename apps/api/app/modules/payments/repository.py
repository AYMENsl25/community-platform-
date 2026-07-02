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


async def record_payment_webhook_audit(
    session: AsyncSession,
    *,
    webhook_id: str,
    event_type: str,
    provider_payment_id: str | None,
    event_id: str | None,
    user_id: str | None,
    processing_status: str,
    raw_payload: Mapping[str, Any],
    error_message: str | None = None,
) -> str:
    result = await session.execute(
        text(
            """
            INSERT INTO payment_webhook_audit_logs (
              provider,
              webhook_id,
              event_type,
              provider_payment_id,
              event_id,
              user_id,
              processing_status,
              payload,
              error_message,
              processed_at
            )
            VALUES (
              'moyasar',
              :webhook_id,
              :event_type,
              :provider_payment_id,
              CAST(:event_id AS uuid),
              CAST(:user_id AS uuid),
              :processing_status,
              CAST(:raw_payload AS jsonb),
              :error_message,
              CASE WHEN :processing_status IN ('processed', 'ignored', 'failed') THEN now() ELSE NULL END
            )
            ON CONFLICT (provider, webhook_id)
            DO UPDATE SET
              event_type = EXCLUDED.event_type,
              provider_payment_id = COALESCE(EXCLUDED.provider_payment_id, payment_webhook_audit_logs.provider_payment_id),
              event_id = COALESCE(EXCLUDED.event_id, payment_webhook_audit_logs.event_id),
              user_id = COALESCE(EXCLUDED.user_id, payment_webhook_audit_logs.user_id),
              processing_status = EXCLUDED.processing_status,
              payload = EXCLUDED.payload,
              error_message = EXCLUDED.error_message,
              processed_at = COALESCE(EXCLUDED.processed_at, payment_webhook_audit_logs.processed_at),
              delivery_count = payment_webhook_audit_logs.delivery_count + 1,
              updated_at = now()
            RETURNING id::text AS id
            """
        ),
        {
            "webhook_id": webhook_id,
            "event_type": event_type,
            "provider_payment_id": provider_payment_id,
            "event_id": event_id,
            "user_id": user_id,
            "processing_status": processing_status,
            "raw_payload": json.dumps(raw_payload),
            "error_message": error_message,
        },
    )
    return str(result.one()._mapping["id"])


async def list_admin_payments(
    session: AsyncSession,
    *,
    status_filter: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            """
            SELECT
              ep.id::text AS id,
              ep.event_id::text AS event_id,
              e.title AS event_title,
              ep.user_id::text AS user_id,
              u.email AS user_email,
              ep.provider,
              ep.provider_payment_id,
              ep.provider_invoice_id,
              ep.amount,
              ep.currency,
              ep.status,
              ep.paid_at,
              ep.created_at,
              ep.updated_at,
              er.status::text AS registration_status,
              er.payment_status AS registration_payment_status
            FROM event_payments ep
            JOIN events e ON e.id = ep.event_id
            JOIN users u ON u.id = ep.user_id
            LEFT JOIN event_registrations er
              ON er.event_id = ep.event_id
             AND er.user_id = ep.user_id
            WHERE (:status_filter IS NULL OR ep.status = CAST(:status_filter AS text))
            ORDER BY ep.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"status_filter": status_filter, "limit": limit, "offset": offset},
    )
    return [dict(row._mapping) for row in result]


async def get_admin_payment(
    session: AsyncSession,
    *,
    payment_id: str,
) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            """
            SELECT
              ep.id::text AS id,
              ep.event_id::text AS event_id,
              e.title AS event_title,
              ep.user_id::text AS user_id,
              u.email AS user_email,
              ep.provider,
              ep.provider_payment_id,
              ep.provider_invoice_id,
              ep.amount,
              ep.currency,
              ep.status,
              ep.paid_at,
              ep.created_at,
              ep.updated_at,
              er.status::text AS registration_status,
              er.payment_status AS registration_payment_status
            FROM event_payments ep
            JOIN events e ON e.id = ep.event_id
            JOIN users u ON u.id = ep.user_id
            LEFT JOIN event_registrations er
              ON er.event_id = ep.event_id
             AND er.user_id = ep.user_id
            WHERE ep.id = CAST(:payment_id AS uuid)
            LIMIT 1
            """
        ),
        {"payment_id": payment_id},
    )
    row = result.first()
    return dict(row._mapping) if row else None


async def record_payment_admin_action(
    session: AsyncSession,
    *,
    payment_id: str,
    action_type: str,
    status: str,
    created_by: str,
    amount: Decimal | None,
    currency: str | None,
    reason: str | None,
    notes: str | None,
    provider_reference: str | None,
    raw_payload: Mapping[str, Any],
) -> str:
    result = await session.execute(
        text(
            """
            INSERT INTO payment_admin_actions (
              payment_id,
              action_type,
              status,
              amount,
              currency,
              reason,
              notes,
              provider_reference,
              created_by,
              raw_payload
            )
            VALUES (
              CAST(:payment_id AS uuid),
              :action_type,
              :status,
              :amount,
              :currency,
              :reason,
              :notes,
              :provider_reference,
              CAST(:created_by AS uuid),
              CAST(:raw_payload AS jsonb)
            )
            RETURNING id::text AS id
            """
        ),
        {
            "payment_id": payment_id,
            "action_type": action_type,
            "status": status,
            "amount": amount,
            "currency": currency,
            "reason": reason,
            "notes": notes,
            "provider_reference": provider_reference,
            "created_by": created_by,
            "raw_payload": json.dumps(raw_payload),
        },
    )
    return str(result.one()._mapping["id"])


async def mark_payment_refunded(
    session: AsyncSession,
    *,
    payment_id: str,
) -> dict[str, str | None]:
    payment = await session.execute(
        text(
            """
            UPDATE event_payments
            SET status = 'refunded', updated_at = now()
            WHERE id = CAST(:payment_id AS uuid)
            RETURNING id::text AS id, event_id::text AS event_id, user_id::text AS user_id, status
            """
        ),
        {"payment_id": payment_id},
    )
    row = payment.first()
    if row is None:
        raise ValueError("Payment not found")
    mapped = dict(row._mapping)
    await session.execute(
        text(
            """
            UPDATE event_registrations
            SET payment_status = 'refunded',
                status = 'cancelled',
                cancelled_at = COALESCE(cancelled_at, now()),
                updated_at = now()
            WHERE event_id = CAST(:event_id AS uuid)
              AND user_id = CAST(:user_id AS uuid)
              AND payment_id = CAST(:payment_id AS uuid)
            """
        ),
        {
            "event_id": mapped["event_id"],
            "user_id": mapped["user_id"],
            "payment_id": payment_id,
        },
    )
    return {
        "payment_status": str(mapped["status"]),
        "registration_payment_status": "refunded",
    }
