"""Make notification projection replay-safe.

Revision ID: 0010_notifications
Revises: 0009_registration_state_machine
Create Date: 2026-08-10
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from talaqi.db.safety import validate_test_database_url

revision: str = "0010_notifications"
down_revision: str | None = "0009_registration_state_machine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("outbox_event_id", sa.Uuid(), nullable=True),
        schema="talaqi",
    )
    op.create_foreign_key(
        "fk_notifications_outbox_event",
        "notifications",
        "outbox_events",
        ["outbox_event_id"],
        ["id"],
        source_schema="talaqi",
        referent_schema="talaqi",
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_notifications_outbox_event",
        "notifications",
        ["outbox_event_id"],
        unique=True,
        schema="talaqi",
        postgresql_where=sa.text("outbox_event_id IS NOT NULL"),
    )


def downgrade() -> None:
    validate_test_database_url(os.environ.get("TEST_DATABASE_URL"))
    op.drop_index("uq_notifications_outbox_event", table_name="notifications", schema="talaqi")
    op.drop_constraint(
        "fk_notifications_outbox_event",
        "notifications",
        schema="talaqi",
        type_="foreignkey",
    )
    op.drop_column("notifications", "outbox_event_id", schema="talaqi")
