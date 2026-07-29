from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from talaqi.db.identifiers import validate_uuid7

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_DIMENSION = 12_000
DEFAULT_MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

MediaStatus = Literal["pending", "verified", "quarantined", "deleted"]


class MediaValidationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class UploadIntent:
    original_filename: str
    content_type: str
    byte_size: int


@dataclass(frozen=True, slots=True)
class MediaAsset:
    id: UUID
    owner_user_id: UUID
    status: MediaStatus
    storage_key: str
    original_filename: str
    content_type: str
    byte_size: int
    width: int | None
    height: int | None
    sha256: bytes | None
    verified_at: datetime | None
    quarantine_reason: str | None
    created_at: datetime
    updated_at: datetime


def validate_upload_intent(
    original_filename: str, content_type: str, byte_size: int
) -> UploadIntent:
    filename = original_filename.strip()
    if (
        not filename
        or filename in {".", ".."}
        or len(filename) > 255
        or "/" in filename
        or "\\" in filename
        or any(unicodedata.category(character).startswith("C") for character in filename)
    ):
        raise MediaValidationError("invalid_media")
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise MediaValidationError("invalid_media")
    if type(byte_size) is not int or not 1 <= byte_size <= MAX_UPLOAD_BYTES:
        code = (
            "media_too_large"
            if type(byte_size) is int and byte_size > MAX_UPLOAD_BYTES
            else "invalid_media"
        )
        raise MediaValidationError(code)
    return UploadIntent(
        original_filename=filename,
        content_type=content_type,
        byte_size=byte_size,
    )


def build_storage_key(owner_user_id: UUID, asset_id: UUID) -> str:
    owner = validate_uuid7(owner_user_id)
    asset = validate_uuid7(asset_id)
    return f"media/{owner}/{asset}/source"


def build_verified_storage_key(owner_user_id: UUID, asset_id: UUID) -> str:
    owner = validate_uuid7(owner_user_id)
    asset = validate_uuid7(asset_id)
    return f"media/{owner}/{asset}/canonical.webp"


__all__ = [
    "ALLOWED_CONTENT_TYPES",
    "DEFAULT_MAX_IMAGE_PIXELS",
    "MAX_IMAGE_DIMENSION",
    "MAX_UPLOAD_BYTES",
    "MediaAsset",
    "MediaStatus",
    "MediaValidationError",
    "UploadIntent",
    "build_storage_key",
    "build_verified_storage_key",
    "validate_upload_intent",
]
