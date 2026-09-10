from __future__ import annotations

import re
from pathlib import Path

import yaml
from talaqi.db.safety import validate_test_database_url

ROOT = Path(__file__).resolve().parents[2]
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_JOBS = {"changes", "web", "api", "contract", "migration", "security", "playwright"}
CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"  # pragma: allowlist secret
SETUP_NODE_SHA = "820762786026740c76f36085b0efc47a31fe5020"  # pragma: allowlist secret
SETUP_PYTHON_SHA = "5fda3b95a4ea91299a34e894583c3862153e4b97"  # pragma: allowlist secret
CACHE_SHA = "55cc8345863c7cc4c66a329aec7e433d2d1c52a9"  # pragma: allowlist secret
DEPENDENCY_REVIEW_SHA = "a1d282b36b6f3519aa1f3fc636f609c47dddb294"  # pragma: allowlist secret
CODEQL_SHA = "99df26d4f13ea111d4ec1a7dddef6063f76b97e9"  # pragma: allowlist secret
EXPECTED_ACTIONS = {
    "actions/checkout": CHECKOUT_SHA,
    "actions/setup-node": SETUP_NODE_SHA,
    "actions/setup-python": SETUP_PYTHON_SHA,
    "actions/cache": CACHE_SHA,
    "actions/dependency-review-action": DEPENDENCY_REVIEW_SHA,
    "github/codeql-action/init": CODEQL_SHA,
    "github/codeql-action/analyze": CODEQL_SHA,
}


def load_workflow(name: str) -> tuple[dict[str, object], str]:
    path = ROOT / ".github" / "workflows" / name
    text = path.read_text(encoding="utf-8")
    parsed = yaml.load(text, Loader=yaml.BaseLoader)
    assert isinstance(parsed, dict)
    return parsed, text


def action_references(value: object) -> list[str]:
    if isinstance(value, dict):
        result: list[str] = []
        for key, item in value.items():
            if key == "uses" and isinstance(item, str):
                result.append(item)
            result.extend(action_references(item))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(action_references(item))
        return result
    return []


def test_ci_contract_permissions_triggers_jobs_and_protected_playwright() -> None:
    workflow, text = load_workflow("ci.yml")
    assert set(workflow["jobs"]) == EXPECTED_JOBS  # type: ignore[arg-type]
    assert workflow["permissions"] == {"contents": "read"}
    assert "pull_request_target" not in text
    assert "pull_request:" in text
    assert "push:" in text
    assert "branches: [main]" in text
    assert "cancel-in-progress: true" in text
    jobs = workflow["jobs"]  # type: ignore[assignment]
    assert "if" not in jobs["playwright"]  # type: ignore[index]
    assert "persist-credentials: false" in text
    assert "fetch-depth: 0" in text


def test_ci_actions_are_exact_immutable_reviewed_pins() -> None:
    for workflow_name in ("ci.yml", "codeql.yml"):
        workflow, _ = load_workflow(workflow_name)
        for reference in action_references(workflow):
            owner_action, sha = reference.rsplit("@", maxsplit=1)
            assert FULL_SHA.fullmatch(sha)
            assert EXPECTED_ACTIONS[owner_action] == sha


def test_ci_security_migration_cache_and_scan_contracts() -> None:
    _, text = load_workflow("ci.yml")
    assert "postgres:18" in text
    assert "127.0.0.1:55432" in text
    assert "talaqi_ci_test" in text
    assert "--audit-level high" in text
    assert "pip-audit" in text
    assert "detect-secrets" in text
    assert "ruff check --select S" in text
    assert "upload-artifact" not in text
    assert ".next" not in text.split("actions/cache", maxsplit=1)[-1]
    assert "playwright-report" not in text
    assert "payment" not in text.lower()
    assert "terms" not in text.lower()
    assert "${{ secrets." not in text


def test_ci_migration_database_url_uses_the_runtime_driver_and_safety_contract() -> None:
    workflow, _ = load_workflow("ci.yml")
    jobs = workflow["jobs"]  # type: ignore[assignment]
    migration = jobs["migration"]  # type: ignore[index]
    url = migration["env"]["TEST_DATABASE_URL"]  # type: ignore[index]
    target = validate_test_database_url(url)
    assert target.host == "127.0.0.1"
    assert target.port == 55432
    assert target.database == "talaqi_ci_test"


def test_codeql_has_minimal_permissions_languages_and_bounded_schedule() -> None:
    workflow, text = load_workflow("codeql.yml")
    assert workflow["permissions"] == {
        "actions": "read",
        "contents": "read",
        "packages": "read",
        "security-events": "write",
    }
    assert "javascript-typescript" in text
    assert "python" in text
    assert "schedule:" in text
    assert "cron:" in text
    assert "branches: [main]" in text
    assert "contents: write" not in text


def test_dependabot_covers_all_ecosystems_weekly_with_low_limits() -> None:
    path = ROOT / ".github" / "dependabot.yml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    updates = config["updates"]
    assert {item["package-ecosystem"] for item in updates} == {"npm", "pip", "github-actions"}
    assert all(item["schedule"]["interval"] == "weekly" for item in updates)
    assert all(item["open-pull-requests-limit"] <= 5 for item in updates)
