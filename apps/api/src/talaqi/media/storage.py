from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

_STORAGE_KEY = re.compile(
    r"^media/[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/"
    r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/"
    r"(?:source|canonical\.webp)$"
)


class StorageError(RuntimeError):
    def __init__(self, code: str, *, retryable: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class UploadGrant:
    method: str
    url: str
    headers: dict[str, str]
    expires_at: datetime


class MediaStorage(Protocol):
    def create_upload_grant(
        self,
        *,
        asset_id: UUID,
        storage_key: str,
        content_type: str,
        byte_size: int,
        expires_at: datetime,
        now: datetime | None = None,
    ) -> UploadGrant: ...

    async def read(self, storage_key: str, *, max_bytes: int) -> bytes: ...

    async def replace(self, storage_key: str, content: bytes, content_type: str) -> None: ...

    async def delete(self, storage_key: str) -> None: ...

    async def ready(self) -> bool: ...


def validate_storage_key(storage_key: str) -> str:
    if _STORAGE_KEY.fullmatch(storage_key) is None:
        raise StorageError("invalid_storage_key")
    return storage_key


__all__ = [
    "MediaStorage",
    "StorageError",
    "UploadGrant",
    "validate_storage_key",
]
