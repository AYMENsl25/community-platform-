"""Seed approved closed-beta operational feature flags.

Revision ID: 0013_feature_flags
Revises: 0012_communications
Create Date: 2026-08-14
"""

from __future__ import annotations

import os
from collections.abc import Sequence

from alembic import op
from talaqi.db.safety import validate_test_database_url

revision: str = "0013_feature_flags"
down_revision: str | None = "0012_communications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FLAGS = (
    "features.member_reports_enabled",
    "features.organizer_announcements_enabled",
    "features.independent_event_creation_enabled",
)


def upgrade() -> None:
    for key in _FLAGS:
        op.execute(
            "INSERT INTO talaqi.platform_settings (key, value) "
            f"VALUES ('{key}', 'true'::jsonb) ON CONFLICT (key) DO NOTHING"
        )


def downgrade() -> None:
    validate_test_database_url(os.environ.get("TEST_DATABASE_URL"))
    quoted = ", ".join(f"'{key}'" for key in _FLAGS)
    op.execute(f"DELETE FROM talaqi.platform_settings WHERE key IN ({quoted})")
