"""Artwork persistence service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from pindou.db.models import Artwork


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

    def delete_artwork(self, *, artwork_id: str, user_id: str | None = None) -> bool:
        artwork = self.get_artwork(artwork_id)
        if artwork is None:
            return False
        if user_id is not None and artwork.user_id != user_id:
            raise PermissionError("Artwork does not belong to the requested user.")

        delete_file_if_exists(artwork.original_path)
        self.session.delete(artwork)
        self.session.commit()
        return True


def delete_file_if_exists(path: str | None) -> bool:
    if not path:
        return False
    target = Path(path)
    if target.exists() and target.is_file():
        target.unlink()
        return True
    return False
