"""PatternBuilder contract from PRD v1.0 section 5.2."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image

from pindou.providers.base import SizePreset


DOMINANT_DOWNSAMPLE_BIN_SIZE = 8
DOMINANT_ALPHA_THRESHOLD = 128
LOW_GRID_FEATURE_MAX_DIMENSION = 32
LOW_GRID_DARK_LUMINANCE_THRESHOLD = 72
LOW_GRID_DARK_PIXEL_RATIO = 0.09
LOW_GRID_SATURATED_PIXEL_RATIO = 0.06
LOW_GRID_MIN_FEATURE_PIXELS = 2
SATURATED_COLOR_SPREAD_THRESHOLD = 70
SATURATED_RED_DOMINANCE_THRESHOLD = 42
SUBJECT_ALIGNMENT_ALPHA_THRESHOLD = 128
SUBJECT_ALIGNMENT_MIN_PIXELS = 4
SUBJECT_ALIGNMENT_MAX_FOREGROUND_RATIO = 0.98
SUBJECT_ALIGNMENT_EPSILON = 0.02


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
class SubjectGridAlignment:
    applied: bool
    shift_x: float = 0.0
    shift_y: float = 0.0
    target_center_x: float | None = None
    target_center_y: float | None = None
    subject_center_x: float | None = None
    subject_center_y: float | None = None
    bbox: tuple[int, int, int, int] | None = None

    def to_metadata(self) -> dict[str, Any]:
        return {
            "applied": self.applied,
            "shift_x": round(self.shift_x, 3),
            "shift_y": round(self.shift_y, 3),
            "target_center": rounded_pair(self.target_center_x, self.target_center_y),
            "subject_center": rounded_pair(self.subject_center_x, self.subject_center_y),
            "bbox": list(self.bbox) if self.bbox is not None else None,
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
        from pindou.pattern.postprocess import cleanup_shape_artifacts, reinforce_low_grid_outline
        from pindou.pattern.quantize import quantize_to_codes

        size = size if isinstance(size, SizePreset) else SizePreset(str(size))
        input_mode = resolve_mode(preview=preview, raw_image=raw_image, mode=mode)
        image_bytes = preview if input_mode == "ai" else raw_image
        if image_bytes is None:
            raise ValueError("PatternBuilder requires preview or raw_image bytes.")

        palette = list(load_palette(brand, bead_diameter_mm))
        prepared_image, no_bead_mask, white_bg_detected, subject_alignment = prepare_input_image(
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
        shape_cleanup = cleanup_shape_artifacts(
            quantized.codes,
            palette_by_code,
            min_component_size=max(self.min_component_size, 4),
        )
        processed_codes = shape_cleanup.codes
        low_grid_feature_priority = min(parse_size(size)) <= LOW_GRID_FEATURE_MAX_DIMENSION
        outline_reinforced = False
        if low_grid_feature_priority and quantized.flat_image_detected:
            processed_codes, outline_reinforced = reinforce_low_grid_outline(
                processed_codes,
                palette_by_code,
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
                "effective_target_colors": quantized.effective_target_colors,
                "flat_image_detected": quantized.flat_image_detected,
                "palette_merge_delta_e": quantized.palette_merge_threshold_delta_e,
                "quantize_runtime_ms": round(quantized.runtime_ms, 2),
                "white_bg_detected": white_bg_detected,
                "auto_remove_white_bg_requested": bool(auto_remove_white_bg and input_mode == "script"),
                "low_grid_feature_priority": low_grid_feature_priority,
                "low_grid_outline_reinforced": outline_reinforced,
                "subject_grid_alignment": subject_alignment.to_metadata(),
                "shape_cleanup": shape_cleanup.to_metadata(),
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
) -> tuple[Image.Image, list[list[bool]], bool, SubjectGridAlignment]:
    from pindou.pattern.postprocess import detect_and_remove_white_bg

    source = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    width, height = parse_size(size)
    white_bg_detected = False
    if input_mode == "script" and auto_remove_white_bg:
        source, white_bg_detected = detect_and_remove_white_bg(source)
        source = source.convert("RGBA")
    background_alpha = 0 if input_mode == "ai" or white_bg_detected else 255
    background = (255, 255, 255, background_alpha)
    fitted, subject_alignment = fit_to_canvas_with_alignment(
        source,
        width,
        height,
        background,
        preserve_features=min(width, height) <= LOW_GRID_FEATURE_MAX_DIMENSION,
    )
    alpha = np.array(fitted.getchannel("A"), dtype=np.uint8)
    if input_mode == "ai" or white_bg_detected:
        no_bead_mask = (alpha < 128).tolist()
    else:
        no_bead_mask = [[False for _ in range(width)] for _ in range(height)]
    return fitted, no_bead_mask, white_bg_detected, subject_alignment


def fit_to_canvas(
    image: Image.Image,
    width: int,
    height: int,
    background: tuple[int, int, int, int],
    *,
    preserve_features: bool = False,
    align_subject_to_grid: bool = True,
) -> Image.Image:
    image, _alignment = fit_to_canvas_with_alignment(
        image,
        width,
        height,
        background,
        preserve_features=preserve_features,
        align_subject_to_grid=align_subject_to_grid,
    )
    return image


def fit_to_canvas_with_alignment(
    image: Image.Image,
    width: int,
    height: int,
    background: tuple[int, int, int, int],
    *,
    preserve_features: bool = False,
    align_subject_to_grid: bool = True,
) -> tuple[Image.Image, SubjectGridAlignment]:
    source = image.convert("RGBA")
    source_arr = np.array(source, dtype=np.uint8)
    source_height, source_width = source_arr.shape[:2]
    if source_width == 0 or source_height == 0:
        return Image.new("RGBA", (width, height), background), SubjectGridAlignment(applied=False)

    scale = min(width / source_width, height / source_height, 1.0)
    fitted_width = max(1, min(width, int(round(source_width * scale))))
    fitted_height = max(1, min(height, int(round(source_height * scale))))
    offset_x = (width - fitted_width) // 2
    offset_y = (height - fitted_height) // 2
    scale_x = fitted_width / source_width
    scale_y = fitted_height / source_height
    subject_alignment = compute_subject_grid_alignment(
        source_arr,
        width=width,
        height=height,
        offset_x=offset_x,
        offset_y=offset_y,
        scale_x=scale_x,
        scale_y=scale_y,
        enabled=align_subject_to_grid,
    )
    canvas = np.zeros((height, width, 4), dtype=np.uint8)
    canvas[:, :] = np.array(background, dtype=np.uint8)

    for y in range(height):
        src_y0_raw = (y - offset_y - subject_alignment.shift_y) / scale_y
        src_y1_raw = (y + 1 - offset_y - subject_alignment.shift_y) / scale_y
        src_y0 = max(0, int(np.floor(src_y0_raw)))
        src_y1 = min(source_height, int(np.ceil(src_y1_raw)))
        for x in range(width):
            src_x0_raw = (x - offset_x - subject_alignment.shift_x) / scale_x
            src_x1_raw = (x + 1 - offset_x - subject_alignment.shift_x) / scale_x
            src_x0 = max(0, int(np.floor(src_x0_raw)))
            src_x1 = min(source_width, int(np.ceil(src_x1_raw)))
            if src_y1 <= src_y0 or src_x1 <= src_x0:
                continue
            region = source_arr[src_y0:src_y1, src_x0:src_x1]
            if preserve_features:
                canvas[y, x] = feature_priority_region_rgba(region, background)
            else:
                canvas[y, x] = dominant_region_rgba(region, background)

    return Image.fromarray(canvas), subject_alignment


def compute_subject_grid_alignment(
    source_arr: np.ndarray,
    *,
    width: int,
    height: int,
    offset_x: int,
    offset_y: int,
    scale_x: float,
    scale_y: float,
    enabled: bool,
) -> SubjectGridAlignment:
    if not enabled:
        return SubjectGridAlignment(applied=False)

    foreground = subject_foreground_mask(source_arr)
    if foreground is None:
        return SubjectGridAlignment(applied=False)

    ys, xs = np.nonzero(foreground)
    min_x = int(xs.min())
    max_x = int(xs.max()) + 1
    min_y = int(ys.min())
    max_y = int(ys.max()) + 1
    bbox_center_x = (min_x + max_x) / 2
    bbox_center_y = (min_y + max_y) / 2

    target_center_x = float(round(width / 2))
    target_center_y = height / 2
    subject_canvas_x = offset_x + bbox_center_x * scale_x
    subject_canvas_y = offset_y + bbox_center_y * scale_y
    raw_shift_x = target_center_x - subject_canvas_x
    raw_shift_y = target_center_y - subject_canvas_y

    bbox_canvas_min_x = offset_x + min_x * scale_x
    bbox_canvas_max_x = offset_x + max_x * scale_x
    bbox_canvas_min_y = offset_y + min_y * scale_y
    bbox_canvas_max_y = offset_y + max_y * scale_y
    shift_x = clamp(raw_shift_x, -bbox_canvas_min_x, width - bbox_canvas_max_x)
    shift_y = clamp(raw_shift_y, -bbox_canvas_min_y, height - bbox_canvas_max_y)
    applied = abs(shift_x) >= SUBJECT_ALIGNMENT_EPSILON or abs(shift_y) >= SUBJECT_ALIGNMENT_EPSILON

    return SubjectGridAlignment(
        applied=applied,
        shift_x=shift_x,
        shift_y=shift_y,
        target_center_x=target_center_x,
        target_center_y=target_center_y,
        subject_center_x=subject_canvas_x,
        subject_center_y=subject_canvas_y,
        bbox=(min_x, min_y, max_x, max_y),
    )


def subject_foreground_mask(source_arr: np.ndarray) -> np.ndarray | None:
    alpha = source_arr[:, :, 3]
    foreground = alpha >= SUBJECT_ALIGNMENT_ALPHA_THRESHOLD
    foreground_count = int(foreground.sum())
    if foreground_count < SUBJECT_ALIGNMENT_MIN_PIXELS:
        return None
    foreground_ratio = foreground_count / foreground.size
    if foreground_ratio >= SUBJECT_ALIGNMENT_MAX_FOREGROUND_RATIO:
        return None
    return foreground


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def rounded_pair(x: float | None, y: float | None) -> list[float] | None:
    if x is None or y is None:
        return None
    return [round(x, 3), round(y, 3)]


def feature_priority_region_rgba(region: np.ndarray, background: tuple[int, int, int, int]) -> np.ndarray:
    foreground = region[region[:, :, 3] >= DOMINANT_ALPHA_THRESHOLD]
    if len(foreground) == 0:
        return np.array(background, dtype=np.uint8)

    rgb = foreground[:, :3]
    if len(rgb) < LOW_GRID_MIN_FEATURE_PIXELS:
        return dominant_region_rgba(region, background)

    luma = (
        0.2126 * rgb[:, 0].astype(np.float64)
        + 0.7152 * rgb[:, 1].astype(np.float64)
        + 0.0722 * rgb[:, 2].astype(np.float64)
    )
    dark_mask = luma <= LOW_GRID_DARK_LUMINANCE_THRESHOLD
    red_feature_mask = (
        (rgb[:, 0].astype(np.int16) - np.maximum(rgb[:, 1], rgb[:, 2]).astype(np.int16))
        >= SATURATED_RED_DOMINANCE_THRESHOLD
    )
    saturated_mask = (
        (rgb.max(axis=1).astype(np.int16) - rgb.min(axis=1).astype(np.int16))
        >= SATURATED_COLOR_SPREAD_THRESHOLD
    ) & red_feature_mask

    dark_count = int(dark_mask.sum())
    saturated_count = int(saturated_mask.sum())
    total = len(rgb)
    dark_ratio = dark_count / total
    saturated_ratio = saturated_count / total

    if saturated_count >= LOW_GRID_MIN_FEATURE_PIXELS and saturated_ratio >= LOW_GRID_SATURATED_PIXEL_RATIO:
        if dark_count < LOW_GRID_MIN_FEATURE_PIXELS or saturated_ratio * 1.35 >= dark_ratio:
            best_rgb = dominant_rgb(rgb[saturated_mask])
            return np.array([int(best_rgb[0]), int(best_rgb[1]), int(best_rgb[2]), 255], dtype=np.uint8)

    if dark_count >= LOW_GRID_MIN_FEATURE_PIXELS and dark_ratio >= LOW_GRID_DARK_PIXEL_RATIO:
        best_rgb = dominant_rgb(rgb[dark_mask])
        return np.array([int(best_rgb[0]), int(best_rgb[1]), int(best_rgb[2]), 255], dtype=np.uint8)

    return dominant_region_rgba(region, background)


def dominant_region_rgba(region: np.ndarray, background: tuple[int, int, int, int]) -> np.ndarray:
    foreground = region[region[:, :, 3] >= DOMINANT_ALPHA_THRESHOLD]
    if len(foreground) == 0:
        return np.array(background, dtype=np.uint8)
    rgb = foreground[:, :3]
    best_rgb = dominant_rgb(rgb)
    return np.array([int(best_rgb[0]), int(best_rgb[1]), int(best_rgb[2]), 255], dtype=np.uint8)


def dominant_rgb(rgb: np.ndarray) -> np.ndarray:
    first_rgb = rgb[0]
    if np.all(rgb == first_rgb):
        return first_rgb
    bins = (rgb // DOMINANT_DOWNSAMPLE_BIN_SIZE).astype(np.uint16)
    packed = (bins[:, 0] << 10) | (bins[:, 1] << 5) | bins[:, 2]
    _unique_bins, inverse, counts = np.unique(packed, return_inverse=True, return_counts=True)
    best_bin = int(np.argmax(counts))
    members = rgb[inverse == best_bin].astype(np.float64)
    return np.rint(members.mean(axis=0)).astype(np.uint8)


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
