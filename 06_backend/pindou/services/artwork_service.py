"""Artwork persistence service."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from pindou.db.models import Artwork
from pindou.services.ownership import belongs_to_owner
from pindou.services.storage_util import get_storage_backend, storage_key_from_url_or_path

THUMBNAIL_SIZE = 200


class ArtworkService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_artwork(
        self,
        *,
        user_id: str | None,
        owner_type: str | None = None,
        owner_id: str | None = None,
        preview_path: str,
        pattern_json: dict[str, Any],
        style_preset: str,
        size_preset: str,
        original_path: str | None = None,
        title: str | None = None,
        tier: str = "basic",
        is_paid_unlocked: bool = False,
    ) -> Artwork:
        normalized_owner_type = owner_type or ("user" if user_id else "")
        normalized_owner_id = owner_id or user_id
        if normalized_owner_type not in {"user", "device"} or not normalized_owner_id:
            raise ValueError("Artwork requires a user or device owner.")
        artwork = Artwork(
            user_id=user_id,
            owner_type=normalized_owner_type,
            owner_id=normalized_owner_id,
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
        self.session.flush()
        self.session.commit()
        return artwork

    def get_artwork(self, artwork_id: str) -> Artwork | None:
        return self.session.get(Artwork, artwork_id)

    def list_artworks(
        self,
        *,
        user_id: str | None = None,
        owner_type: str | None = None,
        owner_id: str | None = None,
    ) -> list[Artwork]:
        owner_type, owner_id = self._normalize_owner(user_id=user_id, owner_type=owner_type, owner_id=owner_id)
        return list(
            self.session.scalars(
                select(Artwork).where(self._owner_clause(owner_type=owner_type, owner_id=owner_id)).order_by(Artwork.created_at.desc())
            )
        )

    def list_frontend_artworks(
        self,
        *,
        user_id: str | None = None,
        owner_type: str | None = None,
        owner_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        owner_type, owner_id = self._normalize_owner(user_id=user_id, owner_type=owner_type, owner_id=owner_id)
        artworks = list(
            self.session.scalars(
                select(Artwork)
                .where(self._owner_clause(owner_type=owner_type, owner_id=owner_id))
                .order_by(Artwork.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return [self.to_frontend_dict(artwork) for artwork in artworks]

    def count_artworks(
        self,
        *,
        user_id: str | None = None,
        owner_type: str | None = None,
        owner_id: str | None = None,
    ) -> int:
        owner_type, owner_id = self._normalize_owner(user_id=user_id, owner_type=owner_type, owner_id=owner_id)
        total = self.session.scalar(
            select(func.count()).select_from(Artwork).where(self._owner_clause(owner_type=owner_type, owner_id=owner_id))
        )
        return int(total or 0)

    def list_gallery_artworks(
        self,
        *,
        user_id: str | None = None,
        owner_type: str | None = None,
        owner_id: str | None = None,
        limit: int = 12,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        owner_type, owner_id = self._normalize_owner(user_id=user_id, owner_type=owner_type, owner_id=owner_id)
        artworks = list(
            self.session.scalars(
                select(Artwork)
                .where(self._owner_clause(owner_type=owner_type, owner_id=owner_id))
                .order_by(Artwork.created_at.desc(), Artwork.artwork_id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return [self.to_gallery_dict(artwork) for artwork in artworks]

    def to_frontend_dict(self, artwork: Artwork) -> dict[str, Any]:
        self.ensure_thumbnail(artwork)
        return artwork.to_frontend_dict()

    def to_gallery_dict(self, artwork: Artwork) -> dict[str, Any]:
        pattern_json = artwork.pattern_json if isinstance(artwork.pattern_json, dict) else {}
        metadata = pattern_json.get("metadata", {}) if isinstance(pattern_json.get("metadata"), dict) else {}
        color_counts = pattern_json.get("color_counts", {})
        if not isinstance(color_counts, dict):
            color_counts = {}
        bead_total = _safe_int(pattern_json.get("bead_total"), default=sum(_safe_int(value) for value in color_counts.values()))
        color_count = len([value for value in color_counts.values() if _safe_int(value) > 0])
        if color_count == 0 and isinstance(pattern_json.get("palette_used"), list):
            color_count = len(pattern_json["palette_used"])
        thumbnail_url = self.ensure_thumbnail(artwork) or metadata.get("thumbnail_url") or artwork.preview_path

        return {
            "artwork_id": artwork.artwork_id,
            "title": artwork.title,
            "thumbnail_url": thumbnail_url,
            "preview_url": artwork.preview_url,
            "size_preset": artwork.size_preset,
            "bead_count": bead_total,
            "color_count": color_count,
            "style_preset": artwork.style_preset,
            "created_at": artwork.to_frontend_dict()["created_at"],
        }

    def ensure_thumbnail(self, artwork: Artwork) -> str | None:
        pattern_json = artwork.pattern_json if isinstance(artwork.pattern_json, dict) else {}
        metadata = pattern_json.setdefault("metadata", {})
        existing_url = metadata.get("thumbnail_url")
        backend = get_storage_backend()
        existing_key = storage_key_from_url_or_path(existing_url) if existing_url else None
        if existing_url and existing_key and backend.exists(existing_key):
            return existing_url

        source_url = (
            metadata.get("labeled_image_url")
            or pattern_json.get("image_url")
            or artwork.preview_path
        )
        source_key = storage_key_from_url_or_path(source_url)
        if source_key is None:
            return existing_url or source_url

        thumbnail_key = f"thumbnails/thumb_{artwork.artwork_id}.png"
        try:
            source_bytes = backend.download(source_key)
            thumbnail_bytes = create_square_thumbnail_bytes(source_bytes)
            backend.upload(thumbnail_key, thumbnail_bytes, content_type="image/png")
        except Exception:
            return existing_url or source_url

        thumbnail_url = backend.get_url(thumbnail_key)
        metadata = {**metadata, "thumbnail_url": thumbnail_url}
        artwork.pattern_json = {**pattern_json, "metadata": metadata}
        flag_modified(artwork, "pattern_json")
        self.session.add(artwork)
        self.session.commit()
        self.session.refresh(artwork)
        return thumbnail_url

    def delete_artwork(
        self,
        *,
        artwork_id: str,
        user_id: str | None = None,
        owner_type: str | None = None,
        owner_id: str | None = None,
    ) -> bool:
        artwork = self.get_artwork(artwork_id)
        if artwork is None:
            return False
        if owner_type is not None or owner_id is not None:
            owner_type, owner_id = self._normalize_owner(user_id=user_id, owner_type=owner_type, owner_id=owner_id)
            if not belongs_to_owner(artwork, owner_type=owner_type, owner_id=owner_id):
                raise PermissionError("Artwork does not belong to the requested owner.")
        elif user_id is not None and not belongs_to_owner(artwork, owner_type="user", owner_id=user_id):
            raise PermissionError("Artwork does not belong to the requested user.")

        delete_file_if_exists(artwork.original_path)
        metadata = artwork.pattern_json.get("metadata", {}) if isinstance(artwork.pattern_json, dict) else {}
        delete_file_if_exists(metadata.get("thumbnail_url"))
        self.session.delete(artwork)
        self.session.commit()
        return True

    @staticmethod
    def _normalize_owner(
        *,
        user_id: str | None = None,
        owner_type: str | None = None,
        owner_id: str | None = None,
    ) -> tuple[str, str]:
        normalized_owner_type = owner_type or ("user" if user_id else "")
        normalized_owner_id = owner_id or user_id or ""
        if normalized_owner_type not in {"user", "device"} or not normalized_owner_id:
            raise ValueError("A user or device owner is required.")
        return normalized_owner_type, normalized_owner_id

    @staticmethod
    def _owner_clause(*, owner_type: str, owner_id: str):
        if owner_type == "user":
            return or_(
                and_(Artwork.owner_type == "user", Artwork.owner_id == owner_id),
                and_(Artwork.user_id == owner_id, Artwork.owner_id.is_(None)),
                and_(Artwork.user_id == owner_id, Artwork.owner_id == ""),
            )
        return and_(Artwork.owner_type == owner_type, Artwork.owner_id == owner_id)


def delete_file_if_exists(path: str | Path | None) -> bool:
    if not path:
        return False
    storage_key = storage_key_from_url_or_path(path)
    if storage_key:
        return get_storage_backend().delete(storage_key)
    target = Path(path)
    if target.exists() and target.is_file():
        target.unlink()
        return True
    return False


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def create_square_thumbnail_bytes(source: bytes) -> bytes:
    with Image.open(BytesIO(source)) as image:
        image = ImageOps.exif_transpose(image).convert("RGBA")
        image.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (THUMBNAIL_SIZE, THUMBNAIL_SIZE), (255, 255, 255, 255))
        offset = ((THUMBNAIL_SIZE - image.width) // 2, (THUMBNAIL_SIZE - image.height) // 2)
        canvas.alpha_composite(image, offset)
        output = BytesIO()
        canvas.convert("RGB").save(output, format="PNG", optimize=True)
        return output.getvalue()


def create_square_thumbnail(source: Path, destination: Path) -> None:
    destination.write_bytes(create_square_thumbnail_bytes(source.read_bytes()))
