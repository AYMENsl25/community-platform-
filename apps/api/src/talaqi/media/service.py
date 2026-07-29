from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from talaqi.db.identifiers import generate_uuid7, validate_uuid7
from talaqi.identity.models import AuthPrincipal
from talaqi.media.models import (
    MAX_UPLOAD_BYTES,
    MediaAsset,
    MediaValidationError,
    UploadIntent,
    build_storage_key,
    build_verified_storage_key,
)
from talaqi.media.repository import MediaRepositoryProtocol
from talaqi.media.storage import MediaStorage, StorageError, UploadGrant
from talaqi.media.verifier import verify_and_canonicalize
from talaqi.platform import ApiError


@dataclass(frozen=True, slots=True)
class UploadSession:
    asset: MediaAsset
    grant: UploadGrant


def _not_found() -> ApiError:
    return ApiError(code="not_found", message_key="errors.not_found", status_code=404)


class MediaService:
    def __init__(
        self,
        repository: MediaRepositoryProtocol,
        storage: MediaStorage,
        *,
        upload_grant_seconds: int,
        max_image_pixels: int = 40_000_000,
    ) -> None:
        if not 60 <= upload_grant_seconds <= 3_600:
            raise ValueError("upload grant lifetime must be between 60 and 3600 seconds")
        if max_image_pixels < 1:
            raise ValueError("maximum image pixels must be positive")
        self._repository = repository
        self._storage = storage
        self._upload_grant_seconds = upload_grant_seconds
        self._max_image_pixels = max_image_pixels

    @staticmethod
    def _require_verified_actor(principal: AuthPrincipal) -> None:
        if principal.status != "active":
            raise ApiError(code="forbidden", message_key="errors.forbidden", status_code=403)
        if not principal.email_verified:
            raise ApiError(
                code="email_verification_required",
                message_key="blockers.email_verification_required",
                status_code=403,
            )

    async def create_upload(
        self,
        principal: AuthPrincipal,
        intent: UploadIntent,
        *,
        now: datetime | None = None,
    ) -> UploadSession:
        self._require_verified_actor(principal)
        current = now or datetime.now(UTC)
        asset_id = generate_uuid7()
        storage_key = build_storage_key(principal.user_id, asset_id)
        asset = await self._repository.create_pending(
            asset_id=asset_id,
            owner_user_id=principal.user_id,
            storage_key=storage_key,
            original_filename=intent.original_filename,
            content_type=intent.content_type,
            byte_size=intent.byte_size,
        )
        expires_at = current + timedelta(seconds=self._upload_grant_seconds)
        grant = self._storage.create_upload_grant(
            asset_id=asset.id,
            storage_key=asset.storage_key,
            content_type=asset.content_type,
            byte_size=asset.byte_size,
            expires_at=expires_at,
            now=current,
        )
        return UploadSession(asset=asset, grant=grant)

    async def resume_upload(
        self,
        principal: AuthPrincipal,
        asset_id: UUID,
        *,
        now: datetime | None = None,
    ) -> UploadSession:
        self._require_verified_actor(principal)
        try:
            identifier = validate_uuid7(asset_id)
        except ValueError:
            raise _not_found() from None
        asset = await self._repository.get_owned(identifier, principal.user_id)
        if asset is None or asset.status != "pending":
            raise _not_found()
        current = now or datetime.now(UTC)
        grant = self._storage.create_upload_grant(
            asset_id=asset.id,
            storage_key=asset.storage_key,
            content_type=asset.content_type,
            byte_size=asset.byte_size,
            expires_at=current + timedelta(seconds=self._upload_grant_seconds),
            now=current,
        )
        return UploadSession(asset=asset, grant=grant)

    async def complete_upload(
        self,
        principal: AuthPrincipal,
        asset_id: UUID,
        *,
        now: datetime | None = None,
    ) -> MediaAsset:
        self._require_verified_actor(principal)
        try:
            identifier = validate_uuid7(asset_id)
        except ValueError:
            raise _not_found() from None
        asset = await self._repository.get_owned(identifier, principal.user_id, for_update=True)
        if asset is None:
            raise _not_found()
        if asset.status == "verified":
            return asset
        if asset.status != "pending":
            raise _not_found()

        try:
            source = await self._storage.read(asset.storage_key, max_bytes=MAX_UPLOAD_BYTES + 1)
        except StorageError as error:
            if error.code == "object_too_large":
                await self._quarantine(asset, "media_too_large", now=now)
                raise ApiError(
                    code="media_too_large",
                    message_key="errors.validation",
                    status_code=422,
                ) from None
            raise ApiError(
                code="media_not_ready" if error.retryable else "media_unavailable",
                message_key="errors.conflict" if error.retryable else "errors.unavailable",
                status_code=409 if error.retryable else 503,
            ) from None
        if len(source) != asset.byte_size:
            await self._quarantine(asset, "invalid_media", now=now)
            raise ApiError(
                code="invalid_media",
                message_key="errors.validation",
                status_code=422,
            )
        try:
            verified = await asyncio.to_thread(
                verify_and_canonicalize,
                source,
                asset.content_type,
                max_pixels=self._max_image_pixels,
            )
        except MediaValidationError as error:
            await self._quarantine(asset, error.code, now=now)
            raise ApiError(
                code=error.code,
                message_key="errors.validation",
                status_code=422,
            ) from None

        canonical_key = build_verified_storage_key(asset.owner_user_id, asset.id)
        try:
            await self._storage.replace(canonical_key, verified.content, verified.content_type)
        except StorageError:
            raise ApiError(
                code="media_unavailable",
                message_key="errors.unavailable",
                status_code=503,
            ) from None
        current = now or datetime.now(UTC)
        completed = await self._repository.mark_verified(
            asset,
            storage_key=canonical_key,
            content_type=verified.content_type,
            byte_size=verified.byte_size,
            width=verified.width,
            height=verified.height,
            sha256=verified.sha256,
            verified_at=current,
        )
        with contextlib.suppress(StorageError):
            await self._storage.delete(asset.storage_key)
        return completed

    async def _quarantine(
        self,
        asset: MediaAsset,
        reason: str,
        *,
        now: datetime | None,
    ) -> None:
        with contextlib.suppress(StorageError):
            await self._storage.delete(asset.storage_key)
        await self._repository.mark_quarantined(
            asset,
            reason=reason[:128],
            now=now or datetime.now(UTC),
        )

    async def require_verified_owned(self, asset_id: UUID, owner_user_id: UUID) -> MediaAsset:
        try:
            identifier = validate_uuid7(asset_id)
            owner = validate_uuid7(owner_user_id)
        except ValueError:
            raise _not_found() from None
        asset = await self._repository.get_owned(identifier, owner)
        if asset is None or asset.status != "verified":
            raise _not_found()
        return asset


__all__ = ["MediaService", "UploadSession"]
