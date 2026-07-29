from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from urllib.parse import quote
from uuid import UUID

from talaqi.media.storage import StorageError, UploadGrant, validate_storage_key


def _encode_token(payload: dict[str, object], secret: bytes) -> str:
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret, encoded, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(encoded + signature).rstrip(b"=").decode("ascii")


def _decode_token(token: str, secret: bytes) -> dict[str, object]:
    try:
        padding = "=" * (-len(token) % 4)
        signed = base64.b64decode(token + padding, altchars=b"-_", validate=True)
        if len(signed) <= hashlib.sha256().digest_size:
            raise ValueError
        payload, provided = signed[:-32], signed[-32:]
        expected = hmac.new(secret, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(provided, expected):
            raise ValueError
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise ValueError
        return cast(dict[str, object], value)
    except (ValueError, TypeError, json.JSONDecodeError):
        raise StorageError("invalid_upload_grant") from None


class LocalMediaStorage:
    def __init__(
        self,
        root: Path,
        *,
        api_public_url: str,
        signing_secret: bytes,
    ) -> None:
        if not signing_secret:
            raise ValueError("local media signing secret must not be empty")
        self._root = root.resolve()
        self._api_public_url = api_public_url.rstrip("/")
        self._secret = signing_secret

    def _path(self, storage_key: str) -> Path:
        key = validate_storage_key(storage_key)
        candidate = (self._root / Path(*key.split("/"))).resolve()
        if not candidate.is_relative_to(self._root):
            raise StorageError("invalid_storage_key")
        return candidate

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
        self._path(storage_key)
        if expires_at.tzinfo is None:
            raise ValueError("upload expiry must be timezone-aware")
        payload: dict[str, object] = {
            "asset": str(asset_id),
            "content_type": content_type,
            "exp": int(expires_at.timestamp()),
            "key": storage_key,
            "size": byte_size,
        }
        token = _encode_token(payload, self._secret)
        return UploadGrant(
            method="PUT",
            url=(
                f"{self._api_public_url}/api/v1/media/uploads/"
                f"{quote(str(asset_id), safe='')}/content"
            ),
            headers={
                "Content-Type": content_type,
                "X-Talaqi-Upload-Token": token,
            },
            expires_at=expires_at,
        )

    def accept_upload(
        self,
        *,
        asset_id: UUID,
        storage_key: str,
        content_type: str,
        expected_size: int,
        content: bytes,
        token: str,
        now: datetime | None = None,
    ) -> None:
        current = now or datetime.now(UTC)
        payload = _decode_token(token, self._secret)
        expected: dict[str, object] = {
            "asset": str(asset_id),
            "content_type": content_type,
            "key": storage_key,
            "size": expected_size,
        }
        expiry = payload.get("exp")
        if (
            any(payload.get(key) != value for key, value in expected.items())
            or type(expiry) is not int
            or expiry < int(current.timestamp())
            or len(content) != expected_size
        ):
            raise StorageError("invalid_upload_grant")
        self._write_atomic(self._path(storage_key), content)

    @staticmethod
    def _write_atomic(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=".upload-")
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as target:
                target.write(content)
                target.flush()
                os.fsync(target.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    def accept_signed_upload(
        self,
        *,
        asset_id: UUID,
        content_type: str,
        content: bytes,
        token: str,
        now: datetime | None = None,
    ) -> None:
        payload = _decode_token(token, self._secret)
        storage_key = payload.get("key")
        expected_size = payload.get("size")
        if (
            not isinstance(storage_key, str)
            or type(expected_size) is not int
            or payload.get("content_type") != content_type
        ):
            raise StorageError("invalid_upload_grant")
        self.accept_upload(
            asset_id=asset_id,
            storage_key=storage_key,
            content_type=content_type,
            expected_size=expected_size,
            content=content,
            token=token,
            now=now,
        )

    async def read(self, storage_key: str, *, max_bytes: int) -> bytes:
        if max_bytes < 1:
            raise ValueError("maximum read size must be positive")
        path = self._path(storage_key)

        def bounded_read() -> bytes:
            try:
                with path.open("rb") as source:
                    content = source.read(max_bytes + 1)
            except FileNotFoundError:
                raise StorageError("object_missing") from None
            if len(content) > max_bytes:
                raise StorageError("object_too_large")
            return content

        return await asyncio.to_thread(bounded_read)

    async def replace(self, storage_key: str, content: bytes, content_type: str) -> None:
        del content_type
        path = self._path(storage_key)
        await asyncio.to_thread(self._write_atomic, path, content)

    async def delete(self, storage_key: str) -> None:
        path = self._path(storage_key)
        await asyncio.to_thread(path.unlink, missing_ok=True)

    async def ready(self) -> bool:
        try:
            await asyncio.to_thread(self._root.mkdir, parents=True, exist_ok=True)
            return self._root.is_dir()
        except OSError:
            return False


__all__ = ["LocalMediaStorage"]
