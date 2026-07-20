"""Add measured partial indexes for public discovery queries.

Revision ID: 0006_discovery_indexes
Revises: 0005_profiles_eligibility
Create Date: 2026-07-18
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from talaqi.db.safety import validate_test_database_url

revision: str = "0006_discovery_indexes"
down_revision: str | None = "0005_profiles_eligibility"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PUBLIC_EVENT_PREDICATE = sa.text(
    "status = 'published' AND visibility = 'public' AND suspended_at IS NULL"
)
_PUBLIC_CLUB_PREDICATE = sa.text("status = 'published' AND suspended_at IS NULL")


def upgrade() -> None:
    op.create_index(
        "ix_events_public_featured",
        "events",
        [
            sa.text("(CASE WHEN ownership_type = 'club' THEN 10 ELSE 0 END) DESC"),
            "start_at",
            "id",
        ],
        schema="talaqi",
        postgresql_where=_PUBLIC_EVENT_PREDICATE,
    )
    op.create_index(
        "ix_clubs_public_name",
        "clubs",
        [sa.text("lower(name)"), "id"],
        schema="talaqi",
        postgresql_where=_PUBLIC_CLUB_PREDICATE,
    )


def downgrade() -> None:
    validate_test_database_url(os.environ.get("TEST_DATABASE_URL"))
    op.drop_index("ix_clubs_public_name", table_name="clubs", schema="talaqi")
    op.drop_index("ix_events_public_featured", table_name="events", schema="talaqi")
