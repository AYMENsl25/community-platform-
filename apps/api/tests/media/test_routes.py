from __future__ import annotations

import io
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from talaqi.db.identifiers import generate_uuid7
from talaqi.media.local_storage import LocalMediaStorage

from .conftest import app_for, create_user, media_settings


def png() -> bytes:
    target = io.BytesIO()
    Image.new("RGB", (8, 6), (10, 60, 120)).save(target, format="PNG")
    return target.getvalue()


def storage(root: Path) -> LocalMediaStorage:
    settings = media_settings()
    return LocalMediaStorage(
        root,
        api_public_url=str(settings.api_public_url),
        signing_secret=settings.session_secret.get_secret_value().encode("utf-8"),
    )


@pytest.mark.asyncio
async def test_create_put_complete_is_private_idempotent_and_canonical(
    media_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    owner = await create_user(media_engine)
    source = png()
    app = app_for(media_engine, storage(tmp_path))
    create_key = f"media-create-{generate_uuid7()}"
    complete_key = f"media-complete-{generate_uuid7()}"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        created = await client.post(
            "/api/v1/media/uploads",
            json={
                "original_filename": "cover.png",
                "content_type": "image/png",
                "byte_size": len(source),
            },
            headers=owner.headers(idempotency_key=create_key),
        )
        replay = await client.post(
            "/api/v1/media/uploads",
            json={
                "original_filename": "cover.png",
                "content_type": "image/png",
                "byte_size": len(source),
            },
            headers=owner.headers(idempotency_key=create_key),
        )
        upload = await client.put(
            created.json()["upload"]["url"],
            content=source,
            headers=created.json()["upload"]["headers"],
        )
        completed = await client.post(
            f"/api/v1/media/uploads/{created.json()['id']}/complete",
            headers=owner.headers(idempotency_key=complete_key),
        )
        completed_replay = await client.post(
            f"/api/v1/media/uploads/{created.json()['id']}/complete",
            headers=owner.headers(idempotency_key=complete_key),
        )

    assert created.status_code == replay.status_code == 201
    assert {key: value for key, value in created.json().items() if key != "upload"} == {
        key: value for key, value in replay.json().items() if key != "upload"
    }
    assert created.headers["cache-control"] == "private, no-store"
    assert upload.status_code == 204
    assert completed.status_code == completed_replay.status_code == 200
    assert completed.json() == completed_replay.json()
    assert completed.json()["status"] == "verified"
    assert completed.json()["content_type"] == "image/webp"
    assert completed.json()["width"] == 8
    assert completed.json()["height"] == 6
    async with media_engine.connect() as connection:
        row = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT status::text, storage_key, content_type, width, height,
                               octet_length(sha256) AS hash_size
                        FROM talaqi.media_assets WHERE id = :id
                        """
                    ),
                    {"id": UUID(created.json()["id"])},
                )
            )
            .mappings()
            .one()
        )
        idempotency_body = (
            (
                await connection.execute(
                    text(
                        """
                        SELECT response_body::text
                        FROM talaqi.idempotency_keys
                        WHERE user_id = :user_id AND key = :key
                        """
                    ),
                    {"user_id": owner.user_id, "key": create_key},
                )
            )
            .scalars()
            .one()
        )
    assert row["status"] == "verified"
    assert row["storage_key"].endswith("/canonical.webp")
    assert row["content_type"] == "image/webp"
    assert row["hash_size"] == 32

    assert "upload" not in idempotency_body
    assert "X-Talaqi-Upload-Token" not in idempotency_body


@pytest.mark.asyncio
async def test_media_routes_enforce_verification_csrf_owner_and_safe_failures(
    media_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    owner = await create_user(media_engine)
    outsider = await create_user(media_engine)
    unverified = await create_user(media_engine, verified=False)
    source = png()
    app = app_for(media_engine, storage(tmp_path))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        no_csrf = await client.post(
            "/api/v1/media/uploads",
            json={
                "original_filename": "cover.png",
                "content_type": "image/png",
                "byte_size": len(source),
            },
            headers={
                "cookie": owner.cookie,
                "Idempotency-Key": f"media-create-{generate_uuid7()}",
            },
        )
        blocked = await client.post(
            "/api/v1/media/uploads",
            json={
                "original_filename": "cover.png",
                "content_type": "image/png",
                "byte_size": len(source),
            },
            headers=unverified.headers(idempotency_key=f"media-create-{generate_uuid7()}"),
        )
        created = await client.post(
            "/api/v1/media/uploads",
            json={
                "original_filename": "cover.png",
                "content_type": "image/png",
                "byte_size": len(source),
            },
            headers=owner.headers(idempotency_key=f"media-create-{generate_uuid7()}"),
        )
        foreign = await client.post(
            f"/api/v1/media/uploads/{created.json()['id']}/complete",
            headers=outsider.headers(idempotency_key=f"media-complete-{generate_uuid7()}"),
        )
        tampered = await client.put(
            created.json()["upload"]["url"],
            content=b"x" * len(source),
            headers={
                **created.json()["upload"]["headers"],
                "Content-Type": "image/jpeg",
            },
        )

    assert no_csrf.status_code == 403
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "email_verification_required"
    assert foreign.status_code == 404
    assert tampered.status_code == 404
    assert "storage_key" not in created.text
