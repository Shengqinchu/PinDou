"""PatternBuilder contract from PRD v1.0 section 5.2."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image

from pindou.providers.base import SizePreset


@dataclass(frozen=True)
class NoBead:
    reason: str = "transparent"


@dataclass(frozen=True)
class ColorRef:
    brand: str
    code: str
    name_cn: str
    name_en: str | None
    hex: str
    rgb: tuple[int, int, int]
    bead_diameter_mm: float

    def to_frontend_dict(self) -> dict[str, Any]:
        return {
            "brand": self.brand,
            "code": self.code,
            "name_cn": self.name_cn,
            "name_en": self.name_en,
            "hex": self.hex,
            "rgb": self.rgb,
            "bead_diameter_mm": self.bead_diameter_mm,
        }


@dataclass(frozen=True)
class PatternSheet:
    grid: list[list[ColorRef | NoBead]]
    color_counts: dict[str, int]
    bead_total: int
    coords: list[tuple[int, int, str]]
    no_bead_mask: list[list[bool]]
    palette_used: list[ColorRef]
    estimated_cost_cny: float
    brand: str
    bead_diameter_mm: float
    suggested_buffer_pct: int = 10
    metadata: dict = field(default_factory=dict)

    def to_frontend_dict(self) -> dict[str, Any]:
        return {
            "grid": [
                [None if isinstance(cell, NoBead) else cell.to_frontend_dict() for cell in row]
                for row in self.grid
            ],
            "color_counts": self.color_counts,
            "bead_total": self.bead_total,
            "coords": self.coords,
            "no_bead_mask": self.no_bead_mask,
            "palette_used": [color.to_frontend_dict() for color in self.palette_used],
            "estimated_cost_cny": self.estimated_cost_cny,
            "suggested_buffer_pct": self.suggested_buffer_pct,
            "brand": self.brand,
            "bead_diameter_mm": self.bead_diameter_mm,
            "metadata": frontend_metadata(self.metadata),
        }


def pattern_sheet_from_frontend_dict(data: dict[str, Any]) -> PatternSheet:
    grid: list[list[ColorRef | NoBead]] = []
    palette_used = [color_ref_from_frontend_dict(item) for item in data.get("palette_used", [])]

    for row in data.get("grid", []):
        grid_row: list[ColorRef | NoBead] = []
        for cell in row:
            if cell is None:
                grid_row.append(NoBead())
            else:
                grid_row.append(color_ref_from_frontend_dict(cell))
        grid.append(grid_row)

    return PatternSheet(
        grid=grid,
        color_counts={str(key): int(value) for key, value in data.get("color_counts", {}).items()},
        bead_total=int(data.get("bead_total", 0)),
        coords=[tuple(coord) for coord in data.get("coords", [])],
        no_bead_mask=data.get("no_bead_mask", []),
        palette_used=palette_used,
        estimated_cost_cny=float(data.get("estimated_cost_cny", 0)),
        suggested_buffer_pct=int(data.get("suggested_buffer_pct", 10)),
        brand=str(data.get("brand", "MARD")),
        bead_diameter_mm=float(data.get("bead_diameter_mm", 5.0)),
        metadata=dict(data.get("metadata", {})),
    )


def color_ref_from_frontend_dict(data: dict[str, Any]) -> ColorRef:
    return ColorRef(
        brand=str(data.get("brand", "MARD")),
        code=str(data["code"]),
        name_cn=str(data.get("name_cn", data["code"])),
        name_en=data.get("name_en"),
        hex=str(data.get("hex", "#000000")),
        rgb=tuple(data.get("rgb", (0, 0, 0))),
        bead_diameter_mm=float(data.get("bead_diameter_mm", 5.0)),
    )


class PatternBuilder:
    def __init__(self, *, target_colors: int = 24, min_component_size: int = 3) -> None:
        self.target_colors = target_colors
        self.min_component_size = min_component_size

    def build(
        self,
        size: SizePreset,
        preview: bytes | None = None,
        raw_image: bytes | None = None,
        brand: str = "MARD",
        bead_diameter_mm: float = 5.0,
        mode: str = "auto",
        auto_remove_white_bg: bool = False,
    ) -> PatternSheet:
        from pindou.colormap.loader import estimate_cost_cny, load_palette
        from pindou.pattern.exporter import PatternExporter
        from pindou.pattern.postprocess import merge_small_components
        from pindou.pattern.quantize import quantize_to_codes

        size = size if isinstance(size, SizePreset) else SizePreset(str(size))
        input_mode = resolve_mode(preview=preview, raw_image=raw_image, mode=mode)
        image_bytes = preview if input_mode == "ai" else raw_image
        if image_bytes is None:
            raise ValueError("PatternBuilder requires preview or raw_image bytes.")

        palette = list(load_palette(brand, bead_diameter_mm))
        prepared_image, no_bead_mask, white_bg_detected = prepare_input_image(
            image_bytes,
            size,
            input_mode=input_mode,
            auto_remove_white_bg=auto_remove_white_bg,
        )
        quantized = quantize_to_codes(
            prepared_image,
            palette,
            size=size,
            no_bead_mask=no_bead_mask,
            target_colors=self.target_colors,
            metric="ciede2000",
            dither_mode="none",
        )
        palette_by_code = {color.code: color for color in palette}
        processed_codes = merge_small_components(
            quantized.codes,
            palette_by_code,
            min_component_size=self.min_component_size,
        )
        sheet = build_pattern_sheet(
            processed_codes,
            palette_by_code,
            brand=brand.upper(),
            bead_diameter_mm=bead_diameter_mm,
            estimated_cost_cny=estimate_cost_cny(color_counts(processed_codes), brand, bead_diameter_mm),
            metadata={
                "mode": input_mode,
                "size_preset": size.value,
                "warning": size.warning,
                "board_aligned": size.warning is None,
                "algorithm": "kmeans+ciede2000+none",
                "target_colors": self.target_colors,
                "quantize_runtime_ms": round(quantized.runtime_ms, 2),
                "white_bg_detected": white_bg_detected,
                "auto_remove_white_bg_requested": bool(auto_remove_white_bg and input_mode == "script"),
            },
        )
        preview_png = PatternExporter().to_simple_grid_png(sheet)
        sheet.metadata["preview_png"] = preview_png
        return sheet


def resolve_mode(*, preview: bytes | None, raw_image: bytes | None, mode: str) -> str:
    if preview is not None and raw_image is not None:
        raise ValueError("Provide exactly one of preview or raw_image.")
    if preview is None and raw_image is None:
        raise ValueError("Provide preview or raw_image.")
    normalized = mode.lower()
    if normalized in {"ai", "preview"}:
        if preview is None:
            raise ValueError("mode='ai' requires preview bytes.")
        return "ai"
    if normalized in {"script", "raw", "fallback_quantize"}:
        if raw_image is None:
            raise ValueError("mode='script' requires raw_image bytes.")
        return "script"
    if normalized == "auto":
        return "ai" if preview is not None else "script"
    raise ValueError(f"Unsupported PatternBuilder mode: {mode}")


def prepare_input_image(
    image_bytes: bytes,
    size: SizePreset,
    *,
    input_mode: str,
    auto_remove_white_bg: bool = False,
) -> tuple[Image.Image, list[list[bool]], bool]:
    from pindou.pattern.postprocess import detect_and_remove_white_bg

    source = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    width, height = parse_size(size)
    white_bg_detected = False
    if input_mode == "script" and auto_remove_white_bg:
        source, white_bg_detected = detect_and_remove_white_bg(source)
        source = source.convert("RGBA")
    background_alpha = 0 if input_mode == "ai" or white_bg_detected else 255
    background = (255, 255, 255, background_alpha)
    fitted = fit_to_canvas(source, width, height, background)
    alpha = np.array(fitted.getchannel("A"), dtype=np.uint8)
    if input_mode == "ai" or white_bg_detected:
        no_bead_mask = (alpha < 128).tolist()
    else:
        no_bead_mask = [[False for _ in range(width)] for _ in range(height)]
    return fitted, no_bead_mask, white_bg_detected


def fit_to_canvas(image: Image.Image, width: int, height: int, background: tuple[int, int, int, int]) -> Image.Image:
    fitted = image.copy()
    fitted.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (width, height), background)
    offset = ((width - fitted.width) // 2, (height - fitted.height) // 2)
    canvas.alpha_composite(fitted, dest=offset)
    return canvas


def parse_size(size: SizePreset) -> tuple[int, int]:
    width_raw, height_raw = size.value.split("x", 1)
    return int(width_raw), int(height_raw)


def color_counts(codes: list[list[str | None]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in codes:
        for code in row:
            if code is not None:
                counts[code] = counts.get(code, 0) + 1
    return counts


def frontend_metadata(metadata: dict) -> dict[str, Any]:
    return {
        key: value
        for key, value in metadata.items()
        if key != "preview_png" and not isinstance(value, bytes | bytearray | memoryview)
    }


def build_pattern_sheet(
    codes: list[list[str | None]],
    palette_by_code: dict[str, ColorRef],
    *,
    brand: str,
    bead_diameter_mm: float,
    estimated_cost_cny: float,
    metadata: dict,
) -> PatternSheet:
    grid: list[list[ColorRef | NoBead]] = []
    no_bead_mask: list[list[bool]] = []
    coords: list[tuple[int, int, str]] = []
    counts = color_counts(codes)
    used_codes = set(counts)

    for row_idx, row in enumerate(codes):
        grid_row: list[ColorRef | NoBead] = []
        mask_row: list[bool] = []
        for col_idx, code in enumerate(row):
            if code is None:
                grid_row.append(NoBead())
                mask_row.append(True)
                continue
            color = palette_by_code[code]
            grid_row.append(color)
            mask_row.append(False)
            coords.append((row_idx, col_idx, code))
        grid.append(grid_row)
        no_bead_mask.append(mask_row)

    palette_used = [color for code, color in palette_by_code.items() if code in used_codes]
    return PatternSheet(
        grid=grid,
        color_counts=counts,
        bead_total=sum(counts.values()),
        coords=coords,
        no_bead_mask=no_bead_mask,
        palette_used=palette_used,
        estimated_cost_cny=estimated_cost_cny,
        brand=brand,
        bead_diameter_mm=bead_diameter_mm,
        suggested_buffer_pct=10,
        metadata=metadata,
    )
