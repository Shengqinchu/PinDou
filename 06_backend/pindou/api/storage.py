"""Storage helpers for uploads, previews, and pattern JSON files."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from pindou.api.errors import ApiException, ErrorCode
from pindou.config import get_settings


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def ensure_storage_dirs() -> None:
    settings = get_settings()
    for directory in (settings.upload_dir, settings.preview_dir, settings.pattern_dir, settings.thumbnail_dir):
        directory.mkdir(parents=True, exist_ok=True)


def save_uploaded_image(filename: str, data: bytes) -> dict[str, str]:
    image, extension = validate_uploaded_image(filename, data)
    image_id = uuid.uuid4().hex
    output_format = _format_for_extension(extension)
    path = get_settings().upload_dir / f"{image_id}{extension}"
    if output_format == "JPEG":
        image = image.convert("RGB")
    image.save(path, format=output_format)
    return {"image_id": image_id, "path": str(path), "image_url": static_url("uploads", path.name)}


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
    path = get_settings().preview_dir / f"{preview_id}.png"
    path.write_bytes(data)
    return path, static_url("previews", path.name)


def save_pattern_json(pattern_id: str, pattern_data: dict[str, Any]) -> tuple[Path, str]:
    path = get_settings().pattern_dir / f"{pattern_id}.json"
    path.write_text(json.dumps(pattern_data, ensure_ascii=False), encoding="utf-8")
    return path, static_url("patterns", path.name)


def save_pattern_png(filename: str, data: bytes) -> tuple[Path, str]:
    safe_name = Path(filename).name
    if not safe_name.lower().endswith(".png"):
        safe_name = f"{Path(safe_name).stem}.png"
    path = get_settings().pattern_dir / safe_name
    path.write_bytes(data)
    return path, static_url("patterns", path.name)


def load_uploaded_image(image_id: str) -> tuple[bytes, Path]:
    path = resolve_stored_file(get_settings().upload_dir, image_id, ALLOWED_EXTENSIONS)
    if path is None:
        raise ApiException(404, ErrorCode.IMAGE_NOT_FOUND, "没有找到这张上传图片，请重新上传。")
    return path.read_bytes(), path


def load_preview_image(preview_id: str) -> tuple[bytes, Path]:
    path = resolve_stored_file(get_settings().preview_dir, preview_id, {".png"})
    if path is None:
        raise ApiException(404, ErrorCode.IMAGE_NOT_FOUND, "没有找到这张预览图，请重新生成。")
    return path.read_bytes(), path


def resolve_stored_file(directory: Path, file_id: str, extensions: set[str]) -> Path | None:
    safe_id = Path(file_id).stem
    for extension in extensions:
        candidate = directory / f"{safe_id}{extension}"
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def static_url(kind: str, filename: str) -> str:
    return f"/static/{kind}/{filename}"


def _normalize_extension(extension: str) -> str:
    normalized = extension.lower()
    return ".jpg" if normalized == ".jpeg" else normalized


def _format_for_extension(extension: str) -> str:
    return {".jpg": "JPEG", ".png": "PNG", ".webp": "WEBP"}[extension]


def _bytes_path(data: bytes):
    import io

    return io.BytesIO(data)
