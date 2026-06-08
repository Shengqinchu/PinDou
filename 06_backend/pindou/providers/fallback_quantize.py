"""Script quantization fallback preview provider."""

from __future__ import annotations

import base64
import io
import time
from typing import Any

from PIL import Image

from pindou.pattern.builder import ColorRef, NoBead, PatternBuilder, PatternSheet
from pindou.providers.base import PreviewProvider, PreviewProviderError, PreviewResult, SizePreset, StylePreset


TRANSPARENT_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/"
    "l6j3NwAAAABJRU5ErkJggg=="
)


class FallbackProvider(PreviewProvider):
    """Call PatternBuilder on the raw image when AI preview providers fail."""

    name = "fallback_quantize"

    def __init__(self, pattern_builder: PatternBuilder | None = None) -> None:
        self.pattern_builder = pattern_builder or PatternBuilder()

    def generate(
        self,
        image: bytes,
        style_preset: StylePreset,
        size_preset: SizePreset,
        seed: int | None = None,
    ) -> PreviewResult:
        started = time.perf_counter()
        try:
            pattern = self.pattern_builder.build(
                size=size_preset,
                raw_image=image,
                mode="fallback_quantize",
                auto_remove_white_bg=should_auto_remove_white_bg(image),
            )
        except Exception as exc:  # noqa: BLE001 - provider boundary normalizes failures.
            raise PreviewProviderError(f"{self.name} failed: {exc}") from exc

        preview_png = self._render_pattern_preview(pattern)
        color_count = len(pattern.palette_used) or len(pattern.color_counts)
        return PreviewResult.from_image_bytes(
            preview_png,
            target_color_count=color_count,
            provider_used=self.name,
            fallback_count=0,
            cost_estimate=0.0,
            latency_ms=round((time.perf_counter() - started) * 1000),
            metadata={
                "style_preset": style_preset.value,
                "size_preset": size_preset.value,
                "bead_total": pattern.bead_total,
                "brand": pattern.brand,
                "bead_diameter_mm": pattern.bead_diameter_mm,
                "seed": seed,
            },
        )

    def _render_pattern_preview(self, pattern: PatternSheet) -> bytes:
        preview_png = pattern.metadata.get("preview_png") if pattern.metadata else None
        if isinstance(preview_png, bytes):
            return preview_png
        if isinstance(preview_png, str):
            return base64.b64decode(preview_png)
        return render_pattern_sheet(pattern)


def render_pattern_sheet(pattern: PatternSheet) -> bytes:
    grid = pattern.grid
    if not grid or not grid[0]:
        return TRANSPARENT_PNG

    height = len(grid)
    width = max(len(row) for row in grid)
    image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    pixels = image.load()
    for y, row in enumerate(grid):
        for x, bead in enumerate(row):
            color = bead_to_rgba(bead)
            pixels[x, y] = color

    scale = max(1, min(12, 1024 // max(width, height)))
    rendered = image.resize((width * scale, height * scale), Image.Resampling.NEAREST)
    output = io.BytesIO()
    rendered.save(output, format="PNG")
    return output.getvalue()


def should_auto_remove_white_bg(image: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(image)) as source:
            width, height = source.size
    except Exception:  # noqa: BLE001 - PatternBuilder will surface the real decode error.
        return True
    return width * height >= 64


def bead_to_rgba(bead: ColorRef | NoBead | Any) -> tuple[int, int, int, int]:
    if isinstance(bead, NoBead):
        return (255, 255, 255, 0)
    rgb = getattr(bead, "rgb", None)
    if isinstance(rgb, tuple | list) and len(rgb) >= 3:
        return (int(rgb[0]), int(rgb[1]), int(rgb[2]), 255)
    return (255, 255, 255, 0)
