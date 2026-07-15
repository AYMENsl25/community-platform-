"""Add authentication lookup support without rewriting identity data.

Revision ID: 0003_identity_authentication
Revises: 0002_regional_catalog
Create Date: 2026-07-15
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from talaqi.db.safety import validate_test_database_url

revision: str = "0003_identity_authentication"
down_revision: str | None = "0002_regional_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_users_auth_lockout",
        "users",
        ["locked_until"],
        schema="talaqi",
        postgresql_where=sa.text("locked_until IS NOT NULL"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO talaqi.schema_revisions (revision, description)
            VALUES ('2026-07-15-identity-authentication', 'Identity authentication support')
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
            WHERE revision = '2026-07-15-identity-authentication'
            """
        )
    )
    op.drop_index("ix_users_auth_lockout", table_name="users", schema="talaqi")
