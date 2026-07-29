from __future__ import annotations

import httpx
import pytest
from talaqi.media.s3_storage import S3MediaStorage
from talaqi.media.storage import StorageError

KEY = "media/018f0000-0000-7000-8000-000000000101/018f0000-0000-7000-8000-000000000102/source"
CANONICAL_KEY = KEY.replace("/source", "/canonical.webp")


def adapter(handler: httpx.MockTransport) -> S3MediaStorage:
    return S3MediaStorage(
        endpoint="https://storage.example.com",
        bucket="media",
        access_key="access",
        secret_key="do-not-disclose",  # pragma: allowlist secret
        transport=handler,
    )


@pytest.mark.asyncio
async def test_s3_object_operations_are_signed_and_bounded() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            assert request.headers["range"] == "bytes=0-8"
            return httpx.Response(206, content=b"12345678")
        if request.method == "HEAD":
            return httpx.Response(200)
        return httpx.Response(204)

    storage = adapter(httpx.MockTransport(handle))

    assert await storage.read(KEY, max_bytes=8) == b"12345678"
    await storage.replace(CANONICAL_KEY, b"webp", "image/webp")
    await storage.delete(KEY)
    assert await storage.ready()
    assert [request.method for request in requests] == ["GET", "PUT", "DELETE", "HEAD"]
    assert all("AWS4-HMAC-SHA256" in request.headers["authorization"] for request in requests)
    assert all("do-not-disclose" not in request.headers["authorization"] for request in requests)


@pytest.mark.asyncio
async def test_s3_read_rejects_range_response_over_bound_and_missing_is_retryable() -> None:
    oversized = adapter(
        httpx.MockTransport(lambda request: httpx.Response(206, content=b"123456789"))
    )
    with pytest.raises(StorageError, match="object_too_large"):
        await oversized.read(KEY, max_bytes=8)

    missing = adapter(httpx.MockTransport(lambda request: httpx.Response(404)))
    with pytest.raises(StorageError, match="object_missing") as error:
        await missing.read(KEY, max_bytes=8)
    assert error.value.retryable
