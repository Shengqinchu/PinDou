"""Backfill artwork thumbnail URLs for existing Phase 2 artwork rows."""

from __future__ import annotations

from sqlalchemy import select

from pindou.db.models import Artwork
from pindou.db.session import SessionLocal, init_db
from pindou.services.artwork_service import ArtworkService


def main() -> None:
    init_db()
    with SessionLocal() as session:
        service = ArtworkService(session)
        artworks = list(session.scalars(select(Artwork).order_by(Artwork.created_at.desc())))
        created = 0
        for artwork in artworks:
            before = artwork.pattern_json.get("metadata", {}).get("thumbnail_url") if isinstance(artwork.pattern_json, dict) else None
            after = service.ensure_thumbnail(artwork)
            if after and after != before:
                created += 1
        print(f"Backfilled thumbnails: {created}/{len(artworks)}")


if __name__ == "__main__":
    main()
