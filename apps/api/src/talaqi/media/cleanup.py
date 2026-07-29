from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.media.storage import MediaStorage, StorageError


@dataclass(frozen=True, slots=True)
class AbandonedAsset:
    id: UUID
    storage_key: str


class CleanupRepository(Protocol):
    async def claim(
        self, *, created_before: datetime, limit: int
    ) -> tuple[AbandonedAsset, ...]: ...

    async def mark_deleted(self, asset_id: UUID) -> None: ...


class PostgresCleanupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim(
        self,
        *,
        created_before: datetime,
        limit: int,
    ) -> tuple[AbandonedAsset, ...]:
        rows = (
            (
                await self._session.execute(
                    text(
                        """
                        SELECT id, storage_key
                        FROM talaqi.media_assets
                        WHERE status = 'pending' AND created_at < :created_before
                        ORDER BY created_at, id
                        FOR UPDATE SKIP LOCKED
                        LIMIT :limit
                        """
                    ),
                    {"created_before": created_before, "limit": limit},
                )
            )
            .mappings()
            .all()
        )
        return tuple(AbandonedAsset(id=row["id"], storage_key=row["storage_key"]) for row in rows)

    async def mark_deleted(self, asset_id: UUID) -> None:
        await self._session.execute(
            text(
                """
                UPDATE talaqi.media_assets
                SET status = 'deleted', quarantine_reason = NULL
                WHERE id = :asset_id AND status = 'pending'
                """
            ),
            {"asset_id": asset_id},
        )


class MediaCleanupService:
    def __init__(self, repository: CleanupRepository, storage: MediaStorage) -> None:
        self._repository = repository
        self._storage = storage

    async def expire_abandoned(
        self,
        *,
        now: datetime,
        pending_lifetime: timedelta = timedelta(hours=24),
        limit: int = 100,
    ) -> int:
        if pending_lifetime <= timedelta(0):
            raise ValueError("pending media lifetime must be positive")
        if not 1 <= limit <= 1_000:
            raise ValueError("media cleanup limit must be between 1 and 1000")
        claimed = await self._repository.claim(
            created_before=now - pending_lifetime,
            limit=limit,
        )
        deleted = 0
        for asset in claimed:
            try:
                await self._storage.delete(asset.storage_key)
            except StorageError as error:
                if error.retryable:
                    continue
            await self._repository.mark_deleted(asset.id)
            deleted += 1
        return deleted


__all__ = [
    "AbandonedAsset",
    "MediaCleanupService",
    "PostgresCleanupRepository",
]
