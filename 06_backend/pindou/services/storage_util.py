"""Storage path helpers shared by services and API routes."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

from pindou.config import get_settings


class StorageBackend(Protocol):
    def upload(self, path: str, content: bytes, *, content_type: str | None = None) -> None:
        ...

    def download(self, path: str) -> bytes:
        ...

    def delete(self, path: str) -> bool:
        ...

    def exists(self, path: str) -> bool:
        ...

    def get_url(self, path: str) -> str:
        ...


class LocalStorageBackend:
    def upload(self, path: str, content: bytes, *, content_type: str | None = None) -> None:
        _ = content_type
        target = local_path_for_key(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def download(self, path: str) -> bytes:
        return local_path_for_key(path).read_bytes()

    def delete(self, path: str) -> bool:
        target = local_path_for_key(path)
        if target.exists() and target.is_file():
            target.unlink()
            return True
        return False

    def exists(self, path: str) -> bool:
        target = local_path_for_key(path)
        return target.exists() and target.is_file()

    def get_url(self, path: str) -> str:
        kind, filename = split_storage_key(path)
        return static_url(kind, filename)


class TencentCosBackend:
    def __init__(self) -> None:
        settings = get_settings()
        if not (settings.cos_secret_id and settings.cos_secret_key and settings.cos_bucket and settings.cos_region):
            raise RuntimeError("COS storage requires COS_SECRET_ID, COS_SECRET_KEY, COS_BUCKET, and COS_REGION.")
        try:
            from qcloud_cos import CosConfig, CosS3Client
        except ImportError as exc:  # pragma: no cover - dependency only needed in COS mode.
            raise RuntimeError("cos-python-sdk-v5 is required when STORAGE_BACKEND=cos.") from exc
        config = CosConfig(
            Region=settings.cos_region,
            SecretId=settings.cos_secret_id.get_secret_value(),
            SecretKey=settings.cos_secret_key.get_secret_value(),
        )
        self.client = CosS3Client(config)
        self.bucket = settings.cos_bucket
        self.public_base_url = settings.cos_public_base_url.rstrip("/") if settings.cos_public_base_url else None

    def upload(self, path: str, content: bytes, *, content_type: str | None = None) -> None:
        kwargs = {"Bucket": self.bucket, "Key": normalize_storage_key(path), "Body": content}
        if content_type:
            kwargs["ContentType"] = content_type
        self.client.put_object(**kwargs)

    def download(self, path: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=normalize_storage_key(path))
        return response["Body"].get_raw_stream().read()

    def delete(self, path: str) -> bool:
        self.client.delete_object(Bucket=self.bucket, Key=normalize_storage_key(path))
        return True

    def exists(self, path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=normalize_storage_key(path))
        except Exception:  # noqa: BLE001 - COS SDK raises provider-specific exceptions.
            return False
        return True

    def get_url(self, path: str) -> str:
        key = normalize_storage_key(path)
        if self.public_base_url:
            return f"{self.public_base_url}/{key}"
        settings = get_settings()
        return f"https://{self.bucket}.cos.{settings.cos_region}.myqcloud.com/{key}"


def ensure_storage_dirs() -> None:
    settings = get_settings()
    for directory in (
        settings.data_dir,
        settings.upload_dir,
        settings.preview_dir,
        settings.pattern_dir,
        settings.thumbnail_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def static_url(kind: str, filename: str) -> str:
    return f"/static/{kind}/{filename}"


@lru_cache
def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend.lower() == "cos":
        return TencentCosBackend()
    return LocalStorageBackend()


def storage_url(path: str) -> str:
    return get_storage_backend().get_url(path)


def storage_key_from_url_or_path(value: str | Path | None) -> str | None:
    if not value:
        return None
    raw = str(value)
    for prefix in ("/static/uploads/", "/static/previews/", "/static/patterns/", "/static/thumbnails/"):
        if raw.startswith(prefix):
            kind = prefix.removeprefix("/static/").strip("/")
            return f"{kind}/{Path(raw).name}"
    normalized = normalize_storage_key(urlparse(raw).path if raw.startswith("http") else raw)
    if normalized.split("/", 1)[0] in {"uploads", "previews", "patterns", "thumbnails"}:
        return normalized
    return None


def normalize_storage_key(path: str) -> str:
    return path.replace("\\", "/").lstrip("/")


def split_storage_key(path: str) -> tuple[str, str]:
    key = normalize_storage_key(path)
    parts = key.split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Storage key must include kind/filename: {path}")
    return parts[0], parts[1]


def local_path_for_key(path: str) -> Path:
    kind, filename = split_storage_key(path)
    settings = get_settings()
    roots = {
        "uploads": settings.upload_dir,
        "previews": settings.preview_dir,
        "patterns": settings.pattern_dir,
        "thumbnails": settings.thumbnail_dir,
    }
    if kind not in roots:
        raise ValueError(f"Unknown storage kind: {kind}")
    return roots[kind] / Path(filename).name


def static_asset_path(url: str | None) -> Path | None:
    if not url:
        return None
    settings = get_settings()
    static_roots = {
        "/static/uploads/": settings.upload_dir,
        "/static/previews/": settings.preview_dir,
        "/static/patterns/": settings.pattern_dir,
        "/static/thumbnails/": settings.thumbnail_dir,
    }
    for prefix, directory in static_roots.items():
        if url.startswith(prefix):
            return directory / Path(url).name
    path = Path(url)
    return path if path.is_absolute() else None
