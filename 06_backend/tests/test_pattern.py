from __future__ import annotations

import io
import time
from pathlib import Path

from PIL import Image, ImageDraw

from pindou.pattern.builder import NoBead, PatternBuilder
from pindou.providers.base import SizePreset


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_INPUT_DIR = PROJECT_ROOT / "01_research" / "tech" / "test_inputs"


def read_input(name: str) -> bytes:
    return (TEST_INPUT_DIR / name).read_bytes()


def assert_grid_size(sheet, width: int, height: int) -> None:
    assert len(sheet.grid) == height
    assert all(len(row) == width for row in sheet.grid)
    assert len(sheet.no_bead_mask) == height
    assert all(len(row) == width for row in sheet.no_bead_mask)


def test_raw_image_path_builds_expected_grid_for_task_b_inputs() -> None:
    builder = PatternBuilder()

    for filename in ("portrait_synthetic.png", "pet_synthetic.png", "cartoon_synthetic.png"):
        sheet = builder.build(SizePreset.SMALL_60X80, raw_image=read_input(filename), mode="script")

        assert_grid_size(sheet, width=60, height=80)
        assert sheet.bead_total == 60 * 80
        assert 1 <= len(sheet.palette_used) <= 24
        assert set(sheet.color_counts) == {color.code for color in sheet.palette_used}
        assert len(sheet.coords) == sheet.bead_total
        assert not any(any(row) for row in sheet.no_bead_mask)
        assert sheet.estimated_cost_cny >= 0


def test_preview_alpha_path_marks_transparent_cells_as_no_bead() -> None:
    builder = PatternBuilder(target_colors=8)
    preview = transparent_preview_bytes()

    sheet = builder.build(SizePreset.SMALL_60X80, preview=preview, mode="ai")

    assert_grid_size(sheet, width=60, height=80)
    no_bead_count = sum(sum(row) for row in sheet.no_bead_mask)
    assert no_bead_count > 0
    assert sheet.bead_total + no_bead_count == 60 * 80
    assert any(isinstance(cell, NoBead) for row in sheet.grid for cell in row)
    assert any(cell is None for row in sheet.to_frontend_dict()["grid"] for cell in row)


def test_large_pattern_build_stays_under_two_seconds_after_warmup() -> None:
    builder = PatternBuilder()
    raw = read_input("cartoon_synthetic.png")
    builder.build(SizePreset.LARGE_100X120, raw_image=raw, mode="script")

    started = time.perf_counter()
    sheet = builder.build(SizePreset.LARGE_100X120, raw_image=raw, mode="script")
    elapsed = time.perf_counter() - started

    assert_grid_size(sheet, width=100, height=120)
    assert elapsed < 2.0


def transparent_preview_bytes() -> bytes:
    image = Image.new("RGBA", (80, 80), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse([16, 12, 64, 62], fill=(255, 180, 120, 255), outline=(30, 30, 30, 255), width=4)
    draw.rectangle([28, 55, 52, 76], fill=(60, 120, 220, 255), outline=(30, 30, 30, 255), width=3)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
