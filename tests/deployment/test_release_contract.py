from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.deployment.release_contract import build_release_plan

ROOT = Path(__file__).resolve().parents[2]


def test_release_plan_requires_deployed_environment_sha_and_public_https() -> None:
    sha = "a" * 40
    plan = build_release_plan(
        environment="production",
        release_sha=sha,
        api_url="https://api.talaqi.example/",
        web_url="https://talaqi.example/",
    )
    assert plan.release_sha == sha
    assert plan.api_url == "https://api.talaqi.example"
    assert plan.rollback_strategy == "redeploy_previous_app_sha_without_schema_downgrade"
    for invalid in ("main", "A" * 40, "abc"):
        with pytest.raises(ValueError, match="immutable"):
            build_release_plan(
                environment="production",
                release_sha=invalid,
                api_url="https://api.talaqi.example",
                web_url="https://talaqi.example",
            )
    with pytest.raises(ValueError, match="public HTTPS"):
        build_release_plan(
            environment="staging",
            release_sha=sha,
            api_url="http://localhost:8000",
            web_url="https://staging.talaqi.example",
        )


def test_deployment_workflow_has_one_migration_job_and_manual_production_environment() -> None:
    path = ROOT / ".github" / "workflows" / "deploy.yml"
    text = path.read_text(encoding="utf-8")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]
    migration_steps = [
        step
        for job in jobs.values()
        for step in job.get("steps", [])
        if "alembic upgrade head" in step.get("run", "")
    ]
    assert len(migration_steps) == 1
    assert workflow["on"] == {"workflow_dispatch": workflow["on"]["workflow_dispatch"]}
    assert jobs["release"]["environment"]["name"] == "${{ inputs.environment }}"
    assert "production" in text
    assert "rollback" in text
    assert "alembic downgrade" not in text


def test_preview_workflow_never_receives_deployment_secrets() -> None:
    text = (ROOT / ".github" / "workflows" / "preview.yml").read_text(encoding="utf-8")
    assert "pull_request:" in text
    assert "secrets." not in text
    assert "permissions:\n  contents: read" in text
    assert "alembic upgrade head" in text
