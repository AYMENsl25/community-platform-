from __future__ import annotations

import hashlib
import io
import struct
import warnings
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from talaqi.media.models import (
    DEFAULT_MAX_IMAGE_PIXELS,
    MAX_IMAGE_DIMENSION,
    MAX_UPLOAD_BYTES,
    MediaValidationError,
)

_FORMAT_CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


@dataclass(frozen=True, slots=True)
class VerifiedImage:
    content: bytes
    content_type: str
    byte_size: int
    width: int
    height: int
    sha256: bytes


def _validate_complete_container(content: bytes, image_format: str) -> None:
    if image_format == "JPEG":
        if not content.startswith(b"\xff\xd8\xff") or not content.endswith(b"\xff\xd9"):
            raise MediaValidationError("invalid_media")
        return
    if image_format == "WEBP":
        if (
            len(content) < 12
            or content[:4] != b"RIFF"
            or content[8:12] != b"WEBP"
            or struct.unpack("<I", content[4:8])[0] + 8 != len(content)
        ):
            raise MediaValidationError("invalid_media")
        return
    if image_format == "PNG":
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise MediaValidationError("invalid_media")
        position = 8
        found_end = False
        while position + 12 <= len(content):
            length = struct.unpack(">I", content[position : position + 4])[0]
            end = position + 12 + length
            if end > len(content):
                raise MediaValidationError("invalid_media")
            chunk_type = content[position + 4 : position + 8]
            position = end
            if chunk_type == b"IEND":
                found_end = True
                break
        if not found_end or position != len(content):
            raise MediaValidationError("invalid_media")
        return
    raise MediaValidationError("invalid_media")


def _validate_dimensions(width: int, height: int, max_pixels: int) -> None:
    if (
        not 1 <= width <= MAX_IMAGE_DIMENSION
        or not 1 <= height <= MAX_IMAGE_DIMENSION
        or width * height > max_pixels
    ):
        raise MediaValidationError("media_dimensions_invalid")


def verify_and_canonicalize(
    content: bytes,
    declared_content_type: str,
    *,
    max_pixels: int = DEFAULT_MAX_IMAGE_PIXELS,
) -> VerifiedImage:
    if not content or len(content) > MAX_UPLOAD_BYTES:
        code = "media_too_large" if len(content) > MAX_UPLOAD_BYTES else "invalid_media"
        raise MediaValidationError(code)
    if type(max_pixels) is not int or max_pixels < 1:
        raise ValueError("maximum image pixels must be a positive integer")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as probe:
                image_format = probe.format
                if image_format not in _FORMAT_CONTENT_TYPES:
                    raise MediaValidationError("invalid_media")
                if _FORMAT_CONTENT_TYPES[image_format] != declared_content_type:
                    raise MediaValidationError("media_type_mismatch")
                _validate_complete_container(content, image_format)
                _validate_dimensions(probe.width, probe.height, max_pixels)
                if getattr(probe, "n_frames", 1) != 1:
                    raise MediaValidationError("invalid_media")
                probe.verify()

            with Image.open(io.BytesIO(content)) as decoded:
                decoded.load()
                oriented = ImageOps.exif_transpose(decoded)
                _validate_dimensions(oriented.width, oriented.height, max_pixels)
                if oriented.mode in {"RGBA", "LA"} or (
                    oriented.mode == "P" and "transparency" in oriented.info
                ):
                    canonical = oriented.convert("RGBA")
                else:
                    canonical = oriented.convert("RGB")
                target = io.BytesIO()
                canonical.save(
                    target,
                    format="WEBP",
                    lossless=True,
                    quality=100,
                    method=6,
                    exact=True,
                    exif=b"",
                    icc_profile=None,
                )
    except MediaValidationError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise MediaValidationError("media_dimensions_invalid") from None
    except (OSError, SyntaxError, UnidentifiedImageError, ValueError):
        raise MediaValidationError("invalid_media") from None

    canonical_content = target.getvalue()
    return VerifiedImage(
        content=canonical_content,
        content_type="image/webp",
        byte_size=len(canonical_content),
        width=canonical.width,
        height=canonical.height,
        sha256=hashlib.sha256(canonical_content).digest(),
    )


__all__ = ["VerifiedImage", "verify_and_canonicalize"]
