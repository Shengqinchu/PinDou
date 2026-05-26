from __future__ import annotations

import io
import time
from pathlib import Path

from PIL import Image, ImageDraw

from pindou.pattern.builder import NoBead, PatternBuilder
from pindou.pattern.exporter import PatternExporter, labeled_grid_filename
from pindou.pattern.postprocess import detect_and_remove_white_bg
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
        sheet = builder.build(SizePreset.DOUBLE_BOARD_52X52, raw_image=read_input(filename), mode="script")

        assert_grid_size(sheet, width=52, height=52)
        assert sheet.bead_total == 52 * 52
        assert 1 <= len(sheet.palette_used) <= 24
        assert set(sheet.color_counts) == {color.code for color in sheet.palette_used}
        assert len(sheet.coords) == sheet.bead_total
        assert not any(any(row) for row in sheet.no_bead_mask)
        assert sheet.estimated_cost_cny >= 0


def test_preview_alpha_path_marks_transparent_cells_as_no_bead() -> None:
    builder = PatternBuilder(target_colors=8)
    preview = transparent_preview_bytes()

    sheet = builder.build(SizePreset.DOUBLE_BOARD_52X52, preview=preview, mode="ai")

    assert_grid_size(sheet, width=52, height=52)
    no_bead_count = sum(sum(row) for row in sheet.no_bead_mask)
    assert no_bead_count > 0
    assert sheet.bead_total + no_bead_count == 52 * 52
    assert any(isinstance(cell, NoBead) for row in sheet.grid for cell in row)
    assert any(cell is None for row in sheet.to_frontend_dict()["grid"] for cell in row)


def test_custom_size_builds_and_reports_board_alignment_warning() -> None:
    builder = PatternBuilder(target_colors=8)
    sheet = builder.build("45x30", raw_image=read_input("cartoon_synthetic.png"), mode="script")
    frontend = sheet.to_frontend_dict()

    assert_grid_size(sheet, width=45, height=30)
    assert sheet.metadata["board_aligned"] is False
    assert "不对齐" in sheet.metadata["warning"]
    assert frontend["metadata"]["warning"] == sheet.metadata["warning"]


def test_white_bg_detect_success() -> None:
    builder = PatternBuilder(target_colors=8)
    raw = white_bg_raw_image_bytes()

    sheet = builder.build(
        SizePreset.DOUBLE_BOARD_52X52,
        raw_image=raw,
        mode="script",
        auto_remove_white_bg=True,
    )

    no_bead_count = sum(sum(row) for row in sheet.no_bead_mask)
    assert sheet.metadata["white_bg_detected"] is True
    assert no_bead_count > 52 * 52 * 0.3
    assert sheet.bead_total + no_bead_count == 52 * 52


def test_white_bg_detect_skip() -> None:
    image = Image.new("RGB", (40, 40), (90, 130, 180))
    draw = ImageDraw.Draw(image)
    draw.rectangle([12, 12, 28, 28], fill=(240, 240, 240))
    processed, detected = detect_and_remove_white_bg(image)

    builder = PatternBuilder(target_colors=8)
    sheet = builder.build(
        SizePreset.DOUBLE_BOARD_52X52,
        raw_image=image_bytes(image),
        mode="script",
        auto_remove_white_bg=True,
    )

    assert detected is False
    assert list(processed.getdata()) == list(image.getdata())
    assert sheet.metadata["white_bg_detected"] is False
    assert not any(any(row) for row in sheet.no_bead_mask)


def test_white_bg_detect_threshold_boundary() -> None:
    near_white = Image.new("RGB", (20, 20), (218, 218, 218))
    just_over = Image.new("RGB", (20, 20), (217, 217, 217))

    processed_near, detected_near = detect_and_remove_white_bg(near_white)
    processed_over, detected_over = detect_and_remove_white_bg(just_over)

    assert detected_near is True
    assert processed_near.convert("RGBA").getpixel((0, 0))[3] == 0
    assert detected_over is False
    assert list(processed_over.getdata()) == list(just_over.getdata())


def test_large_pattern_build_stays_under_two_seconds_after_warmup() -> None:
    builder = PatternBuilder()
    raw = read_input("cartoon_synthetic.png")
    builder.build(SizePreset.FOUR_BOARD_104X104, raw_image=raw, mode="script")

    started = time.perf_counter()
    sheet = builder.build(SizePreset.FOUR_BOARD_104X104, raw_image=raw, mode="script")
    elapsed = time.perf_counter() - started

    assert_grid_size(sheet, width=104, height=104)
    assert elapsed < 2.0


def test_labeled_grid_exporter_adds_readable_png_overlay() -> None:
    builder = PatternBuilder(target_colors=8)
    sheet = builder.build(SizePreset.SINGLE_BOARD_26X26, raw_image=read_input("pet_synthetic.png"), mode="script")

    png = PatternExporter().to_labeled_grid_png(sheet)
    image = Image.open(io.BytesIO(png))

    assert image.format == "PNG"
    assert image.width >= 26 * 24
    assert image.height > 26 * 24
    assert labeled_grid_filename("art_123") == "pattern_art_123_with_grid.png"


def white_bg_raw_image_bytes() -> bytes:
    image = Image.new("RGB", (90, 90), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse([20, 14, 70, 64], fill=(255, 180, 120), outline=(25, 25, 25), width=4)
    draw.rectangle([32, 58, 58, 86], fill=(80, 120, 220), outline=(25, 25, 25), width=4)
    return image_bytes(image)


def transparent_preview_bytes() -> bytes:
    image = Image.new("RGBA", (80, 80), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse([16, 12, 64, 62], fill=(255, 180, 120, 255), outline=(30, 30, 30, 255), width=4)
    draw.rectangle([28, 55, 52, 76], fill=(60, 120, 220, 255), outline=(30, 30, 30, 255), width=3)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def image_bytes(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
