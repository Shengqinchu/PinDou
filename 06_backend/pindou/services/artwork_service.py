"""Artwork persistence service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from pindou.api.storage import static_url
from pindou.config import get_settings
from pindou.db.models import Artwork

THUMBNAIL_SIZE = 200


class ArtworkService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_artwork(
        self,
        *,
        user_id: str,
        preview_path: str,
        pattern_json: dict[str, Any],
        style_preset: str,
        size_preset: str,
        original_path: str | None = None,
        title: str | None = None,
        tier: str = "basic",
        is_paid_unlocked: bool = False,
    ) -> Artwork:
        artwork = Artwork(
            user_id=user_id,
            original_path=original_path,
            preview_path=preview_path,
            pattern_json=pattern_json,
            style_preset=style_preset,
            size_preset=size_preset,
            title=title,
            tier=tier,
            is_paid_unlocked=is_paid_unlocked,
        )
        self.session.add(artwork)
        self.session.commit()
        self.session.refresh(artwork)
        return artwork

    def get_artwork(self, artwork_id: str) -> Artwork | None:
        return self.session.get(Artwork, artwork_id)

    def list_artworks(self, *, user_id: str) -> list[Artwork]:
        return list(
            self.session.scalars(
                select(Artwork).where(Artwork.user_id == user_id).order_by(Artwork.created_at.desc())
            )
        )

    def list_frontend_artworks(self, *, user_id: str, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        artworks = list(
            self.session.scalars(
                select(Artwork)
                .where(Artwork.user_id == user_id)
                .order_by(Artwork.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return [self.to_frontend_dict(artwork) for artwork in artworks]

    def to_frontend_dict(self, artwork: Artwork) -> dict[str, Any]:
        self.ensure_thumbnail(artwork)
        return artwork.to_frontend_dict()

    def ensure_thumbnail(self, artwork: Artwork) -> str | None:
        pattern_json = artwork.pattern_json if isinstance(artwork.pattern_json, dict) else {}
        metadata = pattern_json.setdefault("metadata", {})
        existing_url = metadata.get("thumbnail_url")
        existing_path = static_asset_path(existing_url) if existing_url else None
        if existing_url and existing_path is not None and existing_path.exists():
            return existing_url

        source_url = (
            metadata.get("labeled_image_url")
            or pattern_json.get("image_url")
            or artwork.preview_path
        )
        source_path = static_asset_path(source_url)
        if source_path is None or not source_path.exists():
            return existing_url or source_url

        settings = get_settings()
        settings.thumbnail_dir.mkdir(parents=True, exist_ok=True)
        output_path = settings.thumbnail_dir / f"thumb_{artwork.artwork_id}.png"
        try:
            create_square_thumbnail(source_path, output_path)
        except (OSError, UnidentifiedImageError):
            return existing_url or source_url

        thumbnail_url = static_url("thumbnails", output_path.name)
        metadata["thumbnail_url"] = thumbnail_url
        artwork.pattern_json = {**pattern_json, "metadata": dict(metadata)}
        self.session.add(artwork)
        self.session.commit()
        self.session.refresh(artwork)
        return thumbnail_url

    def delete_artwork(self, *, artwork_id: str, user_id: str | None = None) -> bool:
        artwork = self.get_artwork(artwork_id)
        if artwork is None:
            return False
        if user_id is not None and artwork.user_id != user_id:
            raise PermissionError("Artwork does not belong to the requested user.")

        delete_file_if_exists(artwork.original_path)
        metadata = artwork.pattern_json.get("metadata", {}) if isinstance(artwork.pattern_json, dict) else {}
        delete_file_if_exists(static_asset_path(metadata.get("thumbnail_url")))
        self.session.delete(artwork)
        self.session.commit()
        return True


def delete_file_if_exists(path: str | Path | None) -> bool:
    if not path:
        return False
    target = Path(path)
    if target.exists() and target.is_file():
        target.unlink()
        return True
    return False


def create_square_thumbnail(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert("RGBA")
        image.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (THUMBNAIL_SIZE, THUMBNAIL_SIZE), (255, 255, 255, 255))
        offset = ((THUMBNAIL_SIZE - image.width) // 2, (THUMBNAIL_SIZE - image.height) // 2)
        canvas.alpha_composite(image, offset)
        canvas.convert("RGB").save(destination, format="PNG", optimize=True)


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
