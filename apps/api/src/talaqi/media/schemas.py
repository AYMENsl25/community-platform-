from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MediaUploadCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    original_filename: str = Field(min_length=1, max_length=255)
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    byte_size: int = Field(ge=1, le=10_485_760)


class UploadGrantResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    method: Literal["PUT"]
    url: str = Field(min_length=1, max_length=8_192)
    headers: dict[str, str]
    expires_at: datetime


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    status: Literal["pending", "verified"]
    original_filename: str
    content_type: str
    byte_size: int
    width: int | None
    height: int | None
    verified_at: datetime | None


class MediaUploadResponse(MediaAssetResponse):
    upload: UploadGrantResponse


__all__ = [
    "MediaAssetResponse",
    "MediaUploadCreateRequest",
    "MediaUploadResponse",
    "UploadGrantResponse",
]
