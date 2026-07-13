"""Create the immutable Talaqi closed-beta baseline.

Revision ID: 0001_closed_beta_baseline
Revises:
Create Date: 2026-07-13
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.util.concurrency import await_only
from talaqi.db.safety import validate_test_database_url

revision: str = "0001_closed_beta_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ASSET_SHA256 = "b8a2eb2072302abd7ea4bb5a375474be854d8322cec202b2aec422f5c5c7e86e"
_TRANSACTION_START = "\nBEGIN;\n"
_TRANSACTION_END = "\nCOMMIT;\n"


def _canonical_payload(payload: bytes) -> bytes:
    return payload.replace(b"\r\n", b"\n")


def _baseline_sql() -> str:
    asset = Path(__file__).parents[1] / "assets" / "0001_closed_beta_baseline.sql"
    payload = _canonical_payload(asset.read_bytes())
    if hashlib.sha256(payload).hexdigest() != _ASSET_SHA256:
        raise RuntimeError("immutable baseline migration asset checksum mismatch")

    script = payload.decode("utf-8")
    if script.count(_TRANSACTION_START) != 1 or not script.endswith(_TRANSACTION_END):
        raise RuntimeError("immutable baseline migration asset transaction wrapper is invalid")
    return script.replace(_TRANSACTION_START, "\n", 1)[: -len(_TRANSACTION_END)] + "\n"


def upgrade() -> None:
    if context.is_offline_mode():
        op.execute(sa.text(_baseline_sql()))
        return
    driver_connection = op.get_bind().connection.driver_connection
    await_only(driver_connection.execute(_baseline_sql()))


def downgrade() -> None:
    validate_test_database_url(os.environ.get("TEST_DATABASE_URL"))
    op.execute(sa.text("DROP SCHEMA IF EXISTS talaqi CASCADE"))
