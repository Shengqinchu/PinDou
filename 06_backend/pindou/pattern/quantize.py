"""Pattern quantization based on Phase 0 Task B implementation."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from PIL import Image

from pindou.pattern.builder import ColorRef
from pindou.pattern.quantize_core import (
    Palette,
    dither,
    merge_palette_indices_by_delta_e,
    nearest_indices,
    rgb_to_lab,
    select_palette_colors,
)
from pindou.providers.base import SizePreset


DEFAULT_TARGET_COLORS = 24
FLAT_IMAGE_TOP_N = 5
FLAT_IMAGE_COVERAGE_THRESHOLD = 0.90
FLAT_IMAGE_TARGET_COLORS = 5
FLAT_COLOR_BIN_SIZE = 16
PALETTE_MERGE_DELTA_E = 6.0
NEAR_WHITE_MIN_CHANNEL = 238
NEAR_WHITE_MAX_SPREAD = 24
NEAR_BLACK_MAX_CHANNEL = 38
FEATURE_MIN_PIXEL_RATIO = 0.002
FEATURE_MIN_PIXELS = 3
FEATURE_DARK_LUMINANCE = 64.0
FEATURE_SATURATION_SPREAD = 58
FEATURE_RED_DOMINANCE = 45
FEATURE_YELLOW_MIN_RED = 175
FEATURE_YELLOW_MIN_GREEN = 135
FEATURE_YELLOW_MAX_BLUE = 150


@dataclass(frozen=True)
class QuantizedGrid:
    codes: list[list[str | None]]
    selected_codes: list[str]
    runtime_ms: float
    effective_target_colors: int
    flat_image_detected: bool
    palette_merge_threshold_delta_e: float


def size_to_dimensions(size: SizePreset | str) -> tuple[int, int]:
    width_raw, height_raw = str(size.value if isinstance(size, SizePreset) else size).split("x", 1)
    return int(width_raw), int(height_raw)


def quantize_to_codes(
    image: Image.Image,
    palette: list[ColorRef] | tuple[ColorRef, ...],
    *,
    size: SizePreset,
    no_bead_mask: list[list[bool]] | None = None,
    target_colors: int = DEFAULT_TARGET_COLORS,
    metric: str = "ciede2000",
    dither_mode: str = "none",
    palette_merge_delta_e: float = PALETTE_MERGE_DELTA_E,
    snap_neutral_extremes: bool = False,
    preserve_feature_colors: bool = False,
) -> QuantizedGrid:
    if not palette:
        raise ValueError("Palette cannot be empty.")

    started = time.perf_counter()
    width, height = size_to_dimensions(size)
    rgb_image = image.convert("RGB")
    if rgb_image.size != (width, height):
        rgb_image = rgb_image.resize((width, height), Image.Resampling.LANCZOS)
    image_rgb = np.array(rgb_image, dtype=np.uint8)
    mask = np.array(no_bead_mask, dtype=bool) if no_bead_mask is not None else np.zeros((height, width), dtype=bool)
    if mask.shape != (height, width):
        raise ValueError(f"no_bead_mask shape {mask.shape} does not match target {(height, width)}.")
    if snap_neutral_extremes:
        image_rgb = snap_near_white_black(image_rgb, mask)

    algorithm_palette = make_algorithm_palette(palette)
    visible_pixels = image_rgb[~mask]
    if len(visible_pixels) == 0:
        return QuantizedGrid(
            codes=[[None for _ in range(width)] for _ in range(height)],
            selected_codes=[],
            runtime_ms=0.0,
            effective_target_colors=0,
            flat_image_detected=False,
            palette_merge_threshold_delta_e=palette_merge_delta_e,
        )

    effective_target_colors, flat_image_detected = choose_effective_target_colors(visible_pixels, target_colors)

    selected_indices = select_palette_colors(
        visible_pixels.reshape(-1, 1, 3),
        algorithm_palette,
        "kmeans",
        metric,
        n_colors=effective_target_colors,
    )
    protected_feature_indices: set[int] = set()
    if preserve_feature_colors:
        selected_indices, protected_feature_indices = add_feature_palette_indices(
            selected_indices,
            algorithm_palette,
            visible_pixels,
            metric=metric,
        )
    selected_indices = merge_palette_indices_by_delta_e(
        selected_indices,
        algorithm_palette,
        visible_pixels,
        threshold_delta_e=palette_merge_delta_e,
        metric=metric,
        protected_indices=protected_feature_indices,
    )
    selected_rgb = algorithm_palette.rgb[selected_indices]
    quantized_rgb = dither(image_rgb, selected_rgb, metric, dither_mode)
    selected_local_indices = nearest_indices(quantized_rgb, selected_rgb, "rgb").reshape((height, width))
    selected_codes = [algorithm_palette.codes[int(index)] for index in selected_indices]

    codes: list[list[str | None]] = []
    for y in range(height):
        row: list[str | None] = []
        for x in range(width):
            if mask[y, x]:
                row.append(None)
            else:
                row.append(selected_codes[int(selected_local_indices[y, x])])
        codes.append(row)

    return QuantizedGrid(
        codes=codes,
        selected_codes=list(dict.fromkeys(code for row in codes for code in row if code is not None)),
        runtime_ms=(time.perf_counter() - started) * 1000,
        effective_target_colors=effective_target_colors,
        flat_image_detected=flat_image_detected,
        palette_merge_threshold_delta_e=palette_merge_delta_e,
    )


def snap_near_white_black(image_rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Collapse clean-cartoon near-white and near-black pixels before palette selection."""

    arr = image_rgb.copy()
    visible = ~mask
    minimum = arr.min(axis=2)
    maximum = arr.max(axis=2)
    spread = maximum.astype(np.int16) - minimum.astype(np.int16)

    near_white = visible & (minimum >= NEAR_WHITE_MIN_CHANNEL) & (spread <= NEAR_WHITE_MAX_SPREAD)
    near_black = visible & (maximum <= NEAR_BLACK_MAX_CHANNEL)
    arr[near_white] = (255, 255, 255)
    arr[near_black] = (1, 1, 1)
    return arr


def add_feature_palette_indices(
    selected_indices: np.ndarray,
    palette: Palette,
    pixels_rgb: np.ndarray,
    *,
    metric: str,
) -> tuple[np.ndarray, set[int]]:
    """Guarantee tiny cartoon semantic colors are available before remapping."""

    pixels = pixels_rgb.reshape(-1, 3).astype(np.uint8)
    if len(pixels) == 0:
        return selected_indices, set()

    minimum = pixels.min(axis=1)
    maximum = pixels.max(axis=1)
    spread = maximum.astype(np.int16) - minimum.astype(np.int16)
    luma = (
        0.2126 * pixels[:, 0].astype(np.float64)
        + 0.7152 * pixels[:, 1].astype(np.float64)
        + 0.0722 * pixels[:, 2].astype(np.float64)
    )

    masks = [
        (minimum >= NEAR_WHITE_MIN_CHANNEL) & (spread <= NEAR_WHITE_MAX_SPREAD),
        maximum <= NEAR_BLACK_MAX_CHANNEL,
        luma <= FEATURE_DARK_LUMINANCE,
        (pixels[:, 0].astype(np.int16) - np.maximum(pixels[:, 1], pixels[:, 2]).astype(np.int16) >= FEATURE_RED_DOMINANCE)
        & (spread >= FEATURE_SATURATION_SPREAD),
        (pixels[:, 0] >= FEATURE_YELLOW_MIN_RED)
        & (pixels[:, 1] >= FEATURE_YELLOW_MIN_GREEN)
        & (pixels[:, 2] <= FEATURE_YELLOW_MAX_BLUE)
        & (spread >= FEATURE_SATURATION_SPREAD),
    ]
    min_pixels = max(FEATURE_MIN_PIXELS, int(round(len(pixels) * FEATURE_MIN_PIXEL_RATIO)))
    extra: list[int] = []
    for mask in masks:
        if int(mask.sum()) < min_pixels:
            continue
        representative = dominant_rgb(pixels[mask])
        extra.append(int(nearest_indices(representative.reshape(1, 3), palette.rgb, metric)[0]))
    if not extra:
        return selected_indices, set()
    protected = {int(index) for index in extra}
    return np.array(list(dict.fromkeys(selected_indices.tolist() + extra)), dtype=int), protected


def dominant_rgb(rgb: np.ndarray) -> np.ndarray:
    if len(rgb) == 0:
        return np.array([0, 0, 0], dtype=np.uint8)
    first_rgb = rgb[0]
    if np.all(rgb == first_rgb):
        return first_rgb.astype(np.uint8)
    bins = (rgb // FLAT_COLOR_BIN_SIZE).astype(np.uint16)
    packed = (bins[:, 0] << 10) | (bins[:, 1] << 5) | bins[:, 2]
    _unique_bins, inverse, counts = np.unique(packed, return_inverse=True, return_counts=True)
    best_bin = int(np.argmax(counts))
    members = rgb[inverse == best_bin].astype(np.float64)
    return np.rint(members.mean(axis=0)).astype(np.uint8)


def choose_effective_target_colors(pixels_rgb: np.ndarray, target_colors: int) -> tuple[int, bool]:
    if target_colors <= FLAT_IMAGE_TARGET_COLORS:
        return target_colors, False
    coverage = top_binned_color_coverage(pixels_rgb, top_n=FLAT_IMAGE_TOP_N, bin_size=FLAT_COLOR_BIN_SIZE)
    if coverage >= FLAT_IMAGE_COVERAGE_THRESHOLD:
        return min(target_colors, FLAT_IMAGE_TARGET_COLORS), True
    return target_colors, False


def top_binned_color_coverage(pixels_rgb: np.ndarray, *, top_n: int, bin_size: int) -> float:
    pixels = pixels_rgb.reshape(-1, 3)
    if len(pixels) == 0:
        return 0.0
    bins = (pixels.astype(np.uint16) // bin_size).astype(np.uint16)
    _unique, _inverse, counts = np.unique(bins, axis=0, return_inverse=True, return_counts=True)
    top_counts = np.sort(counts)[-top_n:]
    return float(top_counts.sum() / len(pixels))


def make_algorithm_palette(palette: list[ColorRef] | tuple[ColorRef, ...]) -> Palette:
    rgb = np.array([color.rgb for color in palette], dtype=np.float64)
    lab = rgb_to_lab(rgb.reshape(-1, 1, 3)).reshape(-1, 3)
    return Palette(
        codes=[color.code for color in palette],
        rgb=rgb,
        lab=lab,
    )
