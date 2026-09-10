from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import TypedDict, cast


class ManifestEntry(TypedDict):
    path: str
    size: int
    sha256: str


def describe(path: Path) -> ManifestEntry:
    resolved = path.resolve(strict=True)
    digest = hashlib.sha256()
    size = 0
    with resolved.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return {"path": path.name, "size": size, "sha256": digest.hexdigest()}


def verify(path: Path, entry: ManifestEntry) -> None:
    observed = describe(path)
    if observed != entry:
        raise ValueError(f"backup checksum mismatch for {path.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("create", "verify"))
    parser.add_argument("manifest", type=Path)
    parser.add_argument("files", nargs="+", type=Path)
    arguments = parser.parse_args()
    if arguments.mode == "create":
        manifest = {"version": 1, "files": [describe(path) for path in arguments.files]}
        arguments.manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return
    parsed = cast(object, json.loads(arguments.manifest.read_text(encoding="utf-8")))
    raw_entries = cast(dict[str, object], parsed).get("files") if isinstance(parsed, dict) else None
    if not isinstance(raw_entries, list):
        raise ValueError("backup manifest shape does not match supplied files")
    entries = cast(list[object], raw_entries)
    if len(entries) != len(arguments.files):
        raise ValueError("backup manifest shape does not match supplied files")
    for path, entry in zip(arguments.files, entries, strict=True):
        if not isinstance(entry, dict):
            raise ValueError("backup manifest entry is invalid")
        verify(path, cast(ManifestEntry, entry))


if __name__ == "__main__":
    main()
