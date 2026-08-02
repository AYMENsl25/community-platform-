from __future__ import annotations

import io
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from PIL import Image
from talaqi.db.identifiers import generate_uuid7
from talaqi.identity.models import AuthPrincipal
from talaqi.media.models import MediaAsset, validate_upload_intent
from talaqi.media.service import MediaService
from talaqi.media.storage import StorageError, UploadGrant
from talaqi.platform import ApiError

NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)


def principal(*, verified: bool = True, status: str = "active") -> AuthPrincipal:
    return AuthPrincipal(
        user_id=generate_uuid7(),
        session_id=generate_uuid7(),
        email_verified=verified,
        status=status,  # pyright: ignore[reportArgumentType]
        is_platform_admin=False,
    )


def png() -> bytes:
    target = io.BytesIO()
    Image.new("RGB", (8, 6), (20, 40, 60)).save(target, format="PNG")
    return target.getvalue()


class FakeRepository:
    def __init__(self) -> None:
        self.assets: dict[UUID, MediaAsset] = {}

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
        asset = MediaAsset(
            id=asset_id,
            owner_user_id=owner_user_id,
            status="pending",
            storage_key=storage_key,
            original_filename=original_filename,
            content_type=content_type,
            byte_size=byte_size,
            width=None,
            height=None,
            sha256=None,
            verified_at=None,
            quarantine_reason=None,
            created_at=NOW,
            updated_at=NOW,
        )
        self.assets[asset_id] = asset
        return asset

    async def get_owned(
        self, asset_id: UUID, owner_user_id: UUID, *, for_update: bool = False
    ) -> MediaAsset | None:
        del for_update
        asset = self.assets.get(asset_id)
        return asset if asset is not None and asset.owner_user_id == owner_user_id else None

    async def get_public(self, asset_id: UUID) -> MediaAsset | None:
        asset = self.assets.get(asset_id)
        return asset if asset is not None and asset.status == "verified" else None

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
        updated = replace(
            asset,
            status="verified",
            storage_key=storage_key,
            content_type=content_type,
            byte_size=byte_size,
            width=width,
            height=height,
            sha256=sha256,
            verified_at=verified_at,
            updated_at=verified_at,
        )
        self.assets[asset.id] = updated
        return updated

    async def mark_quarantined(
        self, asset: MediaAsset, *, reason: str, now: datetime
    ) -> MediaAsset:
        updated = replace(
            asset,
            status="quarantined",
            quarantine_reason=reason,
            updated_at=now,
        )
        self.assets[asset.id] = updated
        return updated


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def create_upload_grant(
        self,
        *,
        asset_id: UUID,
        storage_key: str,
        content_type: str,
        byte_size: int,
        expires_at: datetime,
        now: datetime | None = None,
    ) -> UploadGrant:
        del asset_id, storage_key, content_type, byte_size, now
        return UploadGrant("PUT", "http://upload.test", {}, expires_at)

    async def read(self, storage_key: str, *, max_bytes: int) -> bytes:
        value = self.objects.get(storage_key)
        if value is None:
            raise StorageError("object_missing", retryable=True)
        if len(value) > max_bytes:
            raise StorageError("object_too_large")
        return value

    async def replace(self, storage_key: str, content: bytes, content_type: str) -> None:
        del content_type
        self.objects[storage_key] = content

    async def delete(self, storage_key: str) -> None:
        self.objects.pop(storage_key, None)

    async def ready(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_create_is_owner_scoped_and_rejects_unverified_actor() -> None:
    repository = FakeRepository()
    storage = FakeStorage()
    service = MediaService(repository, storage, upload_grant_seconds=600)
    actor = principal()

    result = await service.create_upload(
        actor,
        validate_upload_intent("cover.png", "image/png", len(png())),
        now=NOW,
    )

    assert result.asset.owner_user_id == actor.user_id
    assert result.asset.storage_key.startswith(f"media/{actor.user_id}/{result.asset.id}/")
    assert result.grant.expires_at == NOW + timedelta(seconds=600)
    with pytest.raises(ApiError, match="email_verification_required"):
        await service.create_upload(
            principal(verified=False),
            validate_upload_intent("cover.png", "image/png", len(png())),
            now=NOW,
        )


@pytest.mark.asyncio
async def test_complete_canonicalizes_then_marks_verified_and_is_idempotent() -> None:
    repository = FakeRepository()
    storage = FakeStorage()
    service = MediaService(repository, storage, upload_grant_seconds=600)
    actor = principal()
    source = png()
    created = await service.create_upload(
        actor,
        validate_upload_intent("cover.png", "image/png", len(source)),
        now=NOW,
    )
    storage.objects[created.asset.storage_key] = source

    completed = await service.complete_upload(actor, created.asset.id, now=NOW)
    replay = await service.complete_upload(actor, created.asset.id, now=NOW)

    assert completed.status == "verified"
    assert completed.content_type == "image/webp"
    assert completed.storage_key.endswith("/canonical.webp")
    assert completed.storage_key in storage.objects
    assert created.asset.storage_key not in storage.objects
    assert replay == completed


@pytest.mark.asyncio
async def test_complete_hides_foreign_asset_and_quarantines_invalid_bytes() -> None:
    repository = FakeRepository()
    storage = FakeStorage()
    service = MediaService(repository, storage, upload_grant_seconds=600)
    owner = principal()
    outsider = principal()
    created = await service.create_upload(
        owner,
        validate_upload_intent("cover.png", "image/png", 8),
        now=NOW,
    )
    storage.objects[created.asset.storage_key] = b"notimage"

    with pytest.raises(ApiError, match="not_found"):
        await service.complete_upload(outsider, created.asset.id, now=NOW)
    with pytest.raises(ApiError, match="invalid_media"):
        await service.complete_upload(owner, created.asset.id, now=NOW)

    assert repository.assets[created.asset.id].status == "quarantined"
    assert created.asset.storage_key not in storage.objects
