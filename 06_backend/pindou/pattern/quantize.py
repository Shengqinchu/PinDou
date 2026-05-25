"""Pattern quantization based on Phase 0 Task B implementation."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from pindou.pattern.builder import ColorRef
from pindou.providers.base import SizePreset


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALGORITHM_IMPLS_DIR = PROJECT_ROOT / "01_research" / "tech" / "algorithm_impls"
if str(ALGORITHM_IMPLS_DIR) not in sys.path:
    sys.path.append(str(ALGORITHM_IMPLS_DIR))

from quantize_core import Palette, dither, nearest_indices, rgb_to_lab, select_palette_colors  # noqa: E402


DEFAULT_TARGET_COLORS = 24


@dataclass(frozen=True)
class QuantizedGrid:
    codes: list[list[str | None]]
    selected_codes: list[str]
    runtime_ms: float


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

    algorithm_palette = make_algorithm_palette(palette)
    visible_pixels = image_rgb[~mask]
    if len(visible_pixels) == 0:
        return QuantizedGrid(codes=[[None for _ in range(width)] for _ in range(height)], selected_codes=[], runtime_ms=0.0)

    selected_indices = select_palette_colors(
        visible_pixels.reshape(-1, 1, 3),
        algorithm_palette,
        "kmeans",
        metric,
        n_colors=target_colors,
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
    )


def make_algorithm_palette(palette: list[ColorRef] | tuple[ColorRef, ...]) -> Palette:
    rgb = np.array([color.rgb for color in palette], dtype=np.float64)
    lab = rgb_to_lab(rgb.reshape(-1, 1, 3)).reshape(-1, 3)
    return Palette(
        codes=[color.code for color in palette],
        rgb=rgb,
        lab=lab,
    )
