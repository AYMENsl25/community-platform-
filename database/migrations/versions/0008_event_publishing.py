"""Allow optional capacity for otherwise complete published events.

Revision ID: 0008_event_publishing
Revises: 0007_moderation_priority
Create Date: 2026-07-29
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from talaqi.db.safety import validate_test_database_url

revision: str = "0008_event_publishing"
down_revision: str | None = "0007_moderation_priority"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PUBLISHED_FIELDS = """
status NOT IN ('published', 'cancelled', 'completed', 'suspended')
OR (length(btrim(description)) > 0
    AND category_id IS NOT NULL AND country_id IS NOT NULL AND city_id IS NOT NULL
    AND start_at IS NOT NULL AND end_at IS NOT NULL AND time_zone IS NOT NULL
    AND registration_method IS NOT NULL
    AND cancellation_cutoff_minutes IS NOT NULL)
"""

_PUBLISHED_FIELDS_WITH_CAPACITY = """
status NOT IN ('published', 'cancelled', 'completed', 'suspended')
OR (length(btrim(description)) > 0
    AND category_id IS NOT NULL AND country_id IS NOT NULL AND city_id IS NOT NULL
    AND start_at IS NOT NULL AND end_at IS NOT NULL AND time_zone IS NOT NULL
    AND capacity IS NOT NULL AND registration_method IS NOT NULL
    AND cancellation_cutoff_minutes IS NOT NULL)
"""


def _replace_constraint(expression: str) -> None:
    op.execute(sa.text("ALTER TABLE talaqi.events DROP CONSTRAINT ck_events_published_fields"))
    op.execute(
        sa.text(
            "ALTER TABLE talaqi.events ADD CONSTRAINT ck_events_published_fields "
            f"CHECK ({expression})"
        )
    )


def upgrade() -> None:
    _replace_constraint(_PUBLISHED_FIELDS)


def downgrade() -> None:
    validate_test_database_url(os.environ.get("TEST_DATABASE_URL"))
    op.execute(
        sa.text(
            """
            UPDATE talaqi.events
            SET capacity = 2147483647
            WHERE capacity IS NULL
              AND status IN ('published', 'cancelled', 'completed', 'suspended')
            """
        )
    )
    _replace_constraint(_PUBLISHED_FIELDS_WITH_CAPACITY)
