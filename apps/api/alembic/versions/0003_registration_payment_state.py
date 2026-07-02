"""add registration payment state and webhook audit logs

Revision ID: 0003_registration_payment_state
Revises: 0002_event_payments
Create Date: 2026-07-01
"""

from alembic import op

revision = "0003_registration_payment_state"
down_revision = "0002_event_payments"
branch_labels = None
depends_on = None


def execute_statements(sql: str) -> None:
    bind = op.get_bind()
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            bind.exec_driver_sql(statement)


def upgrade() -> None:
    execute_statements(
        """
        ALTER TABLE event_payments
          DROP CONSTRAINT IF EXISTS event_payments_status_valid;

        ALTER TABLE event_payments
          ADD CONSTRAINT event_payments_status_valid CHECK (
            status IN (
              'initiated',
              'pending',
              'paid',
              'authorized',
              'failed',
              'cancelled',
              'refunded',
              'captured',
              'voided',
              'verified'
            )
          );

        ALTER TABLE event_registrations
          ADD COLUMN IF NOT EXISTS payment_required boolean NOT NULL DEFAULT false,
          ADD COLUMN IF NOT EXISTS payment_status text NOT NULL DEFAULT 'not_required',
          ADD COLUMN IF NOT EXISTS payment_id uuid REFERENCES event_payments(id) ON DELETE SET NULL,
          ADD COLUMN IF NOT EXISTS checkout_id text,
          ADD COLUMN IF NOT EXISTS idempotency_key text;

        ALTER TABLE event_registrations
          DROP CONSTRAINT IF EXISTS event_registrations_payment_status_valid;

        ALTER TABLE event_registrations
          ADD CONSTRAINT event_registrations_payment_status_valid CHECK (
            payment_status IN (
              'not_required',
              'unpaid',
              'pending',
              'paid',
              'failed',
              'cancelled',
              'refunded'
            )
          );

        UPDATE event_registrations er
        SET payment_required = (e.price_amount > 0),
            payment_status = CASE
              WHEN e.price_amount > 0 THEN 'unpaid'
              ELSE 'not_required'
            END
        FROM events e
        WHERE e.id = er.event_id
          AND er.payment_status = 'not_required';

        CREATE UNIQUE INDEX IF NOT EXISTS event_registrations_idempotency_idx
          ON event_registrations (event_id, user_id, idempotency_key)
          WHERE idempotency_key IS NOT NULL;

        CREATE INDEX IF NOT EXISTS event_registrations_payment_status_idx
          ON event_registrations (payment_status, status);

        CREATE TABLE IF NOT EXISTS payment_webhook_audit_logs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          provider text NOT NULL DEFAULT 'moyasar',
          webhook_id text NOT NULL,
          event_type text NOT NULL,
          provider_payment_id text,
          event_id uuid REFERENCES events(id) ON DELETE SET NULL,
          user_id uuid REFERENCES users(id) ON DELETE SET NULL,
          processing_status text NOT NULL DEFAULT 'received',
          delivery_count integer NOT NULL DEFAULT 1,
          payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          error_message text,
          received_at timestamptz NOT NULL DEFAULT now(),
          processed_at timestamptz,
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT payment_webhook_audit_status_valid CHECK (
            processing_status IN ('received', 'processed', 'ignored', 'failed')
          ),
          CONSTRAINT payment_webhook_audit_delivery_count_positive CHECK (
            delivery_count > 0
          ),
          CONSTRAINT payment_webhook_audit_unique UNIQUE (provider, webhook_id)
        );

        DROP TRIGGER IF EXISTS payment_webhook_audit_logs_set_updated_at
          ON payment_webhook_audit_logs;
        CREATE TRIGGER payment_webhook_audit_logs_set_updated_at
        BEFORE UPDATE ON payment_webhook_audit_logs
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();

        CREATE INDEX IF NOT EXISTS payment_webhook_audit_event_idx
          ON payment_webhook_audit_logs (event_id, user_id);
        CREATE INDEX IF NOT EXISTS payment_webhook_audit_provider_payment_idx
          ON payment_webhook_audit_logs (provider, provider_payment_id);
        """
    )


def downgrade() -> None:
    execute_statements(
        """
        DROP TABLE IF EXISTS payment_webhook_audit_logs;
        DROP INDEX IF EXISTS event_registrations_payment_status_idx;
        DROP INDEX IF EXISTS event_registrations_idempotency_idx;

        ALTER TABLE event_registrations
          DROP CONSTRAINT IF EXISTS event_registrations_payment_status_valid;
        ALTER TABLE event_registrations
          DROP COLUMN IF EXISTS idempotency_key,
          DROP COLUMN IF EXISTS checkout_id,
          DROP COLUMN IF EXISTS payment_id,
          DROP COLUMN IF EXISTS payment_status,
          DROP COLUMN IF EXISTS payment_required;

        ALTER TABLE event_payments
          DROP CONSTRAINT IF EXISTS event_payments_status_valid;
        ALTER TABLE event_payments
          ADD CONSTRAINT event_payments_status_valid CHECK (
            status IN ('initiated', 'paid', 'authorized', 'failed', 'refunded', 'captured', 'voided', 'verified')
          );
        """
    )
