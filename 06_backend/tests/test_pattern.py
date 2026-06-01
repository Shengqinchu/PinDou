from __future__ import annotations

import io
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from pindou.pattern.builder import NoBead, PatternBuilder, fit_to_canvas
from pindou.pattern.exporter import PatternExporter, fit_cell_code_font, labeled_grid_filename, partition_filename
from pindou.pattern.postprocess import detect_and_remove_white_bg
from pindou.pattern.quantize import choose_effective_target_colors
from pindou.pattern.quantize_core import Palette, merge_palette_indices_by_delta_e, rgb_to_lab
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
    just_over = Image.new("RGB", (20, 20), (160, 160, 160))

    processed_near, detected_near = detect_and_remove_white_bg(near_white)
    processed_over, detected_over = detect_and_remove_white_bg(just_over)

    assert detected_near is True
    assert processed_near.convert("RGBA").getpixel((0, 0))[3] == 0
    assert detected_over is False
    assert list(processed_over.getdata()) == list(just_over.getdata())


def test_white_bg_flood_fill_removes_only_edge_connected_background() -> None:
    image = Image.new("RGB", (80, 80), (252, 252, 248))
    draw = ImageDraw.Draw(image)
    draw.ellipse([18, 14, 62, 62], fill=(150, 124, 96), outline=(20, 20, 20), width=5)
    draw.ellipse([34, 30, 46, 42], fill=(255, 255, 255), outline=(20, 20, 20), width=2)

    processed, detected = detect_and_remove_white_bg(image)
    rgba = processed.convert("RGBA")

    assert detected is True
    assert rgba.getpixel((0, 0))[3] == 0
    assert rgba.getpixel((40, 36))[3] == 255


def test_dominant_downsample_does_not_invent_boundary_color() -> None:
    image = Image.new("RGBA", (40, 10), (160, 130, 100, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 21, 9], fill=(10, 10, 10, 255))

    fitted = fit_to_canvas(image, 4, 1, (255, 255, 255, 0))
    colors = [fitted.getpixel((x, 0))[:3] for x in range(4)]

    assert set(colors) <= {(10, 10, 10), (160, 130, 100)}
    assert colors[2] == (160, 130, 100)


def test_palette_delta_e_merge_collapses_near_colors_to_larger_cluster() -> None:
    rgb = np.array([(200, 0, 0), (203, 2, 2), (0, 0, 200)], dtype=np.float64)
    palette = Palette(
        codes=["R1", "R2", "B1"],
        rgb=rgb,
        lab=rgb_to_lab(rgb.reshape(-1, 1, 3)).reshape(-1, 3),
    )
    pixels = np.array([(200, 0, 0)] * 80 + [(203, 2, 2)] * 10 + [(0, 0, 200)] * 40, dtype=np.uint8)

    merged = merge_palette_indices_by_delta_e(
        np.array([0, 1, 2], dtype=int),
        palette,
        pixels,
        threshold_delta_e=5.0,
    )

    assert merged.tolist() == [0, 2]


def test_flat_image_detection_lowers_k_without_touching_photo_like_pixels() -> None:
    flat_pixels = np.array(
        [(20, 20, 20)] * 50 + [(150, 120, 90)] * 35 + [(210, 30, 30)] * 10 + [(255, 255, 255)] * 5,
        dtype=np.uint8,
    )
    photo_like_pixels = np.array([(i, (i * 37) % 256, (i * 83) % 256) for i in range(180)], dtype=np.uint8)

    flat_target, is_flat = choose_effective_target_colors(flat_pixels, 24)
    photo_target, photo_is_flat = choose_effective_target_colors(photo_like_pixels, 24)

    assert is_flat is True
    assert flat_target == 5
    assert photo_is_flat is False
    assert photo_target == 24


def test_flat_sticker_builds_transparent_low_color_pattern() -> None:
    builder = PatternBuilder(target_colors=24)

    sheet = builder.build(
        SizePreset.DOUBLE_BOARD_52X52,
        raw_image=flat_dog_sticker_bytes(),
        mode="script",
        auto_remove_white_bg=True,
    )

    no_bead_count = sum(sum(row) for row in sheet.no_bead_mask)
    red_codes = {
        color.code
        for color in sheet.palette_used
        if color.rgb[0] >= 160 and color.rgb[1] <= 80 and color.rgb[2] <= 90
    }

    assert sheet.metadata["white_bg_detected"] is True
    assert sheet.metadata["flat_image_detected"] is True
    assert sheet.metadata["effective_target_colors"] <= 5
    assert len(sheet.color_counts) <= 5
    assert no_bead_count > 52 * 52 * 0.45
    assert sheet.bead_total + no_bead_count == 52 * 52
    assert any(sheet.color_counts[code] > 0 for code in red_codes)


def test_low_grid_flat_sticker_preserves_outline_and_small_features() -> None:
    builder = PatternBuilder(target_colors=24)

    sheet = builder.build(
        SizePreset.SINGLE_BOARD_26X26,
        raw_image=flat_rabbit_sticker_bytes(),
        mode="script",
        auto_remove_white_bg=True,
    )

    black_codes = {
        color.code
        for color in sheet.palette_used
        if max(color.rgb) <= 60 or 0.2126 * color.rgb[0] + 0.7152 * color.rgb[1] + 0.0722 * color.rgb[2] <= 45
    }
    red_codes = {
        color.code
        for color in sheet.palette_used
        if color.rgb[0] >= 160 and color.rgb[1] <= 90 and color.rgb[2] <= 100
    }
    black_cells = cells_for_codes(sheet, black_codes)

    assert sheet.metadata["white_bg_detected"] is True
    assert sheet.metadata["low_grid_feature_priority"] is True
    assert sheet.metadata["low_grid_outline_reinforced"] is True
    assert len(sheet.color_counts) <= 6
    assert sum(sheet.color_counts.get(code, 0) for code in black_codes) >= 55
    assert largest_component(black_cells, 26, 26) >= 45
    assert sum(sheet.color_counts.get(code, 0) for code in red_codes) >= 8
    assert count_cells_in_box(black_cells, row_range=range(8, 14), col_range=range(8, 18)) >= 2


def test_feature_priority_downsample_keeps_tiny_red_block_over_fill_vote() -> None:
    image = Image.new("RGBA", (16, 16), (170, 140, 110, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle([6, 6, 9, 9], fill=(220, 20, 35, 255))

    fitted_plain = fit_to_canvas(image, 1, 1, (255, 255, 255, 0), preserve_features=False)
    fitted_feature = fit_to_canvas(image, 1, 1, (255, 255, 255, 0), preserve_features=True)

    assert fitted_plain.getpixel((0, 0))[:3] == (170, 140, 110)
    assert fitted_feature.getpixel((0, 0))[0] >= 200
    assert fitted_feature.getpixel((0, 0))[1] <= 60


def test_medium_and_large_flat_sticker_do_not_regress() -> None:
    builder = PatternBuilder(target_colors=24)
    raw = flat_rabbit_sticker_bytes()

    for size in (SizePreset.DOUBLE_BOARD_52X52, SizePreset.FOUR_BOARD_104X104):
        sheet = builder.build(size, raw_image=raw, mode="script", auto_remove_white_bg=True)
        red_codes = {
            color.code
            for color in sheet.palette_used
            if color.rgb[0] >= 160 and color.rgb[1] <= 90 and color.rgb[2] <= 100
        }

        assert sheet.metadata["white_bg_detected"] is True
        assert len(sheet.color_counts) <= 6
        assert sum(sheet.color_counts.get(code, 0) for code in red_codes) > 0
        assert sheet.bead_total + sum(sum(row) for row in sheet.no_bead_mask) == size.width * size.height


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


def test_partition_exporter_splits_standard_boards_into_four_quadrants() -> None:
    builder = PatternBuilder(target_colors=8)
    expected = {
        SizePreset.SINGLE_BOARD_26X26: 13,
        SizePreset.DOUBLE_BOARD_52X52: 26,
        SizePreset.TRIPLE_BOARD_78X78: 39,
        SizePreset.FOUR_BOARD_104X104: 52,
    }

    for size, quadrant_dim in expected.items():
        sheet = builder.build(size, raw_image=read_input("pet_synthetic.png"), mode="script")
        partitions = PatternExporter().export_partitions(sheet, partition_size=13)
        first = Image.open(io.BytesIO(partitions[0].image))

        assert len(partitions) == 4
        assert [partition.key for partition in partitions] == ["top_left", "top_right", "bottom_left", "bottom_right"]
        assert [partition.label for partition in partitions] == ["左上区", "右上区", "左下区", "右下区"]
        assert partitions[0].rows == quadrant_dim
        assert partitions[0].cols == quadrant_dim
        assert first.format == "PNG"
        assert first.width >= quadrant_dim * 7
        assert first.height > quadrant_dim * 7
    assert partition_filename("art_123", 1) == "pattern_art_123_partition_01.png"


def test_partition_cell_code_font_fits_multi_character_codes() -> None:
    image = Image.new("RGBA", (60, 60), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    font = fit_cell_code_font(draw, "R12", 30)
    assert font is not None
    bbox = draw.textbbox((0, 0), "R12", font=font)

    assert bbox[2] - bbox[0] <= 21


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


def flat_dog_sticker_bytes() -> bytes:
    image = Image.new("RGB", (160, 160), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse([38, 30, 122, 122], fill=(151, 128, 102), outline=(20, 20, 20), width=8)
    draw.polygon([(52, 36), (36, 16), (70, 30)], fill=(151, 128, 102), outline=(20, 20, 20))
    draw.polygon([(108, 36), (124, 16), (90, 30)], fill=(151, 128, 102), outline=(20, 20, 20))
    draw.rectangle([55, 104, 105, 116], fill=(210, 40, 42), outline=(20, 20, 20), width=3)
    draw.ellipse([58, 62, 70, 74], fill=(255, 255, 255), outline=(20, 20, 20), width=3)
    draw.ellipse([90, 62, 102, 74], fill=(255, 255, 255), outline=(20, 20, 20), width=3)
    draw.ellipse([75, 78, 86, 88], fill=(20, 20, 20))
    return image_bytes(image)


def flat_rabbit_sticker_bytes() -> bytes:
    image = Image.new("RGB", (180, 180), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    fill = (238, 218, 185)
    outline = (18, 18, 18)
    red = (214, 30, 42)
    pink = (252, 158, 182)

    draw.ellipse([48, 8, 78, 86], fill=fill, outline=outline, width=8)
    draw.ellipse([102, 8, 132, 86], fill=fill, outline=outline, width=8)
    draw.ellipse([57, 20, 69, 70], fill=pink)
    draw.ellipse([111, 20, 123, 70], fill=pink)
    draw.ellipse([36, 48, 144, 144], fill=fill, outline=outline, width=8)
    draw.ellipse([64, 78, 76, 92], fill=outline)
    draw.ellipse([104, 78, 116, 92], fill=outline)
    draw.ellipse([86, 96, 96, 106], fill=outline)
    draw.arc([74, 98, 92, 118], start=20, end=155, fill=outline, width=4)
    draw.arc([88, 98, 106, 118], start=25, end=160, fill=outline, width=4)
    draw.rectangle([56, 130, 124, 145], fill=red, outline=outline, width=4)
    return image_bytes(image)


def cells_for_codes(sheet, codes: set[str]) -> set[tuple[int, int]]:
    return {
        (row_idx, col_idx)
        for row_idx, row in enumerate(sheet.grid)
        for col_idx, cell in enumerate(row)
        if not isinstance(cell, NoBead) and cell.code in codes
    }


def largest_component(cells: set[tuple[int, int]], height: int, width: int) -> int:
    remaining = set(cells)
    best = 0
    while remaining:
        start = remaining.pop()
        stack = [start]
        size = 1
        while stack:
            row, col = stack.pop()
            for d_row, d_col in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                neighbor = (row + d_row, col + d_col)
                if 0 <= neighbor[0] < height and 0 <= neighbor[1] < width and neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
                    size += 1
        best = max(best, size)
    return best


def count_cells_in_box(cells: set[tuple[int, int]], *, row_range: range, col_range: range) -> int:
    rows = set(row_range)
    cols = set(col_range)
    return sum(1 for row, col in cells if row in rows and col in cols)


def image_bytes(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
