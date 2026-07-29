from __future__ import annotations

import io

import pytest
from talaqi.media.models import MediaValidationError
from talaqi.media.verifier import verify_and_canonicalize


def _image_bytes(
    *,
    image_format: str = "PNG",
    size: tuple[int, int] = (8, 6),
    exif: bytes = b"",
    icc_profile: bytes | None = None,
) -> bytes:
    pillow_image = pytest.importorskip("PIL.Image")
    image = pillow_image.new("RGB", size, (20, 100, 180))
    target = io.BytesIO()
    image.save(target, format=image_format, exif=exif, icc_profile=icc_profile)
    return target.getvalue()


@pytest.mark.parametrize(
    ("declared", "actual_format"),
    [
        ("image/png", "JPEG"),
        ("image/jpeg", "PNG"),
        ("image/webp", "PNG"),
    ],
)
def test_verifier_rejects_mime_signature_mismatch(declared: str, actual_format: str) -> None:
    with pytest.raises(MediaValidationError, match="media_type_mismatch"):
        verify_and_canonicalize(_image_bytes(image_format=actual_format), declared)


def test_verifier_returns_metadata_free_canonical_webp() -> None:
    pillow_image = pytest.importorskip("PIL.Image")
    exif = pillow_image.Exif()
    exif[0x010E] = "private description"
    source = _image_bytes(exif=exif.tobytes(), icc_profile=b"private-profile")

    verified = verify_and_canonicalize(source, "image/png")

    assert verified.content_type == "image/webp"
    assert verified.width == 8
    assert verified.height == 6
    assert len(verified.sha256) == 32
    assert verified.byte_size == len(verified.content)
    decoded = pillow_image.open(io.BytesIO(verified.content))
    assert decoded.format == "WEBP"
    assert decoded.n_frames == 1
    assert decoded.getexif() == {}
    assert "icc_profile" not in decoded.info
    assert "xmp" not in decoded.info


def test_verifier_rejects_malformed_and_oversized_dimensions() -> None:
    with pytest.raises(MediaValidationError, match="invalid_media"):
        verify_and_canonicalize(b"<html>not an image</html>", "image/png")

    with pytest.raises(MediaValidationError, match="media_dimensions_invalid"):
        verify_and_canonicalize(
            _image_bytes(size=(12_001, 1)),
            "image/png",
            max_pixels=20_000,
        )


def test_canonical_encoding_is_deterministic() -> None:
    source = _image_bytes()

    first = verify_and_canonicalize(source, "image/png")
    second = verify_and_canonicalize(source, "image/png")

    assert first.content == second.content
    assert first.sha256 == second.sha256


def test_verifier_rejects_image_with_polyglot_trailing_payload() -> None:
    with pytest.raises(MediaValidationError, match="invalid_media"):
        verify_and_canonicalize(_image_bytes() + b"<script>alert(1)</script>", "image/png")
