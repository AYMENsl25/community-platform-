from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from talaqi.media.local_storage import LocalMediaStorage
from talaqi.media.storage import StorageError

ASSET_ID = UUID("018f0000-0000-7000-8000-000000000102")
KEY = "media/018f0000-0000-7000-8000-000000000101/018f0000-0000-7000-8000-000000000102/source"
NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)


def storage(root: Path) -> LocalMediaStorage:
    return LocalMediaStorage(
        root,
        api_public_url="http://localhost:8000",
        signing_secret=b"local-test-secret",
    )


def test_local_grant_is_method_key_size_type_and_expiry_bound(tmp_path: Path) -> None:
    adapter = storage(tmp_path)
    grant = adapter.create_upload_grant(
        asset_id=ASSET_ID,
        storage_key=KEY,
        content_type="image/png",
        byte_size=128,
        expires_at=NOW + timedelta(minutes=10),
    )

    assert grant.method == "PUT"
    assert grant.url == (
        "http://localhost:8000/api/v1/media/uploads/018f0000-0000-7000-8000-000000000102/content"
    )
    assert set(grant.headers) == {"Content-Type", "X-Talaqi-Upload-Token"}
    adapter.accept_upload(
        asset_id=ASSET_ID,
        storage_key=KEY,
        content_type="image/png",
        expected_size=128,
        content=b"x" * 128,
        token=grant.headers["X-Talaqi-Upload-Token"],
        now=NOW,
    )


@pytest.mark.parametrize(
    ("key", "content_type", "size", "asset_id"),
    [
        (KEY.replace("/source", "/other"), "image/png", 128, ASSET_ID),
        (KEY, "image/jpeg", 128, ASSET_ID),
        (KEY, "image/png", 127, ASSET_ID),
        (KEY, "image/png", 128, UUID("018f0000-0000-7000-8000-000000000103")),
    ],
)
def test_local_grant_rejects_tampering(
    tmp_path: Path, key: str, content_type: str, size: int, asset_id: UUID
) -> None:
    adapter = storage(tmp_path)
    grant = adapter.create_upload_grant(
        asset_id=ASSET_ID,
        storage_key=KEY,
        content_type="image/png",
        byte_size=128,
        expires_at=NOW + timedelta(minutes=10),
    )

    with pytest.raises(StorageError, match="invalid_upload_grant"):
        adapter.accept_upload(
            asset_id=asset_id,
            storage_key=key,
            content_type=content_type,
            expected_size=size,
            content=b"x" * size,
            token=grant.headers["X-Talaqi-Upload-Token"],
            now=NOW,
        )


def test_local_storage_rejects_expired_grant_and_path_traversal(tmp_path: Path) -> None:
    adapter = storage(tmp_path)
    grant = adapter.create_upload_grant(
        asset_id=ASSET_ID,
        storage_key=KEY,
        content_type="image/png",
        byte_size=4,
        expires_at=NOW,
    )

    with pytest.raises(StorageError, match="invalid_upload_grant"):
        adapter.accept_upload(
            asset_id=ASSET_ID,
            storage_key=KEY,
            content_type="image/png",
            expected_size=4,
            content=b"data",
            token=grant.headers["X-Talaqi-Upload-Token"],
            now=NOW + timedelta(seconds=1),
        )
    with pytest.raises(StorageError, match="invalid_storage_key"):
        adapter.create_upload_grant(
            asset_id=ASSET_ID,
            storage_key="../outside",
            content_type="image/png",
            byte_size=4,
            expires_at=NOW + timedelta(minutes=1),
        )


@pytest.mark.asyncio
async def test_local_storage_bounds_reads_replaces_and_deletes(tmp_path: Path) -> None:
    adapter = storage(tmp_path)
    await adapter.replace(KEY, b"original", "image/png")

    assert await adapter.read(KEY, max_bytes=8) == b"original"
    with pytest.raises(StorageError, match="object_too_large"):
        await adapter.read(KEY, max_bytes=7)

    await adapter.replace(KEY, b"canonical", "image/webp")
    assert await adapter.read(KEY, max_bytes=20) == b"canonical"
    await adapter.delete(KEY)
    with pytest.raises(StorageError, match="object_missing"):
        await adapter.read(KEY, max_bytes=20)
