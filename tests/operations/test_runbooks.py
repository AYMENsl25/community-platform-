from __future__ import annotations

from pathlib import Path


def test_required_operator_runbooks_have_stop_conditions_and_safe_boundaries() -> None:
    root = Path(__file__).resolve().parents[2]
    required = {
        "restore.md": ("manifest", "isolated", "Stop"),
        "stuck-jobs.md": ("lease token", "MFA", "Never bulk"),
        "failed-migration.md": ("do not downgrade", "restore", "application SHA"),
        "account-recovery.md": ("30-day", "unrecoverable", "cannot edit database"),
        "data-rights.md": ("Encrypt", "single-use", "immutable audit"),
        "compromised-admin.md": ("revoke", "MFA", "never mutate audit"),
    }
    for name, phrases in required.items():
        text = (root / "docs" / "runbooks" / name).read_text(encoding="utf-8")
        assert all(phrase.casefold() in text.casefold() for phrase in phrases)
