from __future__ import annotations

import io
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from pindou.pattern.builder import ColorRef, NoBead, PatternBuilder, PatternSheet, fit_to_canvas
from pindou.pattern.exporter import PatternExporter, fit_cell_code_font, labeled_grid_filename, partition_filename
from pindou.pattern.postprocess import cleanup_shape_artifacts, detect_and_remove_white_bg, normalize_cartoon_eye_features
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


def palette_map(*items: tuple[str, tuple[int, int, int]]) -> dict[str, ColorRef]:
    return {
        code: ColorRef("MARD", code, code, None, f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}", rgb, 5.0)
        for code, rgb in items
    }


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


def test_subject_alignment_centers_symmetric_cartoon_on_grid_axis() -> None:
    image = shifted_symmetric_face_image()

    for size in (26, 52):
        unaligned = fit_to_canvas(
            image,
            size,
            size,
            (255, 255, 255, 0),
            align_subject_to_grid=False,
        )
        aligned = fit_to_canvas(image, size, size, (255, 255, 255, 0))
        target_axis = size / 2

        unaligned_error = abs(foreground_bbox_center_x(unaligned) - target_axis)
        aligned_error = abs(foreground_bbox_center_x(aligned) - target_axis)
        unaligned_mismatch = vertical_alpha_mismatch(unaligned, target_axis)
        aligned_mismatch = vertical_alpha_mismatch(aligned, target_axis)

        assert unaligned_error >= 0.7
        assert aligned_error <= 0.3
        assert aligned_mismatch < unaligned_mismatch


def test_subject_alignment_metadata_is_reported_for_transparent_preview() -> None:
    builder = PatternBuilder(target_colors=8)

    sheet = builder.build(
        SizePreset.SINGLE_BOARD_26X26,
        preview=image_bytes(shifted_symmetric_face_image()),
        mode="ai",
    )

    alignment = sheet.metadata["subject_grid_alignment"]
    assert alignment["applied"] is True
    assert alignment["target_center"][0] == 13.0
    assert abs(alignment["shift_x"]) >= 0.7


def test_subject_alignment_does_not_transform_opaque_photo_like_input() -> None:
    image = opaque_asymmetric_photo_like_image()

    baseline = fit_to_canvas(
        image,
        26,
        26,
        (255, 255, 255, 255),
        align_subject_to_grid=False,
    )
    aligned = fit_to_canvas(image, 26, 26, (255, 255, 255, 255))

    assert np.array_equal(np.array(aligned, dtype=np.uint8), np.array(baseline, dtype=np.uint8))


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


def test_ai_flat_sticker_uses_minimal_palette_merge() -> None:
    builder = PatternBuilder(target_colors=6)

    sheet = builder.build(
        SizePreset.DOUBLE_BOARD_52X52,
        preview=flat_dog_sticker_bytes(),
        mode="ai",
    )

    assert sheet.metadata["target_colors"] == 6
    assert sheet.metadata["effective_target_colors"] <= 5
    assert sheet.metadata["palette_merge_delta_e"] == 9.0
    assert len(sheet.color_counts) <= 4


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


def test_shape_cleanup_merges_isolated_noise_but_keeps_dark_features() -> None:
    palette = palette_map(
        ("SKIN", (236, 198, 142)),
        ("NOISE", (92, 174, 138)),
        ("INK", (18, 18, 18)),
    )
    codes = [["SKIN" for _col in range(9)] for _row in range(9)]
    codes[1][1] = "NOISE"
    codes[3][3] = "INK"
    codes[3][5] = "INK"
    codes[5][4] = "INK"

    cleanup = cleanup_shape_artifacts(
        codes,
        palette,
        min_component_size=4,
        smooth_passes=1,
        enable_symmetry=False,
    )

    assert cleanup.codes[1][1] == "SKIN"
    assert cleanup.codes[3][3] == "INK"
    assert cleanup.codes[3][5] == "INK"
    assert cleanup.codes[5][4] == "INK"
    assert cleanup.denoised_cells == 1
    assert cleanup.protected_feature_cells == 3


def test_shape_cleanup_majority_vote_smooths_jagged_fill_edge() -> None:
    palette = palette_map(
        ("FILL", (230, 174, 118)),
        ("EDGE", (150, 128, 110)),
    )
    codes = [["FILL" for _col in range(5)] for _row in range(5)]
    codes[2][2] = "EDGE"

    cleanup = cleanup_shape_artifacts(
        codes,
        palette,
        min_component_size=1,
        smooth_passes=1,
        smooth_majority_threshold=5,
        enable_symmetry=False,
    )

    assert cleanup.codes[2][2] == "FILL"
    assert cleanup.smoothed_cells == 1


def test_shape_cleanup_symmetry_mirrors_tiny_protected_feature() -> None:
    palette = palette_map(
        ("SKIN", (236, 198, 142)),
        ("INK", (18, 18, 18)),
    )
    codes = [["SKIN" for _col in range(7)] for _row in range(7)]
    codes[2][2] = "INK"
    codes[2][4] = "INK"
    codes[4][2] = "INK"

    cleanup = cleanup_shape_artifacts(
        codes,
        palette,
        min_component_size=4,
        smooth_passes=1,
        enable_symmetry=True,
    )

    assert cleanup.codes[4][2] == "INK"
    assert cleanup.codes[4][4] == "INK"
    assert cleanup.symmetry_applied is True
    assert cleanup.symmetry_cells == 1


def test_cartoon_eye_normalization_makes_paired_eyes_equal_without_global_mirror() -> None:
    palette = palette_map(
        ("W", (255, 255, 255)),
        ("D", (1, 1, 1)),
        ("R", (230, 40, 50)),
    )
    codes: list[list[str | None]] = [[None for _ in range(40)] for _ in range(24)]
    for row in range(3, 21):
        for col in range(3, 37):
            codes[row][col] = "W"

    for row, col in ((10, 10), (10, 11), (11, 10), (11, 11), (12, 10)):
        codes[row][col] = "D"
    for row, col in ((10, 29), (10, 30), (11, 29)):
        codes[row][col] = "D"
    codes[15][20] = "D"
    codes[4][31] = "R"

    result = normalize_cartoon_eye_features(codes, palette)

    assert result.applied is True
    assert result.left_cells == result.right_cells
    assert result.codes[4][31] == "R"
    assert result.codes[15][20] == "D"


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


def test_clean_white_cat_sticker_keeps_white_body_and_continuous_outline() -> None:
    builder = PatternBuilder(target_colors=24)

    sheet = builder.build(
        SizePreset.DOUBLE_BOARD_52X52,
        raw_image=white_cat_sticker_bytes(),
        mode="script",
        auto_remove_white_bg=True,
    )

    white_codes = {
        color.code
        for color in sheet.palette_used
        if min(color.rgb) >= 248 and max(color.rgb) - min(color.rgb) <= 4
    }
    dirty_gray_codes = {
        color.code
        for color in sheet.palette_used
        if 180 <= min(color.rgb) < 248 and max(color.rgb) - min(color.rgb) <= 36
    }
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
    assert sheet.metadata["quality_preset"] == "clean_cartoon"
    assert sheet.metadata["preset_feature_priority"] is True
    assert sheet.metadata["flat_image_detected"] is True
    assert sheet.metadata["effective_target_colors"] <= 5
    assert len(sheet.color_counts) <= 6
    assert sum(sum(row) for row in sheet.no_bead_mask) >= int(52 * 52 * 0.45)
    assert sum(sheet.color_counts.get(code, 0) for code in white_codes) >= 240
    assert sum(sheet.color_counts.get(code, 0) for code in dirty_gray_codes) <= 4
    assert len(black_cells) >= 140
    assert largest_component(black_cells, 52, 52) >= int(len(black_cells) * 0.62)
    assert sum(sheet.color_counts.get(code, 0) for code in red_codes) >= 18
    assert any(
        count >= 3
        for color in sheet.palette_used
        for count in [sheet.color_counts.get(color.code, 0)]
        if color.rgb[0] >= 170 and color.rgb[1] >= 130 and color.rgb[2] <= 150
    )


def test_clean_cartoon_custom_sizes_keep_preset_and_eye_normalization() -> None:
    builder = PatternBuilder(target_colors=24)
    raw = white_cat_sticker_bytes()

    for size_value in ("64x64", "72x72", "104x104"):
        sheet = builder.build(
            SizePreset(size_value),
            raw_image=raw,
            mode="script",
            auto_remove_white_bg=True,
        )

        assert sheet.metadata["quality_preset"] == "clean_cartoon"
        assert sheet.metadata["preset_feature_priority"] is True
        assert sheet.metadata["eye_normalization"]["enabled"] is True
        assert sheet.metadata["eye_normalization"]["applied"] is True
        assert sheet.metadata["eye_normalization"]["left_cells"] == sheet.metadata["eye_normalization"]["right_cells"]


def test_photo_like_input_does_not_use_clean_cartoon_preset() -> None:
    builder = PatternBuilder(target_colors=24)

    sheet = builder.build(
        SizePreset.DOUBLE_BOARD_52X52,
        raw_image=photo_like_gradient_bytes(),
        mode="script",
        auto_remove_white_bg=True,
    )

    assert sheet.metadata["white_bg_detected"] is False
    assert sheet.metadata["quality_preset"] == "photo"
    assert sheet.metadata["preset_feature_priority"] is False
    assert sheet.metadata["eye_normalization"]["enabled"] is False
    assert sheet.metadata["flat_image_detected"] is False
    assert sheet.metadata["effective_target_colors"] == 24
    assert sum(sum(row) for row in sheet.no_bead_mask) == 0
    assert len(sheet.color_counts) >= 12


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

    assert bbox[2] - bbox[0] <= 24
    assert bbox[3] - bbox[1] <= 24


def test_labeled_grid_cell_code_font_fits_common_color_codes() -> None:
    image = Image.new("RGBA", (60, 60), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)

    for code in ("H7", "G11", "F23"):
        font = fit_cell_code_font(draw, code, 24)
        assert font is not None
        bbox = draw.textbbox((0, 0), code, font=font)
        assert bbox[2] - bbox[0] <= 20
        assert bbox[3] - bbox[1] <= 20


def test_labeled_grid_exporter_handles_multi_character_codes_on_26_grid() -> None:
    colors = [
        ColorRef("MARD", "H7", "H7", None, "#F05050", (240, 80, 80), 5.0),
        ColorRef("MARD", "G11", "G11", None, "#50A050", (80, 160, 80), 5.0),
        ColorRef("MARD", "F23", "F23", None, "#5060D0", (80, 96, 208), 5.0),
    ]
    grid = [[colors[(row + col) % len(colors)] for col in range(26)] for row in range(26)]
    counts = {color.code: 0 for color in colors}
    coords = []
    for row_idx, row in enumerate(grid):
        for col_idx, color in enumerate(row):
            counts[color.code] += 1
            coords.append((row_idx, col_idx, color.code))

    sheet = PatternSheet(
        grid=grid,
        color_counts=counts,
        bead_total=26 * 26,
        coords=coords,
        no_bead_mask=[[False for _col in range(26)] for _row in range(26)],
        palette_used=colors,
        estimated_cost_cny=0.0,
        brand="MARD",
        bead_diameter_mm=5.0,
    )

    png = PatternExporter().to_labeled_grid_png(sheet)
    image = Image.open(io.BytesIO(png))

    assert image.format == "PNG"
    assert image.width >= 26 * 24
    assert image.height > 26 * 24


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


def white_cat_sticker_bytes() -> bytes:
    image = Image.new("RGB", (220, 220), (250, 250, 246))
    pixels = image.load()
    assert pixels is not None
    for y in range(220):
        for x in range(220):
            base = 246 + ((x * 7 + y * 11) % 12)
            pixels[x, y] = (base, base, max(236, base - 6))

    center_x, center_y = 110, 105
    for y in range(220):
        for x in range(220):
            if ((x - center_x) / 67) ** 2 + ((y - center_y) / 62) ** 2 <= 1:
                base = 240 + ((x * 5 + y * 3) % 16)
                pixels[x, y] = (base, base, max(234, base - 4))

    draw = ImageDraw.Draw(image)
    outline = (18, 18, 18)
    red = (220, 35, 55)
    yellow = (245, 205, 72)

    draw.ellipse([43, 43, 177, 167], outline=outline, width=8)
    draw.polygon([(58, 57), (47, 18), (89, 46)], outline=outline)
    draw.polygon([(162, 57), (173, 18), (131, 46)], outline=outline)
    draw.ellipse([78, 90, 92, 104], fill=outline)
    draw.ellipse([128, 90, 142, 104], fill=outline)
    draw.ellipse([105, 108, 116, 118], fill=yellow, outline=outline, width=2)
    draw.line([108, 119, 108, 130], fill=outline, width=3)
    draw.arc([88, 120, 108, 140], start=0, end=145, fill=outline, width=3)
    draw.arc([108, 120, 128, 140], start=35, end=180, fill=outline, width=3)
    draw.ellipse([134, 30, 178, 70], fill=red, outline=outline, width=4)
    return image_bytes(image)


def photo_like_gradient_bytes() -> bytes:
    image = Image.new("RGB", (96, 72), (0, 0, 0))
    pixels = image.load()
    assert pixels is not None
    for y in range(72):
        for x in range(96):
            pixels[x, y] = (
                int(35 + x * 1.8 + (y % 7) * 4),
                int(55 + y * 2.3 + (x % 9) * 3),
                int(70 + ((x * 5 + y * 3) % 150)),
            )
    draw = ImageDraw.Draw(image)
    draw.ellipse([14, 18, 46, 58], fill=(226, 86, 72))
    draw.polygon([(58, 10), (90, 32), (72, 66)], fill=(62, 155, 112))
    return image_bytes(image)


def shifted_symmetric_face_image() -> Image.Image:
    image = Image.new("RGBA", (120, 120), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    axis = 52
    fill = (238, 214, 180, 255)
    outline = (20, 20, 20, 255)
    red = (210, 36, 48, 255)

    draw.ellipse([axis - 34, 18, axis + 34, 94], fill=fill, outline=outline, width=6)
    draw.ellipse([axis - 49, 40, axis - 29, 66], fill=fill, outline=outline, width=5)
    draw.ellipse([axis + 29, 40, axis + 49, 66], fill=fill, outline=outline, width=5)
    draw.ellipse([axis - 20, 50, axis - 9, 61], fill=outline)
    draw.ellipse([axis + 9, 50, axis + 20, 61], fill=outline)
    draw.rectangle([axis - 18, 75, axis + 18, 84], fill=red, outline=outline, width=3)
    draw.rectangle([axis - 12, 94, axis + 12, 112], fill=(80, 120, 220, 255), outline=outline, width=4)
    return image


def opaque_asymmetric_photo_like_image() -> Image.Image:
    image = Image.new("RGBA", (96, 72), (190, 170, 145, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 42, 71], fill=(70, 94, 138, 255))
    draw.rectangle([43, 0, 95, 71], fill=(205, 178, 118, 255))
    draw.ellipse([8, 22, 42, 58], fill=(230, 70, 60, 255))
    draw.polygon([(58, 10), (88, 30), (74, 62)], fill=(50, 150, 105, 255))
    return image


def foreground_bbox_center_x(image: Image.Image) -> float:
    alpha = np.array(image.getchannel("A"), dtype=np.uint8)
    _ys, xs = np.nonzero(alpha >= 128)
    assert len(xs) > 0
    return (int(xs.min()) + int(xs.max()) + 1) / 2


def vertical_alpha_mismatch(image: Image.Image, axis_x: float) -> float:
    alpha = np.array(image.getchannel("A"), dtype=np.uint8) >= 128
    height, width = alpha.shape
    radius = int(min(axis_x, width - axis_x))
    mismatches = 0
    compared = 0
    for offset in range(radius):
        left = int(axis_x - 1 - offset)
        right = int(axis_x + offset)
        if left < 0 or right >= width:
            continue
        mismatches += int(np.count_nonzero(alpha[:, left] != alpha[:, right]))
        compared += height
    return mismatches / compared if compared else 0.0


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
