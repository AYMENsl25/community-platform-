from __future__ import annotations

from pathlib import Path

import pytest

from scripts.operations.backup_manifest import describe, verify


def test_backup_manifest_detects_size_and_content_tampering(tmp_path: Path) -> None:
    backup = tmp_path / "database.dump.gpg"
    backup.write_bytes(b"encrypted-backup")
    entry = describe(backup)
    assert entry["path"] == backup.name
    assert entry["size"] == len(b"encrypted-backup")
    assert len(entry["sha256"]) == 64
    verify(backup, entry)
    backup.write_bytes(b"tampered-backup")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify(backup, entry)


def test_backup_workflow_encrypts_before_upload_and_restore_is_manual() -> None:
    root = Path(__file__).resolve().parents[2]
    backup = (root / ".github/workflows/backup.yml").read_text(encoding="utf-8")
    restore = (root / ".github/workflows/restore-rehearsal.yml").read_text(encoding="utf-8")
    assert backup.index("pg_dump") < backup.index("gpg --batch") < backup.index("aws s3 cp")
    assert "schedule:" in backup
    assert "workflow_dispatch:" in restore
    assert "schedule:" not in restore
    assert "_restore_test" in restore
    assert "pg_restore --exit-on-error" in restore
    assert "backup_manifest.py verify" in restore
