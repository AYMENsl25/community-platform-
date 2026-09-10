from __future__ import annotations

import argparse
import json
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


def probe(base_url: str, path: str) -> dict[str, object]:
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or parsed.hostname is None:
        raise ValueError("smoke target must be public HTTPS")
    request = Request(urljoin(base_url.rstrip("/") + "/", path.lstrip("/")))
    try:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - HTTPS validated above
            payload = json.loads(response.read(4096))
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"smoke probe failed for {path}") from error
    if response.status != 200 or not isinstance(payload, dict):
        raise RuntimeError(f"smoke probe was unhealthy for {path}")
    return cast(dict[str, object], payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", required=True)
    arguments = parser.parse_args()
    live = probe(arguments.api_url, "/health/live")
    ready = probe(arguments.api_url, "/health/ready")
    if live.get("status") != "ok" or ready.get("status") != "ready":
        raise RuntimeError("deployed application did not satisfy liveness and readiness")
    print("deployment smoke passed")


if __name__ == "__main__":
    main()
