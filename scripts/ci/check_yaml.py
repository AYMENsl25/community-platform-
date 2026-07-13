from __future__ import annotations

import sys
from pathlib import Path

import yaml


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(
    loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    loader.flatten_mapping(node)
    result: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "duplicate mapping key",
                key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def yaml_is_safe(path: Path) -> bool:
    try:
        # UniqueKeyLoader subclasses SafeLoader; this is safe-load plus duplicate rejection.
        yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=UniqueKeyLoader,  # noqa: S506
        )
    except (OSError, UnicodeError, yaml.YAMLError, TypeError):
        return False
    return True


def main(paths: list[str]) -> int:
    failed = False
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_file() and not yaml_is_safe(path):
            print(f"{path}: invalid, unsafe, or duplicate-key YAML")
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
