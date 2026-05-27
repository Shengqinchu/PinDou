"""Storage path helpers shared by services and API routes."""

from __future__ import annotations

from pathlib import Path

from pindou.config import get_settings


def ensure_storage_dirs() -> None:
    settings = get_settings()
    for directory in (settings.upload_dir, settings.preview_dir, settings.pattern_dir, settings.thumbnail_dir):
        directory.mkdir(parents=True, exist_ok=True)


def static_url(kind: str, filename: str) -> str:
    return f"/static/{kind}/{filename}"


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
