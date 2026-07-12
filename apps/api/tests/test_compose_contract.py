from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[3]


def test_compose_defines_exact_local_service_contract() -> None:
    document = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    services = document["services"]

    assert set(services) == {"postgres", "minio", "mailpit"}
    assert set(document["volumes"]) == {"postgres_data", "minio_data"}
    for service in services.values():
        image = service["image"]
        assert ":" in image or "@sha256:" in image
        assert not image.endswith(":latest")
        assert service["restart"] == "unless-stopped"
        assert "healthcheck" in service
        assert all(port.startswith("127.0.0.1:") for port in service["ports"])

    rendered = (ROOT / "compose.yaml").read_text(encoding="utf-8").lower()
    assert "redis" not in rendered
    assert "changeme" not in rendered
    assert "postgres_password" in rendered
    assert "minio_root_user" in rendered
    assert "minio_root_password" in rendered
