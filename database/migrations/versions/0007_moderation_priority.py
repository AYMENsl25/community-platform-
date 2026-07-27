"""Enforce highest-priority handling for safety moderation cases.

Revision ID: 0007_moderation_priority
Revises: 0006_discovery_indexes
Create Date: 2026-07-27
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from talaqi.db.safety import validate_test_database_url

revision: str = "0007_moderation_priority"
down_revision: str | None = "0006_discovery_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE talaqi.moderation_cases
            SET priority = 'emergency'
            WHERE category = 'safety' AND priority <> 'emergency'
            """
        )
    )
    op.create_check_constraint(
        "ck_moderation_safety_priority",
        "moderation_cases",
        "category <> 'safety' OR priority = 'emergency'",
        schema="talaqi",
    )


def downgrade() -> None:
    validate_test_database_url(os.environ.get("TEST_DATABASE_URL"))
    op.drop_constraint(
        "ck_moderation_safety_priority",
        "moderation_cases",
        schema="talaqi",
        type_="check",
    )
