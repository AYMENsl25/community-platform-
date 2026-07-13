from __future__ import annotations

import re
from pathlib import Path

import yaml

from scripts.ci.check_text import text_issues
from scripts.ci.check_yaml import yaml_is_safe

ROOT = Path(__file__).resolve().parents[2]


def test_text_gate_rejects_trailing_whitespace_and_missing_or_extra_eof_newlines() -> None:
    assert text_issues(b"clean\n") == []
    assert text_issues(b"trailing \n") == ["line 1 has trailing whitespace"]
    assert text_issues(b"missing") == ["file must end with one newline"]
    assert text_issues(b"extra\n\n") == ["file must end with one newline"]
    assert text_issues(b"\x00binary") == []


def test_yaml_gate_uses_safe_parser_and_rejects_duplicate_keys(tmp_path: Path) -> None:
    valid = tmp_path / "valid.yml"
    valid.write_text("name: value\nitems:\n  - one\n", encoding="utf-8")
    duplicate = tmp_path / "duplicate.yml"
    duplicate.write_text("name: one\nname: two\n", encoding="utf-8")
    unsafe = tmp_path / "unsafe.yml"
    unsafe.write_text("value: !!python/object/apply:os.system ['unsafe']\n", encoding="utf-8")
    assert yaml_is_safe(valid)
    assert not yaml_is_safe(duplicate)
    assert not yaml_is_safe(unsafe)


def test_precommit_uses_only_local_system_workspace_tools() -> None:
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    assert config["repos"][0]["repo"] == "local"
    hooks = config["repos"][0]["hooks"]
    assert {hook["id"] for hook in hooks} == {
        "text-safety",
        "yaml-safety",
        "ruff-format",
        "ruff-check",
        "prettier",
        "detect-secrets",
    }
    assert all(hook["language"] == "system" for hook in hooks)
    assert all("http" not in hook["entry"] for hook in hooks)


def test_detect_secrets_scans_tracked_environment_templates() -> None:
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    detect_secrets = next(
        hook for hook in config["repos"][0]["hooks"] if hook["id"] == "detect-secrets"
    )
    excluded = re.compile(detect_secrets["exclude"])
    assert excluded.fullmatch(".env.example") is None
    assert excluded.fullmatch(".env.test.local") is not None


def test_secret_baseline_contains_only_reviewed_preexisting_test_and_checksum_fixtures() -> None:
    baseline = yaml.safe_load((ROOT / ".secrets.baseline").read_text(encoding="utf-8"))
    paths = {path.replace("\\", "/") for path in baseline["results"]}
    assert paths
    assert all(
        "/tests/" in path
        or path
        in {
            "database/migrations/versions/0001_closed_beta_baseline.py",
            "packages/ui/src/brand-assets.test.ts",
            "scripts/brand/generate-assets.mjs",
        }
        for path in paths
    )
    assert not any(
        "/src/" in path and "/tests/" not in path and path != "packages/ui/src/brand-assets.test.ts"
        for path in paths
    )


def test_current_moderate_dependency_finding_has_a_concrete_tracking_record() -> None:
    policy = (ROOT / "docs" / "engineering" / "ci-security.md").read_text(encoding="utf-8")
    assert "GHSA-qx2v-qp2m-jg93" in policy
    assert "CVE-2026-41305" in policy
    assert "Owner: Web Platform" in policy
    assert "Affected component: `next@16.2.10` bundles `postcss@8.4.31`" in policy
    assert "Compensating control:" in policy
    assert "Due date: 2026-08-14" in policy
    assert "suppression" not in policy.split("GHSA-qx2v-qp2m-jg93", maxsplit=1)[1].lower()
