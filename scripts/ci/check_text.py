from __future__ import annotations

import sys
from pathlib import Path


def text_issues(content: bytes) -> list[str]:
    if b"\x00" in content:
        return []
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return []
    issues = [
        f"line {number} has trailing whitespace"
        for number, line in enumerate(text.splitlines(), start=1)
        if line.rstrip(" \t") != line
    ]
    if content and (not text.endswith("\n") or text.endswith("\n\n")):
        issues.append("file must end with one newline")
    return issues


def main(paths: list[str]) -> int:
    failed = False
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file():
            continue
        for issue in text_issues(path.read_bytes()):
            print(f"{path}: {issue}")
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
