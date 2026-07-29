from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlencode, urlsplit
from uuid import UUID

import httpx

from talaqi.media.storage import StorageError, UploadGrant, validate_storage_key

_MAX_PRESIGN_SECONDS = 604_800


def _hmac(key: bytes, value: str) -> bytes:
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret: str, date: str, region: str) -> bytes:
    date_key = _hmac(("AWS4" + secret).encode("utf-8"), date)
    region_key = _hmac(date_key, region)
    service_key = _hmac(region_key, "s3")
    return _hmac(service_key, "aws4_request")


def _encode_path(value: str) -> str:
    return "/".join(quote(segment, safe="-_.~") for segment in value.split("/"))


class S3MediaStorage:
    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        parsed = urlsplit(endpoint.rstrip("/"))
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname is None
            or parsed.query
            or parsed.fragment
            or not bucket
            or "/" in bucket
            or not access_key
            or not secret_key
        ):
            raise ValueError("invalid S3-compatible storage configuration")
        self._endpoint = endpoint.rstrip("/")
        self._base_path = parsed.path.rstrip("/")
        self._host = parsed.netloc
        self._bucket = bucket
        self._access_key = access_key
        self._secret_key = secret_key
        self._region = region
        self._transport = transport

    def _canonical_uri(self, storage_key: str | None = None) -> str:
        suffix = self._bucket if storage_key is None else f"{self._bucket}/{storage_key}"
        return _encode_path(f"{self._base_path}/{suffix}")

    def _url(self, storage_key: str | None = None) -> str:
        suffix = (
            self._bucket if storage_key is None else f"{self._bucket}/{_encode_path(storage_key)}"
        )
        return f"{self._endpoint}/{suffix}"

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
        del asset_id
        key = validate_storage_key(storage_key)
        current = (now or datetime.now(UTC)).astimezone(UTC)
        if expires_at.tzinfo is None:
            raise ValueError("upload expiry must be timezone-aware")
        expires = max(
            1,
            min(
                _MAX_PRESIGN_SECONDS,
                int((expires_at.astimezone(UTC) - current).total_seconds()),
            ),
        )
        timestamp = current.strftime("%Y%m%dT%H%M%SZ")
        date = current.strftime("%Y%m%d")
        scope = f"{date}/{self._region}/s3/aws4_request"
        signed_headers = "content-type;host;x-amz-meta-declared-size"
        query = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{self._access_key}/{scope}",
            "X-Amz-Date": timestamp,
            "X-Amz-Expires": str(expires),
            "X-Amz-SignedHeaders": signed_headers,
        }
        canonical_query = urlencode(sorted(query.items()), quote_via=quote, safe="-_.~")
        canonical_headers = (
            f"content-type:{content_type}\n"
            f"host:{self._host}\n"
            f"x-amz-meta-declared-size:{byte_size}\n"
        )
        canonical_request = "\n".join(
            (
                "PUT",
                self._canonical_uri(key),
                canonical_query,
                canonical_headers,
                signed_headers,
                "UNSIGNED-PAYLOAD",
            )
        )
        string_to_sign = "\n".join(
            (
                "AWS4-HMAC-SHA256",
                timestamp,
                scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            )
        )
        signature = hmac.new(
            _signing_key(self._secret_key, date, self._region),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return UploadGrant(
            method="PUT",
            url=f"{self._url(key)}?{canonical_query}&X-Amz-Signature={signature}",
            headers={
                "Content-Type": content_type,
                "X-Amz-Meta-Declared-Size": str(byte_size),
            },
            expires_at=current + timedelta(seconds=expires),
        )

    def _signed_headers(
        self,
        method: str,
        *,
        storage_key: str | None,
        content: bytes,
        content_type: str | None,
        now: datetime,
    ) -> dict[str, str]:
        payload_hash = hashlib.sha256(content).hexdigest()
        timestamp = now.strftime("%Y%m%dT%H%M%SZ")
        date = now.strftime("%Y%m%d")
        headers = {
            "host": self._host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": timestamp,
        }
        if content_type is not None:
            headers["content-type"] = content_type
        signed_headers = ";".join(sorted(headers))
        canonical_headers = "".join(f"{key}:{headers[key]}\n" for key in sorted(headers))
        canonical_request = "\n".join(
            (
                method,
                self._canonical_uri(storage_key),
                "",
                canonical_headers,
                signed_headers,
                payload_hash,
            )
        )
        scope = f"{date}/{self._region}/s3/aws4_request"
        string_to_sign = "\n".join(
            (
                "AWS4-HMAC-SHA256",
                timestamp,
                scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            )
        )
        signature = hmac.new(
            _signing_key(self._secret_key, date, self._region),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers["authorization"] = (
            f"AWS4-HMAC-SHA256 Credential={self._access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        headers.pop("host")
        return headers

    async def _request(
        self,
        method: str,
        *,
        storage_key: str | None,
        content: bytes = b"",
        content_type: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        now = datetime.now(UTC)
        headers = self._signed_headers(
            method,
            storage_key=storage_key,
            content=content,
            content_type=content_type,
            now=now,
        )
        headers.update(extra_headers or {})
        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                timeout=httpx.Timeout(10.0, connect=3.0),
            ) as client:
                return await client.request(
                    method,
                    self._url(storage_key),
                    headers=headers,
                    content=content,
                )
        except httpx.HTTPError:
            raise StorageError("storage_unavailable", retryable=True) from None

    @staticmethod
    def _check(response: httpx.Response, *, missing_retryable: bool = False) -> None:
        if response.status_code in {200, 201, 202, 204, 206}:
            return
        if response.status_code == 404:
            raise StorageError("object_missing", retryable=missing_retryable)
        raise StorageError(
            "storage_unavailable",
            retryable=response.status_code >= 500,
        )

    async def read(self, storage_key: str, *, max_bytes: int) -> bytes:
        key = validate_storage_key(storage_key)
        if max_bytes < 1:
            raise ValueError("maximum read size must be positive")
        headers = self._signed_headers(
            "GET",
            storage_key=key,
            content=b"",
            content_type=None,
            now=datetime.now(UTC),
        )
        headers["Range"] = f"bytes=0-{max_bytes}"
        content = bytearray()
        try:
            async with (
                httpx.AsyncClient(
                    transport=self._transport,
                    timeout=httpx.Timeout(10.0, connect=3.0),
                ) as client,
                client.stream(
                    "GET",
                    self._url(key),
                    headers=headers,
                ) as response,
            ):
                self._check(response, missing_retryable=True)
                async for chunk in response.aiter_bytes():
                    remaining = max_bytes + 1 - len(content)
                    content.extend(chunk[:remaining])
                    if len(content) > max_bytes:
                        raise StorageError("object_too_large")
        except StorageError:
            raise
        except httpx.HTTPError:
            raise StorageError("storage_unavailable", retryable=True) from None
        return bytes(content)

    async def replace(self, storage_key: str, content: bytes, content_type: str) -> None:
        key = validate_storage_key(storage_key)
        response = await self._request(
            "PUT",
            storage_key=key,
            content=content,
            content_type=content_type,
        )
        self._check(response)

    async def delete(self, storage_key: str) -> None:
        key = validate_storage_key(storage_key)
        response = await self._request("DELETE", storage_key=key)
        if response.status_code == 404:
            return
        self._check(response)

    async def ready(self) -> bool:
        try:
            response = await self._request("HEAD", storage_key=None)
            return response.status_code in {200, 204}
        except StorageError:
            return False


__all__ = ["S3MediaStorage"]
