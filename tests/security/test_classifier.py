from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.ci.classify_changes import ALL_CLASSES, _changed_paths, classify_paths, normalize_path


def test_classifier_is_pure_deterministic_and_normalizes_separators() -> None:
    paths = ["apps\\web\\src\\app\\page.tsx", "openapi/talaqi-v1.json"]
    first = classify_paths(paths)
    second = classify_paths(reversed(paths))
    assert first == second
    assert normalize_path("./apps\\web//src/app/page.tsx") == "apps/web/src/app/page.tsx"
    assert first == {
        "web": True,
        "api": False,
        "contract": True,
        "migration": False,
        "security": True,
    }


@pytest.mark.parametrize(
    ("path", "enabled"),
    [
        ("docs/product/mvp-acceptance.md", set()),
        ("docs/engineering/ci-security.md", {"security"}),
        ("apps/web/src/app/page.tsx", {"web", "security"}),
        ("apps/web/package.json", {"web", "security"}),
        ("packages/api-client/src/index.ts", {"web", "contract", "security"}),
        ("apps/api/src/talaqi/main.py", {"api", "contract", "security"}),
        ("apps/worker/pyproject.toml", {"api", "security"}),
        ("apps/api/src/talaqi/db/session.py", {"api", "contract", "migration", "security"}),
        ("database/migrations/versions/0002.py", {"api", "migration", "security"}),
        (".github/workflows/ci.yml", {"security"}),
        ("package.json", {"web", "contract", "security"}),
        ("uv.lock", {"api", "contract", "migration", "security"}),
        ("README.md", {"security"}),
        ("compose.yaml", {"api", "migration", "security"}),
        ("playwright.config.ts", {"security"}),
        ("tests/e2e/foundation.spec.ts", {"security"}),
    ],
)
def test_classifier_conservative_mapping(path: str, enabled: set[str]) -> None:
    result = classify_paths([path])
    assert {name for name, value in result.items() if value} == enabled


def test_fail_safe_result_enables_every_class() -> None:
    assert set(ALL_CLASSES) == {"web", "api", "contract", "migration", "security"}
    assert all(ALL_CLASSES.values())


def test_real_git_diff_reports_deleted_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "ci-classifier@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "CI Classifier"], cwd=tmp_path, check=True)
    deleted = tmp_path / "apps" / "web" / "src" / "deleted.ts"
    deleted.parent.mkdir(parents=True)
    deleted.write_text("export const deleted = true;\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "base"], cwd=tmp_path, check=True)
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout.strip()
    deleted.unlink()
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "delete"], cwd=tmp_path, check=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout.strip()

    monkeypatch.chdir(tmp_path)
    paths = _changed_paths(base, head)
    assert paths == ["apps/web/src/deleted.ts"]
    assert classify_paths(paths)["security"] is True


def test_cli_invalid_base_fails_safe(tmp_path) -> None:  # type: ignore[no-untyped-def]
    output = tmp_path / "output"
    result = subprocess.run(
        [
            ".venv/Scripts/python.exe",
            "scripts/ci/classify_changes.py",
            "0" * 40,
            "also-invalid",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert output.read_text(encoding="utf-8").splitlines() == [
        "web=true",
        "api=true",
        "contract=true",
        "migration=true",
        "security=true",
    ]
