"""Add audience and idempotency contracts for organizer communications.

Revision ID: 0012_communications
Revises: 0011_email_intents
Create Date: 2026-08-10
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from talaqi.db.safety import validate_test_database_url

revision: str = "0012_communications"
down_revision: str | None = "0011_email_intents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("announcements", "event_updates"):
        default_audience = "all_members" if table == "announcements" else "all_active"
        op.add_column(
            table,
            sa.Column("audience_key", sa.Text(), nullable=False, server_default=default_audience),
            schema="talaqi",
        )
        op.add_column(
            table,
            sa.Column("deduplication_key", sa.Text(), nullable=True),
            schema="talaqi",
        )
        op.execute(
            f"UPDATE talaqi.{table} SET deduplication_key = '{table}:' || id::text "
            "WHERE deduplication_key IS NULL"
        )
        op.alter_column(table, "deduplication_key", nullable=False, schema="talaqi")
        op.create_unique_constraint(
            f"uq_{table}_deduplication_key",
            table,
            ["deduplication_key"],
            schema="talaqi",
        )
        op.alter_column(table, "audience_key", server_default=None, schema="talaqi")
    op.add_column(
        "event_updates",
        sa.Column("source_revision", sa.Integer(), nullable=True),
        schema="talaqi",
    )
    for table, parent, parent_column in (
        ("announcement_recipients", "announcements", "announcement_id"),
        ("event_update_recipients", "event_updates", "event_update_id"),
    ):
        op.create_table(
            table,
            sa.Column(
                parent_column,
                sa.Uuid(),
                sa.ForeignKey(f"talaqi.{parent}.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "recipient_user_id",
                sa.Uuid(),
                sa.ForeignKey("talaqi.users.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            schema="talaqi",
        )
    op.execute(
        """
        INSERT INTO talaqi.announcement_recipients (
            announcement_id, recipient_user_id
        )
        SELECT announcement.id, membership.user_id
        FROM talaqi.announcements AS announcement
        JOIN talaqi.club_memberships AS membership
          ON membership.club_id = announcement.club_id
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO talaqi.event_update_recipients (
            event_update_id, recipient_user_id
        )
        SELECT event_update.id, registration.user_id
        FROM talaqi.event_updates AS event_update
        JOIN talaqi.registrations AS registration
          ON registration.event_id = event_update.event_id
         AND registration.state IN ('confirmed', 'cash_pending', 'waitlisted')
        ON CONFLICT DO NOTHING
        """
    )
    op.create_check_constraint(
        "ck_announcements_audience",
        "announcements",
        "audience_key IN ('all_members', 'admins')",
        schema="talaqi",
    )
    op.create_check_constraint(
        "ck_event_updates_audience",
        "event_updates",
        "audience_key IN ('all_active', 'confirmed', 'cash_pending', 'waitlisted')",
        schema="talaqi",
    )


def downgrade() -> None:
    validate_test_database_url(os.environ.get("TEST_DATABASE_URL"))
    op.drop_table("event_update_recipients", schema="talaqi")
    op.drop_table("announcement_recipients", schema="talaqi")
    op.drop_column("event_updates", "source_revision", schema="talaqi")
    for table in ("event_updates", "announcements"):
        op.drop_constraint(
            f"ck_{table}_audience",
            table,
            schema="talaqi",
            type_="check",
        )
        op.drop_constraint(
            f"uq_{table}_deduplication_key",
            table,
            schema="talaqi",
            type_="unique",
        )
        op.drop_column(table, "deduplication_key", schema="talaqi")
        op.drop_column(table, "audience_key", schema="talaqi")
