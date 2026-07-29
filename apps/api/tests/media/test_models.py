from __future__ import annotations

from uuid import UUID

import pytest
from talaqi.media.models import (
    MAX_UPLOAD_BYTES,
    MediaValidationError,
    build_storage_key,
    validate_upload_intent,
)

OWNER_ID = UUID("018f0000-0000-7000-8000-000000000101")
ASSET_ID = UUID("018f0000-0000-7000-8000-000000000102")


@pytest.mark.parametrize(
    "filename",
    [
        "../avatar.png",
        r"..\avatar.png",
        "folder/avatar.png",
        "folder\\avatar.png",
        ".",
        "..",
        "bad\x00name.png",
        "a" * 256,
    ],
)
def test_upload_intent_rejects_unsafe_filename(filename: str) -> None:
    with pytest.raises(MediaValidationError, match="invalid_media"):
        validate_upload_intent(filename, "image/png", 128)


@pytest.mark.parametrize(
    ("content_type", "byte_size"),
    [
        ("image/gif", 128),
        ("text/html", 128),
        ("image/png; charset=utf-8", 128),
        ("image/png", 0),
        ("image/png", MAX_UPLOAD_BYTES + 1),
        ("image/png", True),
    ],
)
def test_upload_intent_rejects_type_and_size_outside_contract(
    content_type: str, byte_size: int
) -> None:
    with pytest.raises(MediaValidationError):
        validate_upload_intent("avatar.png", content_type, byte_size)


def test_upload_intent_preserves_safe_display_filename() -> None:
    value = validate_upload_intent("  summer photo.PNG  ", "image/png", 128)

    assert value.original_filename == "summer photo.PNG"
    assert value.content_type == "image/png"
    assert value.byte_size == 128


def test_storage_key_uses_only_server_owned_identifiers() -> None:
    assert build_storage_key(OWNER_ID, ASSET_ID) == (
        "media/018f0000-0000-7000-8000-000000000101/018f0000-0000-7000-8000-000000000102/source"
    )
