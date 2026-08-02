from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[4]


def test_discovery_migration_remains_single_index_only_revision() -> None:
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))

    assert scripts.get_heads() == ["0009_registration_state_machine"]
    assert scripts.get_revision("0008_event_publishing").down_revision == (
        "0007_moderation_priority"
    )
    assert scripts.get_revision("0007_moderation_priority").down_revision == (
        "0006_discovery_indexes"
    )
    assert scripts.get_revision("0006_discovery_indexes").down_revision == (
        "0005_profiles_eligibility"
    )

    migration = (ROOT / "database/migrations/versions/0006_discovery_indexes.py").read_text(
        encoding="utf-8"
    )
    lowered = migration.casefold()
    assert "insert into" not in lowered
    assert "update talaqi" not in lowered
    assert "delete from" not in lowered
    assert "status = 'published'" in migration
    assert "visibility = 'public'" in migration
    assert "suspended_at IS NULL" in migration
    assert migration.count("op.create_index(") == 2
    assert "ix_events_public_price_featured" not in migration
