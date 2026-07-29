from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from talaqi.media.cleanup import AbandonedAsset, MediaCleanupService
from talaqi.media.storage import StorageError

NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)
FIRST = AbandonedAsset(
    UUID("018f0000-0000-7000-8000-000000000101"),
    ("media/018f0000-0000-7000-8000-000000000201/018f0000-0000-7000-8000-000000000101/source"),
)
SECOND = AbandonedAsset(
    UUID("018f0000-0000-7000-8000-000000000102"),
    ("media/018f0000-0000-7000-8000-000000000202/018f0000-0000-7000-8000-000000000102/source"),
)


class Repository:
    def __init__(self) -> None:
        self.deleted: list[UUID] = []
        self.before: datetime | None = None

    async def claim(self, *, created_before: datetime, limit: int) -> tuple[AbandonedAsset, ...]:
        assert limit == 2
        self.before = created_before
        return FIRST, SECOND

    async def mark_deleted(self, asset_id: UUID) -> None:
        self.deleted.append(asset_id)


class Storage:
    def create_upload_grant(self, **kwargs: object):
        del kwargs
        raise AssertionError

    async def read(self, storage_key: str, *, max_bytes: int) -> bytes:
        del storage_key, max_bytes
        raise AssertionError

    async def replace(self, storage_key: str, content: bytes, content_type: str) -> None:
        del storage_key, content, content_type
        raise AssertionError

    async def delete(self, storage_key: str) -> None:
        if storage_key == SECOND.storage_key:
            raise StorageError("storage_unavailable", retryable=True)

    async def ready(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_cleanup_deletes_only_objects_successfully_removed() -> None:
    repository = Repository()
    service = MediaCleanupService(repository, Storage())

    count = await service.expire_abandoned(
        now=NOW,
        pending_lifetime=timedelta(hours=24),
        limit=2,
    )

    assert count == 1
    assert repository.before == NOW - timedelta(hours=24)
    assert repository.deleted == [FIRST.id]
