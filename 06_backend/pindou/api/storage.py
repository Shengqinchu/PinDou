"""Storage helpers for uploads, previews, and pattern JSON files."""

from __future__ import annotations

import json
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from pindou.api.errors import ApiException, ErrorCode
from pindou.services.storage_util import ensure_storage_dirs, get_storage_backend, static_url


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def save_uploaded_image(filename: str, data: bytes) -> dict[str, str]:
    image, extension = validate_uploaded_image(filename, data)
    image_id = uuid.uuid4().hex
    output_format = _format_for_extension(extension)
    key = f"uploads/{image_id}{extension}"
    if output_format == "JPEG":
        image = image.convert("RGB")
    output = BytesIO()
    image.save(output, format=output_format)
    get_storage_backend().upload(key, output.getvalue(), content_type=_content_type_for_extension(extension))
    return {
        "image_id": image_id,
        "path": key,
        "image_url": get_storage_backend().get_url(key),
    }


def normalized_upload_png_bytes(filename: str, data: bytes) -> bytes:
    image, _extension = validate_uploaded_image(filename, data)
    import io

    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def validate_uploaded_image(filename: str, data: bytes) -> tuple[Image.Image, str]:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiException(413, ErrorCode.INVALID_UPLOAD, "上传的照片太大了，请上传小于 10MB 的照片。")
    extension = _normalize_extension(Path(filename).suffix)
    if extension not in ALLOWED_EXTENSIONS:
        raise ApiException(400, ErrorCode.INVALID_UPLOAD, "不支持这种格式的照片，请上传 jpg、png 或 webp。")

    try:
        image = Image.open(_bytes_path(data))
        image = ImageOps.exif_transpose(image)
    except (UnidentifiedImageError, OSError) as exc:
        raise ApiException(400, ErrorCode.INVALID_UPLOAD, "照片无法读取，请换一张清晰图片再试。") from exc
    return image, extension


def save_preview_png(preview_id: str, data: bytes) -> tuple[Path, str]:
    key = f"previews/{preview_id}.png"
    get_storage_backend().upload(key, data, content_type="image/png")
    return Path(key), get_storage_backend().get_url(key)


def save_pattern_json(pattern_id: str, pattern_data: dict[str, Any]) -> tuple[Path, str]:
    key = f"patterns/{Path(pattern_id).stem}.json"
    get_storage_backend().upload(
        key,
        json.dumps(pattern_data, ensure_ascii=False).encode("utf-8"),
        content_type="application/json",
    )
    return Path(key), get_storage_backend().get_url(key)


def save_pattern_png(filename: str, data: bytes) -> tuple[Path, str]:
    safe_name = Path(filename).name
    if not safe_name.lower().endswith(".png"):
        safe_name = f"{Path(safe_name).stem}.png"
    key = f"patterns/{safe_name}"
    get_storage_backend().upload(key, data, content_type="image/png")
    return Path(key), get_storage_backend().get_url(key)


def load_uploaded_image(image_id: str) -> tuple[bytes, Path]:
    return load_stored_image("uploads", image_id, ALLOWED_EXTENSIONS, "没有找到这张上传图片，请重新上传。")


def load_preview_image(preview_id: str) -> tuple[bytes, Path]:
    return load_stored_image("previews", preview_id, {".png"}, "没有找到这张预览图，请重新生成。")


def load_stored_image(kind: str, file_id: str, extensions: set[str], message: str) -> tuple[bytes, Path]:
    safe_id = Path(file_id).stem
    backend = get_storage_backend()
    for extension in extensions:
        key = f"{kind}/{safe_id}{extension}"
        if backend.exists(key):
            return backend.download(key), Path(key)
    raise ApiException(404, ErrorCode.IMAGE_NOT_FOUND, message)


def _normalize_extension(extension: str) -> str:
    normalized = extension.lower()
    return ".jpg" if normalized == ".jpeg" else normalized


def _format_for_extension(extension: str) -> str:
    return {".jpg": "JPEG", ".png": "PNG", ".webp": "WEBP"}[extension]


def _content_type_for_extension(extension: str) -> str:
    return {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}[extension]


def _bytes_path(data: bytes):
    import io

    return io.BytesIO(data)
