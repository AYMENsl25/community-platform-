"""Add profile eligibility count indexes.

Revision ID: 0005_profiles_eligibility
Revises: 0004_verification_sessions
Create Date: 2026-07-16
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from talaqi.db.safety import validate_test_database_url

revision: str = "0005_profiles_eligibility"
down_revision: str | None = "0004_verification_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_clubs_active_owner_eligibility",
        "clubs",
        ["owner_user_id"],
        schema="talaqi",
        postgresql_where=sa.text("status <> 'closed'"),
    )
    op.create_index(
        "ix_events_active_independent_owner_eligibility",
        "events",
        ["owner_user_id"],
        schema="talaqi",
        postgresql_where=sa.text(
            "ownership_type = 'independent' AND status NOT IN ('cancelled', 'completed')"
        ),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO talaqi.schema_revisions (revision, description)
            VALUES (
                '2026-07-16-profiles-eligibility',
                'Profiles and creation eligibility support'
            )
            ON CONFLICT (revision) DO UPDATE SET description = EXCLUDED.description
            """
        )
    )


def downgrade() -> None:
    validate_test_database_url(os.environ.get("TEST_DATABASE_URL"))
    op.execute(
        sa.text(
            """
            DELETE FROM talaqi.schema_revisions
            WHERE revision = '2026-07-16-profiles-eligibility'
            """
        )
    )
    op.drop_index(
        "ix_events_active_independent_owner_eligibility",
        table_name="events",
        schema="talaqi",
    )
    op.drop_index(
        "ix_clubs_active_owner_eligibility",
        table_name="clubs",
        schema="talaqi",
    )
