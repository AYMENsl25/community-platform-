"""Add recovery and rotating-session lookup support.

Revision ID: 0004_verification_sessions
Revises: 0003_identity_authentication
Create Date: 2026-07-15
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from talaqi.db.safety import validate_test_database_url

revision: str = "0004_verification_sessions"
down_revision: str | None = "0003_identity_authentication"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_auth_tokens_active_kind",
        "auth_tokens",
        ["user_id", "kind", "expires_at"],
        schema="talaqi",
        postgresql_where=sa.text("used_at IS NULL"),
    )
    op.create_index(
        "ix_sessions_active_family",
        "sessions",
        ["family_id", "expires_at"],
        schema="talaqi",
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO talaqi.schema_revisions (revision, description)
            VALUES ('2026-07-15-verification-rotating-sessions',
                    'Verification, reset, and rotating sessions')
            ON CONFLICT (revision) DO UPDATE SET description=EXCLUDED.description
            """
        )
    )


def downgrade() -> None:
    validate_test_database_url(os.environ.get("TEST_DATABASE_URL"))
    op.execute(
        sa.text(
            """DELETE FROM talaqi.schema_revisions
            WHERE revision='2026-07-15-verification-rotating-sessions'"""
        )
    )
    op.drop_index("ix_sessions_active_family", table_name="sessions", schema="talaqi")
    op.drop_index("ix_auth_tokens_active_kind", table_name="auth_tokens", schema="talaqi")
