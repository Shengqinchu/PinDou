"""Run real-image quantization quality checks for the cartoon cleanup work.

By default the harness compares the current working tree with cartoon eye
normalization disabled against the current working tree with the feature
enabled. This keeps the before/after focused on the eye-specialized batch. A
Git HEAD baseline remains available with ``--baseline-mode head``.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
from collections import Counter, deque
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from pindou.pattern.builder import NoBead, PatternBuilder, PatternSheet, prepare_input_image
from pindou.pattern.exporter import PatternExporter
from pindou.providers.base import SizePreset


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "06_backend"
ARTIFACT_DIR = BACKEND_DIR / "artifacts" / "quantization-quality"
INPUT_DIR = ARTIFACT_DIR / "inputs"
REQUIRED_INPUTS = {
    "hellokitty": INPUT_DIR / "hellokitty.png",
    "photo": INPUT_DIR / "photo.png",
}
DEFAULT_SIZES = ("52x52", "64x64", "72x72", "104x104")
DEFAULT_BASELINE_MODE = "current-no-eye"


def main() -> None:
    args = parse_args()
    missing = [str(path) for path in REQUIRED_INPUTS.values() if not path.exists()]
    if missing:
        raise SystemExit("Missing required real input(s):\n" + "\n".join(missing))

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    all_results: dict[str, Any] = {
        "sizes": args.sizes,
        "baseline_mode": args.baseline_mode,
        "baseline_ref": args.baseline_ref,
        "cases": {},
        "rembg": {},
        "resolution_summary": {},
    }

    for case_name, input_path in REQUIRED_INPUTS.items():
        case_results: dict[str, Any] = {}
        for size_value in args.sizes:
            case_results[size_value] = run_case(case_name, input_path, size_value, args)
        all_results["cases"][case_name] = case_results
        all_results["resolution_summary"][case_name] = build_resolution_summary(case_results)
        if args.include_rembg:
            all_results["rembg"][case_name] = run_rembg_probe(case_name, input_path, args.sizes[0])

    summary_path = ARTIFACT_DIR / "metrics-summary.json"
    summary_path.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path = ARTIFACT_DIR / "README.md"
    markdown_path.write_text(render_markdown(all_results), encoding="utf-8")
    print(json.dumps(all_results, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default=",".join(DEFAULT_SIZES))
    parser.add_argument("--baseline-mode", choices=("current-no-eye", "head"), default=DEFAULT_BASELINE_MODE)
    parser.add_argument("--baseline-ref", default="HEAD")
    parser.add_argument("--include-rembg", action="store_true")
    args = parser.parse_args()
    args.sizes = [size.strip() for size in args.sizes.split(",") if size.strip()]
    if not args.sizes:
        raise SystemExit("--sizes cannot be empty.")
    return args


def run_case(case_name: str, input_path: Path, size_value: str, args: argparse.Namespace) -> dict[str, Any]:
    if args.baseline_mode == "head":
        baseline = run_baseline_from_git(args.baseline_ref, case_name, input_path, size_value)
    else:
        baseline = run_current(case_name, input_path, size_value, label="before", eye_normalization=False)
    current = run_current(case_name, input_path, size_value, label="after", eye_normalization=True)
    near_white_mask = source_near_white_mask(input_path, size_value)
    baseline["metrics"] = calculate_metrics(baseline, near_white_mask)
    current["metrics"] = calculate_metrics(current, near_white_mask)
    write_eye_closeup(case_name, size_value, "before", baseline)
    write_eye_closeup(case_name, size_value, "after", current)
    return {
        "input": str(input_path),
        "baseline": strip_sheet_payload(baseline),
        "current": strip_sheet_payload(current),
        "delta": metric_delta(baseline["metrics"], current["metrics"]),
    }


def run_current(
    case_name: str,
    input_path: Path,
    size_value: str,
    *,
    label: str,
    eye_normalization: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    sheet = PatternBuilder(enable_cartoon_eye_normalization=eye_normalization).build(
        SizePreset(size_value),
        raw_image=input_path.read_bytes(),
        mode="script",
        auto_remove_white_bg=True,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return write_outputs(case_name, label, sheet, elapsed_ms, size_value=size_value)


def run_baseline_from_git(ref: str, case_name: str, input_path: Path, size_value: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="pindou-baseline-") as temp_raw:
        temp_dir = Path(temp_raw)
        archive_path = temp_dir / "backend.tar"
        subprocess.run(
            ["git", "archive", "--format=tar", "--output", str(archive_path), ref, "06_backend/pindou"],
            cwd=ROOT,
            check=True,
        )
        with tarfile.open(archive_path, "r") as archive:
            archive.extractall(temp_dir, filter="data")
        output_json = temp_dir / "sheet.json"
        output_simple = ARTIFACT_DIR / f"{case_name}-{size_slug(size_value)}-before-preview.png"
        output_labeled = ARTIFACT_DIR / f"{case_name}-{size_slug(size_value)}-before-labeled.png"
        script = baseline_inline_script()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(temp_dir / "06_backend")
        started = time.perf_counter()
        subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                str(input_path),
                str(output_json),
                str(output_simple),
                str(output_labeled),
                size_value,
            ],
            cwd=temp_dir / "06_backend",
            env=env,
            check=True,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        payload["runtime_ms_total"] = round(elapsed_ms, 2)
        payload["preview_png"] = str(output_simple)
        payload["labeled_png"] = str(output_labeled)
        return payload


def baseline_inline_script() -> str:
    return r'''
import json
import sys
import time
from pathlib import Path

from pindou.pattern.builder import NoBead, PatternBuilder
from pindou.pattern.exporter import PatternExporter
from pindou.providers.base import SizePreset


def compact(sheet):
    return {
        "grid": [[None if isinstance(cell, NoBead) else cell.code for cell in row] for row in sheet.grid],
        "palette": {
            color.code: {
                "rgb": list(color.rgb),
                "hex": color.hex,
                "name_cn": color.name_cn,
            }
            for color in sheet.palette_used
        },
        "color_counts": sheet.color_counts,
        "bead_total": sheet.bead_total,
        "metadata": {key: value for key, value in sheet.metadata.items() if key != "preview_png"},
    }


input_path = Path(sys.argv[1])
output_json = Path(sys.argv[2])
output_simple = Path(sys.argv[3])
output_labeled = Path(sys.argv[4])
size_value = sys.argv[5]
started = time.perf_counter()
sheet = PatternBuilder().build(
    SizePreset(size_value),
    raw_image=input_path.read_bytes(),
    mode="script",
    auto_remove_white_bg=True,
)
elapsed_ms = (time.perf_counter() - started) * 1000
output_simple.write_bytes(sheet.metadata["preview_png"])
output_labeled.write_bytes(PatternExporter().to_labeled_grid_png(sheet))
payload = compact(sheet)
payload["runtime_ms_total"] = round(elapsed_ms, 2)
payload["preview_png"] = str(output_simple)
payload["labeled_png"] = str(output_labeled)
output_json.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
'''


def write_outputs(case_name: str, label: str, sheet: PatternSheet, elapsed_ms: float, *, size_value: str) -> dict[str, Any]:
    slug = size_slug(size_value)
    preview_path = ARTIFACT_DIR / f"{case_name}-{slug}-{label}-preview.png"
    labeled_path = ARTIFACT_DIR / f"{case_name}-{slug}-{label}-labeled.png"
    preview_path.write_bytes(sheet.metadata["preview_png"])
    labeled_path.write_bytes(PatternExporter().to_labeled_grid_png(sheet))
    payload = compact_sheet(sheet)
    payload["runtime_ms_total"] = round(elapsed_ms, 2)
    payload["preview_png"] = str(preview_path)
    payload["labeled_png"] = str(labeled_path)
    return payload


def size_slug(size_value: str) -> str:
    return size_value.replace("x", "x")


def write_eye_closeup(case_name: str, size_value: str, label: str, sheet_payload: dict[str, Any]) -> None:
    grid = sheet_payload["grid"]
    palette = sheet_payload["palette"]
    if not grid or not grid[0]:
        return
    pair = detect_eye_pair(grid, palette)
    roi = eye_roi_from_pair(grid, pair)
    image = render_grid_crop(grid, palette, roi, cell_px=18 if len(grid) <= 72 else 12)
    path = ARTIFACT_DIR / f"{case_name}-{size_slug(size_value)}-{label}-eyes.png"
    image.save(path)
    sheet_payload["eye_closeup_png"] = str(path)


def eye_roi_from_pair(
    grid: list[list[str | None]],
    pair: tuple[dict[str, Any], dict[str, Any]] | None,
) -> tuple[int, int, int, int]:
    height = len(grid)
    width = len(grid[0]) if height else 0
    if pair is None:
        foreground = [(row, col) for row, line in enumerate(grid) for col, code in enumerate(line) if code is not None]
        if not foreground:
            return (0, height - 1, 0, width - 1)
        min_row = min(row for row, _col in foreground)
        max_row = max(row for row, _col in foreground)
        min_col = min(col for _row, col in foreground)
        max_col = max(col for _row, col in foreground)
        subject_height = max_row - min_row + 1
        return (
            max(0, int(round(min_row + subject_height * 0.18))),
            min(height - 1, int(round(min_row + subject_height * 0.62))),
            min_col,
            max_col,
        )
    cells = pair[0]["cells"] + pair[1]["cells"]
    min_row, max_row, min_col, max_col = component_bbox(cells)
    margin = max(4, int(round(max(max_row - min_row + 1, max_col - min_col + 1) * 0.9)))
    return (
        max(0, min_row - margin),
        min(height - 1, max_row + margin),
        max(0, min_col - margin),
        min(width - 1, max_col + margin),
    )


def render_grid_crop(
    grid: list[list[str | None]],
    palette: dict[str, dict[str, Any]],
    roi: tuple[int, int, int, int],
    *,
    cell_px: int,
) -> Image.Image:
    min_row, max_row, min_col, max_col = roi
    rows = max_row - min_row + 1
    cols = max_col - min_col + 1
    image = Image.new("RGB", (cols * cell_px + 1, rows * cell_px + 1), (252, 248, 242))
    arr = np.array(image, dtype=np.uint8)
    for row in range(rows):
        for col in range(cols):
            code = grid[min_row + row][min_col + col]
            if code is None:
                color = (255, 255, 255)
            else:
                color = tuple(palette.get(code, {}).get("rgb", [210, 210, 210]))
            y0 = row * cell_px
            x0 = col * cell_px
            arr[y0 : y0 + cell_px, x0 : x0 + cell_px] = color
    grid_color = np.array([223, 211, 198], dtype=np.uint8)
    arr[::cell_px, :] = grid_color
    arr[:, ::cell_px] = grid_color
    arr[-1, :] = grid_color
    arr[:, -1] = grid_color
    return Image.fromarray(arr)


def compact_sheet(sheet: PatternSheet) -> dict[str, Any]:
    return {
        "grid": [[None if isinstance(cell, NoBead) else cell.code for cell in row] for row in sheet.grid],
        "palette": {
            color.code: {
                "rgb": list(color.rgb),
                "hex": color.hex,
                "name_cn": color.name_cn,
            }
            for color in sheet.palette_used
        },
        "color_counts": sheet.color_counts,
        "bead_total": sheet.bead_total,
        "metadata": {key: value for key, value in sheet.metadata.items() if key != "preview_png"},
    }


def source_near_white_mask(input_path: Path, size_value: str) -> list[list[bool]]:
    prepared, no_bead_mask, _white_bg, _alignment = prepare_input_image(
        input_path.read_bytes(),
        SizePreset(size_value),
        input_mode="script",
        auto_remove_white_bg=True,
    )
    rgb = np.array(prepared.convert("RGB"), dtype=np.uint8)
    mask = np.array(no_bead_mask, dtype=bool)
    minimum = rgb.min(axis=2)
    maximum = rgb.max(axis=2)
    spread = maximum.astype(np.int16) - minimum.astype(np.int16)
    near_white = (~mask) & (minimum >= 238) & (spread <= 24)
    return near_white.tolist()


def calculate_metrics(sheet_payload: dict[str, Any], near_white_mask: list[list[bool]]) -> dict[str, Any]:
    grid = sheet_payload["grid"]
    palette = sheet_payload["palette"]
    height = len(grid)
    width = len(grid[0]) if height else 0
    total = width * height if width and height else 1
    no_beads = sum(1 for row in grid for code in row if code is None)
    palette_codes = sorted({code for row in grid for code in row if code is not None})
    components = collect_components(grid)
    isolated_components = sum(1 for component in components if len(component["cells"]) == 1)
    small_components_lt3 = sum(1 for component in components if len(component["cells"]) < 3)
    black_largest = largest_black_component(components, palette)
    symmetry = vertical_symmetry_mismatch(grid)
    eye_metrics = calculate_eye_metrics(grid, palette)
    near_white_codes_all: Counter[str] = Counter()
    near_white_codes_visible: Counter[str] = Counter()
    for row_idx, row in enumerate(grid):
        for col_idx, code in enumerate(row):
            if row_idx < len(near_white_mask) and col_idx < len(near_white_mask[row_idx]):
                if near_white_mask[row_idx][col_idx]:
                    final_code = code if code is not None else "NO_BEAD"
                    near_white_codes_all[final_code] += 1
                    if code is not None:
                        near_white_codes_visible[code] += 1
    return {
        "color_count": len(palette_codes),
        "codes": palette_codes,
        "bead_total": total - no_beads,
        "no_bead_ratio": round(no_beads / total, 4),
        "near_white_final_codes_all": dict(near_white_codes_all.most_common()),
        "near_white_final_codes_visible": dict(near_white_codes_visible.most_common()),
        "isolated_component_count": isolated_components,
        "small_component_lt3_count": small_components_lt3,
        "black_outline_largest_component": black_largest,
        "vertical_symmetry_mismatch": symmetry,
        "eye_metrics": eye_metrics,
        "runtime_ms_total": sheet_payload.get("runtime_ms_total"),
        "metadata": sheet_payload.get("metadata", {}),
    }


def collect_components(grid: list[list[str | None]]) -> list[dict[str, Any]]:
    height = len(grid)
    width = len(grid[0]) if height else 0
    visited = [[False for _ in range(width)] for _ in range(height)]
    components: list[dict[str, Any]] = []
    for row in range(height):
        for col in range(width):
            code = grid[row][col]
            if code is None or visited[row][col]:
                continue
            queue: deque[tuple[int, int]] = deque([(row, col)])
            visited[row][col] = True
            cells: list[tuple[int, int]] = []
            while queue:
                current_row, current_col = queue.popleft()
                cells.append((current_row, current_col))
                for n_row, n_col in neighbors4(current_row, current_col, height, width):
                    if not visited[n_row][n_col] and grid[n_row][n_col] == code:
                        visited[n_row][n_col] = True
                        queue.append((n_row, n_col))
            components.append({"code": code, "cells": cells})
    return components


def largest_black_component(components: list[dict[str, Any]], palette: dict[str, dict[str, Any]]) -> int:
    largest = 0
    for component in components:
        rgb = palette.get(component["code"], {}).get("rgb")
        if rgb is None:
            continue
        if black_like(rgb):
            largest = max(largest, len(component["cells"]))
    return largest


def black_like(rgb: list[int]) -> bool:
    r, g, b = rgb
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return luminance <= 45 or max(rgb) <= 55


def vertical_symmetry_mismatch(grid: list[list[str | None]]) -> dict[str, Any]:
    foreground = [(row, col) for row, line in enumerate(grid) for col, code in enumerate(line) if code is not None]
    if not foreground:
        return {"ratio": 0.0, "mismatches": 0, "pairs": 0, "occupancy_mismatches": 0}
    min_row = min(row for row, _col in foreground)
    max_row = max(row for row, _col in foreground)
    min_col = min(col for _row, col in foreground)
    max_col = max(col for _row, col in foreground)
    mismatches = 0
    occupancy_mismatches = 0
    pairs = 0
    for row in range(min_row, max_row + 1):
        for left_col in range(min_col, (min_col + max_col + 1) // 2):
            right_col = min_col + max_col - left_col
            if left_col == right_col:
                continue
            left = grid[row][left_col]
            right = grid[row][right_col]
            if left is None and right is None:
                continue
            pairs += 1
            if (left is None) != (right is None):
                occupancy_mismatches += 1
            if left != right:
                mismatches += 1
    ratio = mismatches / pairs if pairs else 0.0
    return {
        "ratio": round(ratio, 4),
        "mismatches": mismatches,
        "pairs": pairs,
        "occupancy_mismatches": occupancy_mismatches,
    }


def calculate_eye_metrics(grid: list[list[str | None]], palette: dict[str, dict[str, Any]]) -> dict[str, Any]:
    pair = detect_eye_pair(grid, palette)
    if pair is None:
        return {
            "pair_found": False,
            "left_cells": 0,
            "right_cells": 0,
            "cell_delta": 0,
            "shape_mismatch_ratio": None,
        }
    left, right = pair
    left_norm = normalize_eye_shape(left["cells"], mirror=False)
    right_norm = normalize_eye_shape(right["cells"], mirror=True)
    union = left_norm | right_norm
    mismatch = len(left_norm ^ right_norm)
    return {
        "pair_found": True,
        "left_cells": len(left["cells"]),
        "right_cells": len(right["cells"]),
        "cell_delta": abs(len(left["cells"]) - len(right["cells"])),
        "left_bbox": list(component_bbox(left["cells"])),
        "right_bbox": list(component_bbox(right["cells"])),
        "left_center": rounded_pair(left["center_row"], left["center_col"]),
        "right_center": rounded_pair(right["center_row"], right["center_col"]),
        "shape_mismatch_ratio": round(mismatch / len(union), 4) if union else 0.0,
    }


def detect_eye_pair(
    grid: list[list[str | None]],
    palette: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    foreground = [(row, col) for row, line in enumerate(grid) for col, code in enumerate(line) if code is not None]
    if not foreground:
        return None
    min_row = min(row for row, _col in foreground)
    max_row = max(row for row, _col in foreground)
    min_col = min(col for _row, col in foreground)
    max_col = max(col for _row, col in foreground)
    subject_height = max_row - min_row + 1
    subject_width = max_col - min_col + 1
    axis_col = (min_col + max_col) / 2.0
    candidates: list[dict[str, Any]] = []
    for component in collect_components(grid):
        rgb = palette.get(component["code"], {}).get("rgb")
        if rgb is None or not black_like(rgb):
            continue
        cells = component["cells"]
        if len(cells) < 2:
            continue
        bbox = component_bbox(cells)
        comp_min_row, comp_max_row, comp_min_col, comp_max_col = bbox
        comp_width = comp_max_col - comp_min_col + 1
        comp_height = comp_max_row - comp_min_row + 1
        if len(cells) > max(4, int(round(len(grid) * len(grid[0]) * 0.035))):
            continue
        if comp_width > max(2, int(round(subject_width * 0.18))):
            continue
        if comp_height > max(2, int(round(subject_height * 0.22))):
            continue
        center_row = sum(row for row, _col in cells) / len(cells)
        center_col = sum(col for _row, col in cells) / len(cells)
        if not (min_row + subject_height * 0.22 <= center_row <= min_row + subject_height * 0.72):
            continue
        axis_distance = abs(center_col - axis_col)
        if axis_distance < subject_width * 0.08 or axis_distance > subject_width * 0.40:
            continue
        if light_neighbor_ratio(grid, palette, cells) < 0.30:
            continue
        candidates.append(
            {
                "cells": cells,
                "center_row": center_row,
                "center_col": center_col,
                "bbox": bbox,
            }
        )
    left_candidates = [candidate for candidate in candidates if candidate["center_col"] < axis_col]
    right_candidates = [candidate for candidate in candidates if candidate["center_col"] > axis_col]
    best: tuple[dict[str, Any], dict[str, Any]] | None = None
    best_score: float | None = None
    for left in left_candidates:
        for right in right_candidates:
            row_delta = abs(left["center_row"] - right["center_row"])
            symmetry_error = abs((axis_col - left["center_col"]) - (right["center_col"] - axis_col))
            size_delta = abs(len(left["cells"]) - len(right["cells"])) / max(len(left["cells"]), len(right["cells"]))
            if row_delta > max(2.0, subject_height * 0.14):
                continue
            if symmetry_error > max(2.0, subject_width * 0.16):
                continue
            score = row_delta * 2.0 + symmetry_error * 2.0 + size_delta * 6.0 - min(
                len(left["cells"]),
                len(right["cells"]),
            ) * 0.04
            if best_score is None or score < best_score:
                best_score = score
                best = (left, right)
    return best


def component_bbox(cells: list[tuple[int, int]]) -> tuple[int, int, int, int]:
    rows = [row for row, _col in cells]
    cols = [col for _row, col in cells]
    return min(rows), max(rows), min(cols), max(cols)


def normalize_eye_shape(cells: list[tuple[int, int]], *, mirror: bool) -> set[tuple[int, int]]:
    min_row, max_row, min_col, max_col = component_bbox(cells)
    if mirror:
        return {(row - min_row, max_col - col) for row, col in cells}
    return {(row - min_row, col - min_col) for row, col in cells}


def light_neighbor_ratio(
    grid: list[list[str | None]],
    palette: dict[str, dict[str, Any]],
    cells: list[tuple[int, int]],
) -> float:
    height = len(grid)
    width = len(grid[0]) if height else 0
    cell_set = set(cells)
    total = 0
    light = 0
    for row, col in cells:
        for n_row, n_col in neighbors8(row, col, height, width):
            if (n_row, n_col) in cell_set:
                continue
            code = grid[n_row][n_col]
            if code is None:
                continue
            rgb = palette.get(code, {}).get("rgb")
            if rgb is None:
                continue
            total += 1
            if luminance(rgb) >= 135:
                light += 1
    return 0.0 if total == 0 else light / total


def luminance(rgb: list[int]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def rounded_pair(x: float | None, y: float | None) -> list[float] | None:
    if x is None or y is None:
        return None
    return [round(x, 3), round(y, 3)]


def neighbors4(row: int, col: int, height: int, width: int) -> list[tuple[int, int]]:
    return [
        (n_row, n_col)
        for n_row, n_col in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
        if 0 <= n_row < height and 0 <= n_col < width
    ]


def neighbors8(row: int, col: int, height: int, width: int) -> list[tuple[int, int]]:
    return [
        (n_row, n_col)
        for n_row in range(row - 1, row + 2)
        for n_col in range(col - 1, col + 2)
        if (n_row != row or n_col != col) and 0 <= n_row < height and 0 <= n_col < width
    ]


def metric_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_eye = before["eye_metrics"]
    after_eye = after["eye_metrics"]
    before_shape = before_eye.get("shape_mismatch_ratio")
    after_shape = after_eye.get("shape_mismatch_ratio")
    return {
        "color_count": after["color_count"] - before["color_count"],
        "no_bead_ratio": round(after["no_bead_ratio"] - before["no_bead_ratio"], 4),
        "isolated_component_count": after["isolated_component_count"] - before["isolated_component_count"],
        "small_component_lt3_count": after["small_component_lt3_count"] - before["small_component_lt3_count"],
        "black_outline_largest_component": (
            after["black_outline_largest_component"] - before["black_outline_largest_component"]
        ),
        "vertical_symmetry_mismatch_ratio": round(
            after["vertical_symmetry_mismatch"]["ratio"] - before["vertical_symmetry_mismatch"]["ratio"],
            4,
        ),
        "eye_cell_delta": after_eye.get("cell_delta", 0) - before_eye.get("cell_delta", 0),
        "eye_shape_mismatch_ratio": None
        if before_shape is None or after_shape is None
        else round(float(after_shape) - float(before_shape), 4),
    }


def strip_sheet_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"sheet", "grid"}
    }


def build_resolution_summary(case_results: dict[str, Any]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for size_value, result in case_results.items():
        after = result["current"]["metrics"]
        metadata = after.get("metadata", {})
        eye_metadata = metadata.get("eye_normalization", {})
        summary.append(
            {
                "size": size_value,
                "bead_total": after["bead_total"],
                "color_count": after["color_count"],
                "eye_pair_found": after["eye_metrics"]["pair_found"],
                "eye_left_cells": after["eye_metrics"]["left_cells"],
                "eye_right_cells": after["eye_metrics"]["right_cells"],
                "eye_shape_mismatch_ratio": after["eye_metrics"]["shape_mismatch_ratio"],
                "eye_normalization_applied": eye_metadata.get("applied", False),
                "eye_closeup_png": result["current"].get("eye_closeup_png"),
                "after_labeled_png": result["current"].get("labeled_png"),
            }
        )
    return summary


def run_rembg_probe(case_name: str, input_path: Path, size_value: str) -> dict[str, Any]:
    try:
        from rembg import remove  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - optional local dependency
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}"}

    process = current_process()
    memory_before_mb = rss_mb(process)
    started = time.perf_counter()
    try:
        output = remove(input_path.read_bytes(), session=None)
    except Exception as exc:  # pragma: no cover - optional local dependency
        return {"available": True, "failed": True, "reason": f"{type(exc).__name__}: {exc}"}
    elapsed_ms = (time.perf_counter() - started) * 1000
    memory_after_mb = rss_mb(process)
    output_path = ARTIFACT_DIR / f"{case_name}-rembg-u2net.png"
    output_path.write_bytes(output)
    sheet = PatternBuilder().build(
        SizePreset(size_value),
        preview=output,
        mode="ai",
    )
    rembg_sheet = write_outputs(case_name, "rembg-after", sheet, elapsed_ms, size_value=size_value)
    near_white_mask = source_near_white_mask(input_path, size_value)
    metrics = calculate_metrics(rembg_sheet, near_white_mask)
    return {
        "available": True,
        "runtime_ms": round(elapsed_ms, 2),
        "rss_delta_mb": None
        if memory_before_mb is None or memory_after_mb is None
        else round(memory_after_mb - memory_before_mb, 2),
        "matte_png": str(output_path),
        "metrics": metrics,
    }


def current_process() -> Any:
    try:
        import psutil  # type: ignore[import-not-found]

        return psutil.Process(os.getpid())
    except Exception:
        return None


def rss_mb(process: Any) -> float | None:
    if process is None:
        return None
    try:
        return process.memory_info().rss / 1024 / 1024
    except Exception:
        return None


def render_markdown(results: dict[str, Any]) -> str:
    lines = [
        "# Quantization Quality Harness",
        "",
        f"- Sizes: `{', '.join(results['sizes'])}`",
        f"- Baseline mode: `{results['baseline_mode']}`",
        f"- Baseline ref: `{results['baseline_ref']}`",
        "",
    ]
    for case_name, summary in results["resolution_summary"].items():
        lines.extend(
            [
                f"## {case_name}",
                "",
                "### Resolution summary",
                "",
                "| Size | Beads | Colors | Eye pair | L/R eye cells | Eye shape mismatch | Eye normalized | Eye closeup |",
                "| --- | ---: | ---: | --- | --- | ---: | --- | --- |",
            ]
        )
        for row in summary:
            lines.append(
                "| "
                + " | ".join(
                    [
                        row["size"],
                        str(row["bead_total"]),
                        str(row["color_count"]),
                        "yes" if row["eye_pair_found"] else "no",
                        f"{row['eye_left_cells']}/{row['eye_right_cells']}",
                        str(row["eye_shape_mismatch_ratio"]),
                        "yes" if row["eye_normalization_applied"] else "no",
                        f"`{row.get('eye_closeup_png')}`",
                    ]
                )
                + " |"
            )
        lines.append("")
        for size_value, case in results["cases"][case_name].items():
            before = case["baseline"]["metrics"]
            after = case["current"]["metrics"]
            lines.extend(
                [
                    f"### {size_value}",
                    "",
                "| Metric | Before | After | Delta |",
                "| --- | ---: | ---: | ---: |",
                table_row("color_count", before, after, case["delta"]),
                table_row("no_bead_ratio", before, after, case["delta"]),
                table_row("isolated_component_count", before, after, case["delta"]),
                table_row("small_component_lt3_count", before, after, case["delta"]),
                table_row("black_outline_largest_component", before, after, case["delta"]),
                (
                    "| vertical_symmetry_mismatch_ratio | "
                    f"{before['vertical_symmetry_mismatch']['ratio']} | "
                    f"{after['vertical_symmetry_mismatch']['ratio']} | "
                    f"{case['delta']['vertical_symmetry_mismatch_ratio']} |"
                ),
                    (
                        "| eye_cell_delta | "
                        f"{before['eye_metrics']['cell_delta']} | "
                        f"{after['eye_metrics']['cell_delta']} | "
                        f"{case['delta']['eye_cell_delta']} |"
                    ),
                    (
                        "| eye_shape_mismatch_ratio | "
                        f"{before['eye_metrics']['shape_mismatch_ratio']} | "
                        f"{after['eye_metrics']['shape_mismatch_ratio']} | "
                        f"{case['delta']['eye_shape_mismatch_ratio']} |"
                    ),
                "",
                f"- Before preview: `{case['baseline']['preview_png']}`",
                f"- After preview: `{case['current']['preview_png']}`",
                f"- Before labeled: `{case['baseline']['labeled_png']}`",
                f"- After labeled: `{case['current']['labeled_png']}`",
                    f"- Before eyes: `{case['baseline'].get('eye_closeup_png')}`",
                    f"- After eyes: `{case['current'].get('eye_closeup_png')}`",
                f"- Near-white final codes before/all: `{before['near_white_final_codes_all']}`",
                f"- Near-white final codes after/all: `{after['near_white_final_codes_all']}`",
                f"- Near-white final codes before/visible: `{before['near_white_final_codes_visible']}`",
                f"- Near-white final codes after/visible: `{after['near_white_final_codes_visible']}`",
                "",
            ]
            )
    if results.get("rembg"):
        lines.extend(
            [
                "## rembg probe",
                "",
                "| Case | Available | Runtime ms | RSS delta MB | Colors | No-bead | Black max | Matte |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for case_name, probe in results["rembg"].items():
            if not probe.get("available"):
                lines.append(f"| {case_name} | no |  |  |  |  |  | {probe.get('reason', '')} |")
                continue
            metrics = probe["metrics"]
            lines.append(
                "| "
                + " | ".join(
                    [
                        case_name,
                        "yes",
                        str(probe.get("runtime_ms")),
                        str(probe.get("rss_delta_mb")),
                        str(metrics["color_count"]),
                        str(metrics["no_bead_ratio"]),
                        str(metrics["black_outline_largest_component"]),
                        f"`{probe.get('matte_png')}`",
                    ]
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def table_row(metric: str, before: dict[str, Any], after: dict[str, Any], delta: dict[str, Any]) -> str:
    return f"| {metric} | {before[metric]} | {after[metric]} | {delta[metric]} |"


if __name__ == "__main__":
    main()
