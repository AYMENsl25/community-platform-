from __future__ import annotations

import argparse
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

CLASS_NAMES = ("web", "api", "contract", "migration", "security")
ALL_CLASSES = dict.fromkeys(CLASS_NAMES, True)


def normalize_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized.removeprefix("./").strip("/")


def classify_paths(paths: Iterable[str]) -> dict[str, bool]:
    result = dict.fromkeys(CLASS_NAMES, False)
    for raw_path in sorted({normalize_path(path) for path in paths}):
        path = PurePosixPath(raw_path)
        suffix = path.suffix.lower()
        executable = suffix in {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".sql", ".sh", ".ps1"}

        if raw_path == "docs/engineering/ci-security.md":
            result["security"] = True
        if raw_path in {"README.md", "CONTRIBUTING.md"}:
            result["security"] = True
        if raw_path.startswith((".github/", "tests/security/")):
            result["security"] = True
        if raw_path.startswith("scripts/ci/") or raw_path in {
            ".pre-commit-config.yaml",
            ".secrets.baseline",
        }:
            result["security"] = True
        if executable:
            result["security"] = True
        if path.name in {"package.json", "pyproject.toml"} or path.suffix == ".lock":
            result["security"] = True

        if raw_path in {
            "package.json",
            "pnpm-lock.yaml",
            "pnpm-workspace.yaml",
            "turbo.json",
            "tsconfig.base.json",
        }:
            result.update(web=True, contract=True, security=True)
        if raw_path in {"pyproject.toml", "uv.lock"}:
            result.update(api=True, contract=True, migration=True, security=True)
        if raw_path in {".env.example", "compose.yaml"}:
            result.update(api=True, migration=True, security=True)

        if raw_path.startswith(
            (
                "apps/web/",
                "packages/ui/",
                "packages/translations/",
                "packages/config/",
                "scripts/brand/",
            )
        ):
            result["web"] = True
        if raw_path.startswith(("packages/api-client/", "openapi/")):
            result.update(web=True, contract=True)
        if raw_path.startswith("apps/api/"):
            result.update(api=True, contract=True)
        if raw_path.startswith("apps/worker/"):
            result["api"] = True
        if raw_path.startswith("database/") or raw_path == "alembic.ini":
            result.update(api=True, migration=True)
        if raw_path.startswith(("apps/api/src/talaqi/db/", "apps/api/tests/db/")):
            result["migration"] = True
    return result


def _changed_paths(base: str, head: str) -> list[str]:
    if not base or not head or base == "0" * 40 or head == "0" * 40:
        raise ValueError("invalid comparison revisions")
    git = shutil.which("git")
    if git is None:
        raise OSError("git executable is unavailable")
    # Revisions are separate arguments to a fixed executable; no shell is involved.
    merge_base = subprocess.run(  # noqa: S603 -- fixed executable, argv only
        [git, "merge-base", base, head],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not merge_base:
        raise ValueError("merge base is unavailable")
    output = subprocess.run(  # noqa: S603 -- fixed executable, argv only
        [git, "diff", "--name-only", "--diff-filter=ACDMRTUXB", merge_base, head, "--"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return output.splitlines()


def _write_output(result: dict[str, bool], output: Path | None) -> None:
    rendered = "".join(f"{name}={'true' if result[name] else 'false'}\n" for name in CLASS_NAMES)
    if output is None:
        print(rendered, end="")
    else:
        output.write_text(rendered, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    parser.add_argument("head")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    try:
        result = classify_paths(_changed_paths(arguments.base, arguments.head))
    except Exception:
        result = dict(ALL_CLASSES)
    _write_output(result, arguments.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
