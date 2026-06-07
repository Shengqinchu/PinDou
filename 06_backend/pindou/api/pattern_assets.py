"""Helpers for persisted PatternSheet image assets."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from pindou.api.storage import save_pattern_json, save_pattern_png
from pindou.db.models import Artwork
from pindou.pattern.builder import PatternSheet
from pindou.pattern.exporter import PatternExporter, labeled_grid_filename


def attach_labeled_pattern_image(pattern_data: dict[str, Any], sheet: PatternSheet, artwork_id: str) -> str:
    """Persist the full labeled sheet PNG and expose it through metadata."""
    exporter = PatternExporter()
    _path, labeled_url = save_pattern_png(labeled_grid_filename(artwork_id), exporter.to_labeled_grid_png(sheet))
    metadata = pattern_data.setdefault("metadata", {})
    metadata["artwork_id"] = artwork_id
    metadata["labeled_image_url"] = labeled_url
    pattern_data["image_url"] = labeled_url
    return labeled_url


def finalize_artwork_pattern_assets(
    db: Session,
    *,
    artwork: Artwork,
    sheet: PatternSheet,
    pattern_data: dict[str, Any],
    preview_path: str | None = None,
) -> tuple[str, str]:
    """Attach generated image URLs to PatternSheet JSON and persist the final artwork row."""
    labeled_url = attach_labeled_pattern_image(pattern_data, sheet, artwork.artwork_id)
    _pattern_path, pattern_url = save_pattern_json(f"pattern_{artwork.artwork_id}", pattern_data)
    artwork.pattern_json = pattern_data
    artwork.preview_path = preview_path or labeled_url
    db.commit()
    return pattern_url, labeled_url
