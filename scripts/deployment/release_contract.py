from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from urllib.parse import urlsplit

_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class ReleasePlan:
    environment: str
    release_sha: str
    api_url: str
    web_url: str
    migration_command: str = "python -m uv run alembic upgrade head"
    rollback_strategy: str = "redeploy_previous_app_sha_without_schema_downgrade"


def _https_url(value: str, *, name: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"{name} must be a public HTTPS URL without credentials or query data")
    return value.rstrip("/")


def build_release_plan(
    *, environment: str, release_sha: str, api_url: str, web_url: str
) -> ReleasePlan:
    if environment not in {"staging", "production"}:
        raise ValueError("environment must be staging or production")
    if _SHA.fullmatch(release_sha) is None:
        raise ValueError("release SHA must be an immutable 40-character lowercase commit SHA")
    return ReleasePlan(
        environment=environment,
        release_sha=release_sha,
        api_url=_https_url(api_url, name="API URL"),
        web_url=_https_url(web_url, name="web URL"),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", required=True)
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--web-url", required=True)
    arguments = parser.parse_args()
    plan = build_release_plan(
        environment=arguments.environment,
        release_sha=arguments.release_sha,
        api_url=arguments.api_url,
        web_url=arguments.web_url,
    )
    print(json.dumps(asdict(plan), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
