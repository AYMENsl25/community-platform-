from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "apps" / "api" / "src"
sys.path.insert(0, str(SOURCE))

from talaqi.main import create_app  # noqa: E402
from talaqi.platform.openapi import (  # noqa: E402
    OpenApiDriftError,
    build_openapi_document,
    write_openapi,
)

DEFAULT_OUTPUT = ROOT / "openapi" / "talaqi-v1.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Talaqi's deterministic OpenAPI contract")
    parser.add_argument("--check", action="store_true", help="fail if the checked-in file drifts")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    try:
        write_openapi(
            build_openapi_document(create_app()), output=arguments.output, check=arguments.check
        )
    except OpenApiDriftError as error:
        parser.exit(1, f"{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
