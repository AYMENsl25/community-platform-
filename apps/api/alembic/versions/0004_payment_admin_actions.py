"""add payment admin action audit log

Revision ID: 0004_payment_admin_actions
Revises: 0003_registration_payment_state
Create Date: 2026-07-03
"""

from alembic import op

revision = "0004_payment_admin_actions"
down_revision = "0003_registration_payment_state"
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
        CREATE TABLE IF NOT EXISTS payment_admin_actions (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          payment_id uuid NOT NULL REFERENCES event_payments(id) ON DELETE CASCADE,
          action_type text NOT NULL,
          status text NOT NULL DEFAULT 'recorded',
          amount numeric(10,2),
          currency char(3),
          reason text,
          provider_reference text,
          notes text,
          created_by uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
          raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT payment_admin_actions_type_valid CHECK (
            action_type IN ('refund', 'dispute')
          ),
          CONSTRAINT payment_admin_actions_status_valid CHECK (
            status IN ('recorded', 'pending_provider', 'processed', 'failed', 'cancelled')
          ),
          CONSTRAINT payment_admin_actions_amount_nonnegative CHECK (
            amount IS NULL OR amount >= 0
          )
        );

        DROP TRIGGER IF EXISTS payment_admin_actions_set_updated_at
          ON payment_admin_actions;
        CREATE TRIGGER payment_admin_actions_set_updated_at
        BEFORE UPDATE ON payment_admin_actions
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();

        CREATE INDEX IF NOT EXISTS payment_admin_actions_payment_idx
          ON payment_admin_actions (payment_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS payment_admin_actions_type_status_idx
          ON payment_admin_actions (action_type, status, created_at DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payment_admin_actions;")
