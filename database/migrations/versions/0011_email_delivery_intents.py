"""Persist private recovery-email delivery intent beyond outbox retention.

Revision ID: 0011_email_intents
Revises: 0010_notifications
Create Date: 2026-08-10
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from talaqi.db.safety import validate_test_database_url

revision: str = "0011_email_intents"
down_revision: str | None = "0010_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_delivery_intents",
        sa.Column("delivery_id", sa.Uuid(), primary_key=True),
        sa.Column("auth_token_id", sa.Uuid(), nullable=True),
        sa.Column("locale_hint", sa.Text(), nullable=False, server_default="en"),
        sa.ForeignKeyConstraint(
            ["delivery_id"],
            ["talaqi.notification_deliveries.id"],
            ondelete="CASCADE",
            name="fk_email_intents_delivery",
        ),
        sa.CheckConstraint(
            "locale_hint IN ('ar', 'en', 'fr', 'tr')",
            name="ck_email_intents_locale",
        ),
        schema="talaqi",
    )
    op.execute(
        """
        INSERT INTO talaqi.email_delivery_intents (
            delivery_id, auth_token_id, locale_hint
        )
        SELECT delivery.id,
               CASE
                 WHEN event.payload ->> 'auth_token_id' ~
                      '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
                 THEN CAST(event.payload ->> 'auth_token_id' AS uuid)
                 ELSE NULL
               END,
               CASE
                 WHEN COALESCE(event.payload ->> 'locale_hint', profile.locale, 'en')
                      IN ('ar', 'en', 'fr', 'tr')
                 THEN COALESCE(event.payload ->> 'locale_hint', profile.locale, 'en')
                 ELSE 'en'
               END
        FROM talaqi.notification_deliveries AS delivery
        JOIN talaqi.notifications AS notification
          ON notification.id = delivery.notification_id
        LEFT JOIN talaqi.outbox_events AS event
          ON event.id = notification.outbox_event_id
        LEFT JOIN talaqi.profiles AS profile
          ON profile.user_id = notification.recipient_user_id
        WHERE delivery.channel = 'email'
        ON CONFLICT (delivery_id) DO NOTHING
        """
    )
    op.create_table(
        "email_quota_reservations",
        sa.Column("delivery_id", sa.Uuid(), primary_key=True),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=False),
        sa.Column("quota_date", sa.Date(), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["delivery_id"],
            ["talaqi.notification_deliveries.id"],
            ondelete="CASCADE",
            name="fk_email_quota_delivery",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["talaqi.users.id"],
            ondelete="CASCADE",
            name="fk_email_quota_user",
        ),
        sa.UniqueConstraint(
            "recipient_user_id",
            "quota_date",
            "slot",
            name="uq_email_quota_slot",
        ),
        sa.CheckConstraint("slot > 0", name="ck_email_quota_slot_positive"),
        schema="talaqi",
    )


def downgrade() -> None:
    validate_test_database_url(os.environ.get("TEST_DATABASE_URL"))
    op.drop_table("email_quota_reservations", schema="talaqi")
    op.drop_table("email_delivery_intents", schema="talaqi")
