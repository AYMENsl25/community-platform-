from __future__ import annotations

from datetime import datetime
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.media.models import MediaAsset, MediaStatus


class MediaRepositoryProtocol(Protocol):
    async def create_pending(
        self,
        *,
        asset_id: UUID,
        owner_user_id: UUID,
        storage_key: str,
        original_filename: str,
        content_type: str,
        byte_size: int,
    ) -> MediaAsset: ...

    async def get_owned(
        self,
        asset_id: UUID,
        owner_user_id: UUID,
        *,
        for_update: bool = False,
    ) -> MediaAsset | None: ...

    async def mark_verified(
        self,
        asset: MediaAsset,
        *,
        storage_key: str,
        content_type: str,
        byte_size: int,
        width: int,
        height: int,
        sha256: bytes,
        verified_at: datetime,
    ) -> MediaAsset: ...

    async def mark_quarantined(
        self,
        asset: MediaAsset,
        *,
        reason: str,
        now: datetime,
    ) -> MediaAsset: ...


def _asset(row: object) -> MediaAsset:
    values = cast(dict[str, object], row)
    return MediaAsset(
        id=cast(UUID, values["id"]),
        owner_user_id=cast(UUID, values["owner_user_id"]),
        status=cast(MediaStatus, values["status"]),
        storage_key=cast(str, values["storage_key"]),
        original_filename=cast(str, values["original_filename"]),
        content_type=cast(str, values["content_type"]),
        byte_size=cast(int, values["byte_size"]),
        width=cast(int | None, values["width"]),
        height=cast(int | None, values["height"]),
        sha256=cast(bytes | None, values["sha256"]),
        verified_at=cast(datetime | None, values["verified_at"]),
        quarantine_reason=cast(str | None, values["quarantine_reason"]),
        created_at=cast(datetime, values["created_at"]),
        updated_at=cast(datetime, values["updated_at"]),
    )


_COLUMNS = """
id, owner_user_id, status::text AS status, storage_key, original_filename,
content_type, byte_size, width, height, sha256, verified_at, quarantine_reason,
created_at, updated_at
"""


class MediaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pending(
        self,
        *,
        asset_id: UUID,
        owner_user_id: UUID,
        storage_key: str,
        original_filename: str,
        content_type: str,
        byte_size: int,
    ) -> MediaAsset:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        INSERT INTO talaqi.media_assets (
                            id, owner_user_id, storage_key, original_filename,
                            content_type, byte_size
                        )
                        VALUES (
                            :asset_id, :owner_user_id, :storage_key, :original_filename,
                            :content_type, :byte_size
                        )
                        RETURNING id, owner_user_id, status::text AS status,
                                  storage_key, original_filename, content_type, byte_size,
                                  width, height, sha256, verified_at, quarantine_reason,
                                  created_at, updated_at
                        """
                    ),
                    {
                        "asset_id": asset_id,
                        "owner_user_id": owner_user_id,
                        "storage_key": storage_key,
                        "original_filename": original_filename,
                        "content_type": content_type,
                        "byte_size": byte_size,
                    },
                )
            )
            .mappings()
            .one()
        )
        return _asset(dict(row))

    async def get_owned(
        self,
        asset_id: UUID,
        owner_user_id: UUID,
        *,
        for_update: bool = False,
    ) -> MediaAsset | None:
        statement = (
            text(
                """
                SELECT id, owner_user_id, status::text AS status,
                       storage_key, original_filename, content_type, byte_size,
                       width, height, sha256, verified_at, quarantine_reason,
                       created_at, updated_at
                FROM talaqi.media_assets
                WHERE id = :asset_id AND owner_user_id = :owner_user_id
                FOR UPDATE
                """
            )
            if for_update
            else text(
                """
                SELECT id, owner_user_id, status::text AS status,
                       storage_key, original_filename, content_type, byte_size,
                       width, height, sha256, verified_at, quarantine_reason,
                       created_at, updated_at
                FROM talaqi.media_assets
                WHERE id = :asset_id AND owner_user_id = :owner_user_id
                """
            )
        )
        row = (
            (
                await self._session.execute(
                    statement,
                    {"asset_id": asset_id, "owner_user_id": owner_user_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else _asset(dict(row))

    async def mark_verified(
        self,
        asset: MediaAsset,
        *,
        storage_key: str,
        content_type: str,
        byte_size: int,
        width: int,
        height: int,
        sha256: bytes,
        verified_at: datetime,
    ) -> MediaAsset:
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        UPDATE talaqi.media_assets
                        SET status = 'verified', storage_key = :storage_key,
                            content_type = :content_type, byte_size = :byte_size,
                            width = :width, height = :height, sha256 = :sha256,
                            verified_at = :verified_at, quarantine_reason = NULL
                        WHERE id = :asset_id AND owner_user_id = :owner_user_id
                          AND status = 'pending'
                        RETURNING id, owner_user_id, status::text AS status,
                                  storage_key, original_filename, content_type, byte_size,
                                  width, height, sha256, verified_at, quarantine_reason,
                                  created_at, updated_at
                        """
                    ),
                    {
                        "asset_id": asset.id,
                        "owner_user_id": asset.owner_user_id,
                        "storage_key": storage_key,
                        "content_type": content_type,
                        "byte_size": byte_size,
                        "width": width,
                        "height": height,
                        "sha256": sha256,
                        "verified_at": verified_at,
                    },
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise RuntimeError("pending media asset transition was lost")
        return _asset(dict(row))

    async def mark_quarantined(
        self,
        asset: MediaAsset,
        *,
        reason: str,
        now: datetime,
    ) -> MediaAsset:
        del now
        row = (
            (
                await self._session.execute(
                    text(
                        """
                        UPDATE talaqi.media_assets
                        SET status = 'quarantined', quarantine_reason = :reason,
                            verified_at = NULL, sha256 = NULL
                        WHERE id = :asset_id AND owner_user_id = :owner_user_id
                          AND status = 'pending'
                        RETURNING id, owner_user_id, status::text AS status,
                                  storage_key, original_filename, content_type, byte_size,
                                  width, height, sha256, verified_at, quarantine_reason,
                                  created_at, updated_at
                        """
                    ),
                    {
                        "asset_id": asset.id,
                        "owner_user_id": asset.owner_user_id,
                        "reason": reason,
                    },
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise RuntimeError("pending media quarantine transition was lost")
        return _asset(dict(row))


__all__ = ["MediaRepository", "MediaRepositoryProtocol"]
