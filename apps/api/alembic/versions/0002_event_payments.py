"""add event payments table

Revision ID: 0002_event_payments
Revises: 0001_baseline
Create Date: 2026-07-01
"""

from alembic import op

revision = "0002_event_payments"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS event_payments (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          provider text NOT NULL DEFAULT 'moyasar',
          provider_payment_id text NOT NULL,
          provider_invoice_id text,
          amount numeric(10,2) NOT NULL,
          currency char(3) NOT NULL,
          status text NOT NULL,
          raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          paid_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT event_payments_amount_nonnegative CHECK (amount >= 0),
          CONSTRAINT event_payments_status_valid CHECK (
            status IN ('initiated', 'paid', 'authorized', 'failed', 'refunded', 'captured', 'voided', 'verified')
          ),
          CONSTRAINT event_payments_provider_payment_unique UNIQUE (provider, provider_payment_id)
        );

        DROP TRIGGER IF EXISTS event_payments_set_updated_at ON event_payments;
        CREATE TRIGGER event_payments_set_updated_at
        BEFORE UPDATE ON event_payments
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();

        CREATE INDEX IF NOT EXISTS event_payments_event_user_idx ON event_payments (event_id, user_id);
        CREATE INDEX IF NOT EXISTS event_payments_provider_invoice_idx ON event_payments (provider, provider_invoice_id);
        CREATE INDEX IF NOT EXISTS event_payments_status_idx ON event_payments (status, paid_at DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS event_payments;")
