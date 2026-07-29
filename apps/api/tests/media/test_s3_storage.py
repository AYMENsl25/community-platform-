from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from talaqi.media.s3_storage import S3MediaStorage

ASSET_ID = UUID("018f0000-0000-7000-8000-000000000102")
KEY = "media/018f0000-0000-7000-8000-000000000101/018f0000-0000-7000-8000-000000000102/source"


def test_s3_grant_is_path_style_sigv4_without_secret_disclosure() -> None:
    adapter = S3MediaStorage(
        endpoint="http://localhost:9000",
        bucket="talaqi-local",
        access_key="local-access",
        secret_key="do-not-disclose",  # pragma: allowlist secret
        region="us-east-1",
    )

    grant = adapter.create_upload_grant(
        asset_id=ASSET_ID,
        storage_key=KEY,
        content_type="image/png",
        byte_size=128,
        expires_at=datetime(2026, 7, 28, 12, 10, tzinfo=UTC),
        now=datetime(2026, 7, 28, 12, tzinfo=UTC),
    )

    assert grant.method == "PUT"
    assert grant.url.startswith(
        "http://localhost:9000/talaqi-local/media/018f0000-0000-7000-8000-000000000101/"
    )
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in grant.url
    assert "X-Amz-Expires=600" in grant.url
    assert "X-Amz-Signature=" in grant.url
    assert "do-not-disclose" not in grant.url
    assert grant.headers == {
        "Content-Type": "image/png",
        "X-Amz-Meta-Declared-Size": "128",
    }


def test_s3_grant_caps_expiry_to_configured_window() -> None:
    adapter = S3MediaStorage(
        endpoint="https://storage.example.com/base",
        bucket="media",
        access_key="access",
        secret_key="secret",  # pragma: allowlist secret
    )
    now = datetime(2026, 7, 28, 12, tzinfo=UTC)

    grant = adapter.create_upload_grant(
        asset_id=ASSET_ID,
        storage_key=KEY,
        content_type="image/png",
        byte_size=128,
        expires_at=now + timedelta(days=8),
        now=now,
    )

    assert "X-Amz-Expires=604800" in grant.url
