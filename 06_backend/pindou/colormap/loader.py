"""Color map loader for bead palettes."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pindou.pattern.builder import ColorRef


PROJECT_ROOT = Path(__file__).resolve().parents[3]
COLORMAP_DIR = PROJECT_ROOT / "01_research" / "colormap"


def palette_filename(brand: str, bead_diameter_mm: float) -> str:
    brand_slug = brand.strip().lower()
    diameter = float(bead_diameter_mm)
    if diameter.is_integer():
        diameter_slug = str(int(diameter))
    else:
        diameter_slug = str(diameter).replace(".", "_")
    return f"{brand_slug}_{diameter_slug}mm.json"


@lru_cache(maxsize=32)
def load_palette_rows(brand: str = "MARD", bead_diameter_mm: float = 5.0) -> tuple[dict[str, Any], ...]:
    path = COLORMAP_DIR / palette_filename(brand, float(bead_diameter_mm))
    if not path.exists() and brand.strip().lower() == "mard" and float(bead_diameter_mm) == 5.0:
        path = COLORMAP_DIR / "mard.json"
    if not path.exists():
        raise FileNotFoundError(f"Palette file not found for {brand} {bead_diameter_mm}mm: {path}")
    rows = json.loads(path.read_text(encoding="utf-8"))
    return tuple(rows)


@lru_cache(maxsize=32)
def _load_palette_cached(brand: str = "MARD", bead_diameter_mm: float = 5.0) -> tuple[ColorRef, ...]:
    return tuple(color_ref_from_row(row, brand, bead_diameter_mm) for row in load_palette_rows(brand, bead_diameter_mm))


def load_palette(brand: str = "MARD", bead_diameter_mm: float = 5.0) -> list[ColorRef]:
    return list(_load_palette_cached(brand, bead_diameter_mm))


def color_ref_from_row(row: dict[str, Any], default_brand: str, default_diameter: float) -> ColorRef:
    rgb = row.get("rgb") or (0, 0, 0)
    return ColorRef(
        brand=str(row.get("brand") or default_brand).upper(),
        code=str(row["code"]),
        name_cn=str(row.get("name_cn") or row.get("name_en") or row["code"]),
        name_en=str(row["name_en"]) if row.get("name_en") is not None else None,
        hex=str(row.get("hex") or "#000000"),
        rgb=(int(rgb[0]), int(rgb[1]), int(rgb[2])),
        bead_diameter_mm=float(row.get("bead_diameter_mm") or default_diameter),
    )


def estimate_cost_cny(color_counts: dict[str, int], brand: str = "MARD", bead_diameter_mm: float = 5.0) -> float:
    rows_by_code = {str(row["code"]): row for row in load_palette_rows(brand, bead_diameter_mm)}
    total = 0.0
    for code, count in color_counts.items():
        row = rows_by_code.get(code, {})
        price_per_1000 = row.get("price_per_1000pcs")
        if isinstance(price_per_1000, int | float):
            total += count * float(price_per_1000) / 1000
    return round(total, 2)
