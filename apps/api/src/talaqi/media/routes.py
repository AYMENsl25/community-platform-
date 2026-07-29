from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from talaqi.identity.dependencies import CsrfProtection, CurrentPrincipal, DatabaseSession
from talaqi.media.local_storage import LocalMediaStorage
from talaqi.media.models import MAX_UPLOAD_BYTES, MediaAsset, validate_upload_intent
from talaqi.media.repository import MediaRepository
from talaqi.media.runtime import LazyMediaStorage
from talaqi.media.schemas import (
    MediaAssetResponse,
    MediaUploadCreateRequest,
    MediaUploadResponse,
    UploadGrantResponse,
)
from talaqi.media.service import MediaService, UploadSession
from talaqi.media.storage import StorageError
from talaqi.platform import IdempotencyCoordinator, IdempotencyRepository, hash_request_body
from talaqi.platform.errors import ApiError, ErrorEnvelope
from talaqi.runtime import LazySessionFactory

router = APIRouter(prefix="/api/v1/media", tags=["media"])

_AUTH: dict[str, Any] = {"model": ErrorEnvelope, "description": "Authentication required."}
_FORBIDDEN: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Verification, capability, ownership, or CSRF denied.",
}
_NOT_FOUND: dict[str, Any] = {"model": ErrorEnvelope, "description": "Media asset not found."}
_CONFLICT: dict[str, Any] = {
    "model": ErrorEnvelope,
    "description": "Upload state or idempotency conflict.",
}
_INVALID: dict[str, Any] = {"model": ErrorEnvelope, "description": "Media input rejected."}

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=16,
        max_length=200,
        description="Stable key for retrying this media mutation.",
    ),
]
UploadToken = Annotated[
    str,
    Header(alias="X-Talaqi-Upload-Token", min_length=32, max_length=2_048),
]
DeclaredContentType = Annotated[
    str,
    Header(alias="Content-Type", min_length=9, max_length=64),
]


def _service(request: Request, session: AsyncSession) -> MediaService:
    runtime: LazyMediaStorage = request.app.state.media_storage_runtime
    settings = request.app.state.settings_factory()
    return MediaService(
        MediaRepository(session),
        runtime.resolve(),
        upload_grant_seconds=settings.media_upload_grant_seconds,
        max_image_pixels=settings.media_max_image_pixels,
    )


def _asset(asset: MediaAsset) -> MediaAssetResponse:
    if asset.status not in {"pending", "verified"}:
        raise RuntimeError("non-public media status cannot be serialized")
    return MediaAssetResponse(
        id=asset.id,
        status="pending" if asset.status == "pending" else "verified",
        original_filename=asset.original_filename,
        content_type=asset.content_type,
        byte_size=asset.byte_size,
        width=asset.width,
        height=asset.height,
        verified_at=asset.verified_at,
    )


def _upload(value: UploadSession) -> MediaUploadResponse:
    return MediaUploadResponse(
        **_asset(value.asset).model_dump(),
        upload=UploadGrantResponse(
            method="PUT",
            url=value.grant.url,
            headers=value.grant.headers,
            expires_at=value.grant.expires_at,
        ),
    )


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie"


async def _acquire(
    request: Request,
    session: AsyncSession,
    *,
    actor_id: UUID,
    key: str,
    route_fingerprint: str,
    request_hash_override: bytes | None = None,
):
    current = datetime.now(UTC)
    runtime: LazySessionFactory = request.app.state.database_runtime
    repository = IdempotencyRepository(runtime.resolve())
    acquisition = await IdempotencyCoordinator(repository).acquire(
        actor_id=actor_id,
        http_method="POST",
        route_fingerprint=route_fingerprint,
        key=key,
        request_hash=(request_hash_override or hash_request_body(await request.body())),
        now=current,
        lease_duration=timedelta(seconds=30),
        expires_at=current + timedelta(hours=24),
        session=session,
    )
    return repository, acquisition, current


@router.post(
    "/uploads",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createMediaUpload",
    responses={401: _AUTH, 403: _FORBIDDEN, 409: _CONFLICT, 422: _INVALID},
)
async def create_media_upload(
    body: MediaUploadCreateRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
    idempotency_key: IdempotencyKey,
) -> MediaUploadResponse:
    _private(response)
    idempotency, acquisition, current = await _acquire(
        request,
        session,
        actor_id=principal.user_id,
        key=idempotency_key,
        route_fingerprint="/api/v1/media/uploads",
    )
    if acquisition.outcome == "replay":
        replayed = MediaAssetResponse.model_validate(acquisition.response_body)
        return _upload(
            await _service(request, session).resume_upload(
                principal,
                replayed.id,
                now=current,
            )
        )
    if acquisition.claim is None:
        raise RuntimeError("acquired idempotency operation has no claim")
    result = _upload(
        await _service(request, session).create_upload(
            principal,
            validate_upload_intent(
                body.original_filename,
                body.content_type,
                body.byte_size,
            ),
            now=current,
        )
    )
    await idempotency.complete(
        acquisition.claim,
        response_status=status.HTTP_201_CREATED,
        # Signed upload grants are bearer capabilities. Persist only stable
        # asset metadata and mint a new grant for an idempotent replay.
        response_body=MediaAssetResponse.model_validate(
            result.model_dump(exclude={"upload"})
        ).model_dump(mode="json"),
        completed_at=datetime.now(UTC),
        session=session,
    )
    return result


@router.put(
    "/uploads/{asset_id:uuid}/content",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="putLocalMediaUpload",
    include_in_schema=False,
)
async def put_local_media_upload(
    asset_id: UUID,
    request: Request,
    response: Response,
    upload_token: UploadToken,
    content_type: DeclaredContentType,
) -> None:
    response.headers["Cache-Control"] = "no-store"
    runtime: LazyMediaStorage = request.app.state.media_storage_runtime
    storage = runtime.resolve()
    if not isinstance(storage, LocalMediaStorage):
        raise ApiError(code="not_found", message_key="errors.not_found", status_code=404)
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_UPLOAD_BYTES:
            raise ApiError(
                code="media_too_large",
                message_key="errors.validation",
                status_code=422,
            )
    try:
        await asyncio.to_thread(
            storage.accept_signed_upload,
            asset_id=asset_id,
            content_type=content_type,
            content=bytes(content),
            token=upload_token,
        )
    except StorageError:
        raise ApiError(code="not_found", message_key="errors.not_found", status_code=404) from None


@router.post(
    "/uploads/{asset_id:uuid}/complete",
    response_model=MediaAssetResponse,
    operation_id="completeMediaUpload",
    responses={
        401: _AUTH,
        403: _FORBIDDEN,
        404: _NOT_FOUND,
        409: _CONFLICT,
        422: _INVALID,
        503: {"model": ErrorEnvelope, "description": "Storage temporarily unavailable."},
    },
)
async def complete_media_upload(
    asset_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    _csrf: CsrfProtection,
    idempotency_key: IdempotencyKey,
) -> MediaAssetResponse:
    _private(response)
    idempotency, acquisition, current = await _acquire(
        request,
        session,
        actor_id=principal.user_id,
        key=idempotency_key,
        route_fingerprint="/api/v1/media/uploads/{asset_id}/complete",
        request_hash_override=hash_request_body(str(asset_id).encode("ascii")),
    )
    if acquisition.outcome == "replay":
        return MediaAssetResponse.model_validate(acquisition.response_body)
    if acquisition.claim is None:
        raise RuntimeError("acquired idempotency operation has no claim")
    result = _asset(
        await _service(request, session).complete_upload(
            principal,
            asset_id,
            now=current,
        )
    )
    await idempotency.complete(
        acquisition.claim,
        response_status=status.HTTP_200_OK,
        response_body=result.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
        session=session,
    )
    return result


__all__ = ["router"]
