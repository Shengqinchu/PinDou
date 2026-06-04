"""Post-processing rules for bead-friendly pattern grids."""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass

import numpy as np
from PIL import Image

from pindou.colormap.matcher import ciede2000_distance
from pindou.colormap.matcher import nearest_color_code
from pindou.pattern.builder import ColorRef
from pindou.pattern.quantize_core import delta_e_ciede2000, rgb_to_lab


GridCodes = list[list[str | None]]
WHITE_RGB = (255, 255, 255)
FLOOD_FILL_WHITE_DELTA_E = 18.0
EDGE_BACKGROUND_BIN_SIZE = 8
EDGE_BACKGROUND_MIN_DOMINANCE = 0.30
LIGHT_BACKGROUND_MIN_CHANNEL = 185
LIGHT_BACKGROUND_MAX_SPREAD = 70
OPAQUE_ALPHA_THRESHOLD = 128
LOW_GRID_OUTLINE_MIN_DARK_RATIO = 0.025
SHAPE_CLEANUP_MIN_COMPONENT_SIZE = 4
SHAPE_SMOOTH_MAJORITY_THRESHOLD = 5
SHAPE_SMOOTH_PASSES = 1
FEATURE_MAX_COMPONENT_SIZE = 10
FEATURE_DARK_LUMINANCE = 78.0
FEATURE_NEIGHBOR_CONTRAST = 48.0
FEATURE_ACCENT_MAX_COMPONENT_SIZE = 12
SYMMETRY_MAX_MISMATCH_RATIO = 0.22
SYMMETRY_MAX_OCCUPANCY_MISMATCH_RATIO = 0.12


@dataclass(frozen=True)
class ShapeCleanupResult:
    codes: GridCodes
    denoised_cells: int = 0
    smoothed_cells: int = 0
    symmetry_cells: int = 0
    protected_feature_cells: int = 0
    symmetry_applied: bool = False

    def to_metadata(self) -> dict[str, object]:
        return {
            "enabled": True,
            "denoised_cells": self.denoised_cells,
            "smoothed_cells": self.smoothed_cells,
            "symmetry_cells": self.symmetry_cells,
            "protected_feature_cells": self.protected_feature_cells,
            "symmetry_applied": self.symmetry_applied,
        }


def merge_small_components(
    codes: GridCodes,
    palette_by_code: dict[str, ColorRef],
    *,
    min_component_size: int = 3,
    protected_cells: set[tuple[int, int]] | None = None,
) -> GridCodes:
    result, _changed = merge_small_components_with_stats(
        codes,
        palette_by_code,
        min_component_size=min_component_size,
        protected_cells=protected_cells,
    )
    return result


def merge_small_components_with_stats(
    codes: GridCodes,
    palette_by_code: dict[str, ColorRef],
    *,
    min_component_size: int = 3,
    protected_cells: set[tuple[int, int]] | None = None,
) -> tuple[GridCodes, int]:
    if not codes or not codes[0]:
        return codes, 0

    height = len(codes)
    width = len(codes[0])
    result = [row[:] for row in codes]
    visited = [[False for _ in range(width)] for _ in range(height)]
    protected_cells = protected_cells or set()
    changed = 0

    for row in range(height):
        for col in range(width):
            code = result[row][col]
            if code is None or visited[row][col]:
                continue
            component = collect_component(result, visited, row, col, code)
            if len(component) >= min_component_size or any(cell in protected_cells for cell in component):
                continue
            replacement = choose_replacement_code(result, component, palette_by_code, code)
            if replacement is None:
                continue
            for y, x in component:
                result[y][x] = replacement
                changed += 1
    return result, changed


def cleanup_shape_artifacts(
    codes: GridCodes,
    palette_by_code: dict[str, ColorRef],
    *,
    min_component_size: int = SHAPE_CLEANUP_MIN_COMPONENT_SIZE,
    smooth_passes: int = SHAPE_SMOOTH_PASSES,
    smooth_majority_threshold: int = SHAPE_SMOOTH_MAJORITY_THRESHOLD,
    enable_symmetry: bool = True,
) -> ShapeCleanupResult:
    """Remove bead-grid artifacts while preserving tiny high-contrast facial features."""

    if not codes or not codes[0]:
        return ShapeCleanupResult(codes=codes)

    protected_cells = detect_protected_feature_cells(codes, palette_by_code)
    denoised, denoised_cells = merge_small_components_with_stats(
        codes,
        palette_by_code,
        min_component_size=min_component_size,
        protected_cells=protected_cells,
    )
    smoothed, smoothed_cells = majority_vote_smooth(
        denoised,
        palette_by_code,
        protected_cells=protected_cells,
        passes=smooth_passes,
        majority_threshold=smooth_majority_threshold,
    )
    symmetry_codes = smoothed
    symmetry_cells = 0
    symmetry_applied = False
    if enable_symmetry:
        symmetry_codes, symmetry_cells, symmetry_applied = maybe_apply_vertical_symmetry(
            smoothed,
            palette_by_code,
            protected_cells=protected_cells,
        )

    return ShapeCleanupResult(
        codes=symmetry_codes,
        denoised_cells=denoised_cells,
        smoothed_cells=smoothed_cells,
        symmetry_cells=symmetry_cells,
        protected_feature_cells=len(protected_cells),
        symmetry_applied=symmetry_applied,
    )


def detect_protected_feature_cells(codes: GridCodes, palette_by_code: dict[str, ColorRef]) -> set[tuple[int, int]]:
    height = len(codes)
    width = len(codes[0])
    visited = [[False for _ in range(width)] for _ in range(height)]
    protected: set[tuple[int, int]] = set()

    for row in range(height):
        for col in range(width):
            code = codes[row][col]
            if code is None or visited[row][col]:
                continue
            component = collect_component(codes, visited, row, col, code)
            color = palette_by_code.get(code)
            if color is None:
                continue
            if is_protected_dark_feature(codes, component, palette_by_code, color) or is_protected_accent_feature(
                component,
                color,
            ):
                protected.update(component)
    return protected


def is_protected_dark_feature(
    codes: GridCodes,
    component: list[tuple[int, int]],
    palette_by_code: dict[str, ColorRef],
    color: ColorRef,
) -> bool:
    if len(component) > FEATURE_MAX_COMPONENT_SIZE or color_luminance(color) > FEATURE_DARK_LUMINANCE:
        return False
    neighbor_codes = component_neighbor_codes(codes, component)
    if len(neighbor_codes) < 2:
        return False
    neighbor_luminances = [
        color_luminance(palette_by_code[code])
        for code in neighbor_codes
        if code in palette_by_code and code != component_code(codes, component)
    ]
    if not neighbor_luminances:
        return False
    return (sum(neighbor_luminances) / len(neighbor_luminances)) - color_luminance(color) >= FEATURE_NEIGHBOR_CONTRAST


def is_protected_accent_feature(component: list[tuple[int, int]], color: ColorRef) -> bool:
    return len(component) <= FEATURE_ACCENT_MAX_COMPONENT_SIZE and is_feature_accent_color(color)


def majority_vote_smooth(
    codes: GridCodes,
    palette_by_code: dict[str, ColorRef],
    *,
    protected_cells: set[tuple[int, int]],
    passes: int,
    majority_threshold: int,
) -> tuple[GridCodes, int]:
    if passes <= 0:
        return codes, 0

    result = [row[:] for row in codes]
    height = len(codes)
    width = len(codes[0])
    changed = 0
    for _pass in range(passes):
        original = [row[:] for row in result]
        updates: list[tuple[int, int, str | None]] = []
        for row in range(height):
            for col in range(width):
                if (row, col) in protected_cells:
                    continue
                current = original[row][col]
                if current is None:
                    continue
                current_color = palette_by_code.get(current)
                if current_color is not None and is_tiny_feature_color(current_color):
                    continue
                neighbor_values = [
                    original[n_row][n_col]
                    for n_row, n_col in neighbors8(row, col, height, width)
                ]
                counts = Counter(neighbor_values)
                replacement, count = counts.most_common(1)[0]
                if replacement == current or count < majority_threshold:
                    continue
                same_count = counts.get(current, 0)
                if replacement is None and count < majority_threshold + 1:
                    continue
                if same_count > 2:
                    continue
                if replacement is not None and replacement not in palette_by_code:
                    continue
                updates.append((row, col, replacement))
        if not updates:
            continue
        for row, col, replacement in updates:
            result[row][col] = replacement
        changed += len(updates)
    return result, changed


def maybe_apply_vertical_symmetry(
    codes: GridCodes,
    palette_by_code: dict[str, ColorRef],
    *,
    protected_cells: set[tuple[int, int]],
) -> tuple[GridCodes, int, bool]:
    bbox = foreground_bbox(codes)
    if bbox is None:
        return codes, 0, False
    min_row, max_row, min_col, max_col = bbox
    pairs: list[tuple[int, int, int]] = []
    mismatch = 0
    occupancy_mismatch = 0
    for row in range(min_row, max_row + 1):
        for left_col in range(min_col, (min_col + max_col + 1) // 2):
            right_col = min_col + max_col - left_col
            if left_col == right_col:
                continue
            left = codes[row][left_col]
            right = codes[row][right_col]
            if left is None and right is None:
                continue
            pairs.append((row, left_col, right_col))
            if (left is None) != (right is None):
                occupancy_mismatch += 1
            if not codes_equivalent(left, right, palette_by_code):
                mismatch += 1
    if not pairs:
        return codes, 0, False
    mismatch_ratio = mismatch / len(pairs)
    occupancy_ratio = occupancy_mismatch / len(pairs)
    if mismatch_ratio > SYMMETRY_MAX_MISMATCH_RATIO or occupancy_ratio > SYMMETRY_MAX_OCCUPANCY_MISMATCH_RATIO:
        return codes, 0, False

    result = [row[:] for row in codes]
    changed = 0
    for row, left_col, right_col in pairs:
        left = result[row][left_col]
        right = result[row][right_col]
        if codes_equivalent(left, right, palette_by_code):
            continue
        chosen = choose_symmetric_code(result, row, left_col, right_col, protected_cells)
        if result[row][left_col] != chosen:
            result[row][left_col] = chosen
            changed += 1
        if result[row][right_col] != chosen:
            result[row][right_col] = chosen
            changed += 1
    return result, changed, changed > 0


def color_luminance(color: ColorRef) -> float:
    r, g, b = color.rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def component_code(codes: GridCodes, component: list[tuple[int, int]]) -> str | None:
    if not component:
        return None
    row, col = component[0]
    return codes[row][col]


def component_neighbor_codes(codes: GridCodes, component: list[tuple[int, int]]) -> list[str]:
    height = len(codes)
    width = len(codes[0])
    component_set = set(component)
    neighbor_codes: list[str] = []
    for row, col in component:
        for n_row, n_col in neighbors(row, col, height, width):
            if (n_row, n_col) in component_set:
                continue
            neighbor_code = codes[n_row][n_col]
            if neighbor_code is not None:
                neighbor_codes.append(neighbor_code)
    return neighbor_codes


def is_tiny_feature_color(color: ColorRef) -> bool:
    return color_luminance(color) <= FEATURE_DARK_LUMINANCE or is_feature_accent_color(color)


def foreground_bbox(codes: GridCodes) -> tuple[int, int, int, int] | None:
    foreground = [
        (row, col)
        for row, grid_row in enumerate(codes)
        for col, code in enumerate(grid_row)
        if code is not None
    ]
    if not foreground:
        return None
    rows = [row for row, _col in foreground]
    cols = [col for _row, col in foreground]
    return min(rows), max(rows), min(cols), max(cols)


def codes_equivalent(left: str | None, right: str | None, palette_by_code: dict[str, ColorRef]) -> bool:
    if left == right:
        return True
    if left is None or right is None:
        return False
    left_color = palette_by_code.get(left)
    right_color = palette_by_code.get(right)
    if left_color is None or right_color is None:
        return False
    return ciede2000_distance(left_color.rgb, right_color.rgb) <= 8.0


def choose_symmetric_code(
    codes: GridCodes,
    row: int,
    left_col: int,
    right_col: int,
    protected_cells: set[tuple[int, int]],
) -> str | None:
    left = codes[row][left_col]
    right = codes[row][right_col]
    left_protected = (row, left_col) in protected_cells
    right_protected = (row, right_col) in protected_cells
    if left_protected and not right_protected:
        return left
    if right_protected and not left_protected:
        return right
    if left is None and right is not None:
        return right
    if right is None and left is not None:
        return left

    height = len(codes)
    width = len(codes[0])

    def support(col: int, code: str | None) -> int:
        if code is None:
            return 0
        return sum(1 for n_row, n_col in neighbors8(row, col, height, width) if codes[n_row][n_col] == code)

    left_support = support(left_col, left)
    right_support = support(right_col, right)
    if right_support > left_support:
        return right
    return left


def reinforce_low_grid_outline(
    codes: GridCodes,
    palette_by_code: dict[str, ColorRef],
) -> tuple[GridCodes, bool]:
    if not codes or not codes[0]:
        return codes, False

    height = len(codes)
    width = len(codes[0])
    foreground = [(row, col) for row in range(height) for col in range(width) if codes[row][col] is not None]
    if not foreground:
        return codes, False

    black_counts: dict[str, int] = {}
    for row, col in foreground:
        code = codes[row][col]
        if code is not None and code in palette_by_code and is_black_outline(palette_by_code[code]):
            black_counts[code] = black_counts.get(code, 0) + 1
    if not black_counts or sum(black_counts.values()) / len(foreground) < LOW_GRID_OUTLINE_MIN_DARK_RATIO:
        return codes, False

    outline_code = max(black_counts, key=black_counts.get)
    result = [row[:] for row in codes]
    changed = False

    for row, col in foreground:
        if not is_foreground_boundary(codes, row, col):
            continue
        code = result[row][col]
        if code is not None and code in palette_by_code and is_feature_accent_color(palette_by_code[code]):
            continue
        if result[row][col] != outline_code:
            result[row][col] = outline_code
            changed = True

    changed = bridge_single_cell_outline_gaps(result, palette_by_code, outline_code) or changed
    return result, changed


def is_foreground_boundary(codes: GridCodes, row: int, col: int) -> bool:
    height = len(codes)
    width = len(codes[0])
    for d_row in (-1, 0, 1):
        for d_col in (-1, 0, 1):
            if d_row == 0 and d_col == 0:
                continue
            n_row = row + d_row
            n_col = col + d_col
            if n_row < 0 or n_row >= height or n_col < 0 or n_col >= width:
                return True
            if codes[n_row][n_col] is None:
                return True
    return False


def bridge_single_cell_outline_gaps(
    codes: GridCodes,
    palette_by_code: dict[str, ColorRef],
    outline_code: str,
) -> bool:
    height = len(codes)
    width = len(codes[0])
    changed = False
    original = [row[:] for row in codes]
    for row in range(height):
        for col in range(width):
            code = original[row][col]
            if code is None or code == outline_code:
                continue
            if code in palette_by_code and (
                is_black_outline(palette_by_code[code]) or is_feature_accent_color(palette_by_code[code])
            ):
                continue
            horizontal = (
                col > 0
                and col < width - 1
                and original[row][col - 1] == outline_code
                and original[row][col + 1] == outline_code
            )
            vertical = (
                row > 0
                and row < height - 1
                and original[row - 1][col] == outline_code
                and original[row + 1][col] == outline_code
            )
            if horizontal or vertical:
                codes[row][col] = outline_code
                changed = True
    return changed


def is_feature_accent_color(color: ColorRef) -> bool:
    r, g, b = color.rgb
    return r >= 150 and r - max(g, b) >= 45 and max(color.rgb) - min(color.rgb) >= 70


def detect_and_remove_white_bg(
    image: Image.Image,
    tolerance_delta_e: float = FLOOD_FILL_WHITE_DELTA_E,
) -> tuple[Image.Image, bool]:
    rgba = image.convert("RGBA")
    arr = np.array(rgba, dtype=np.uint8)
    background_rgb = dominant_edge_background(arr)
    if background_rgb is None or not is_removable_background(background_rgb, tolerance_delta_e):
        return image, False

    height, width = arr.shape[:2]
    background_mask = background_similarity_mask(arr, background_rgb, tolerance_delta_e)
    visited = np.zeros((height, width), dtype=bool)
    queue: deque[tuple[int, int]] = deque()
    for x in range(width):
        if background_mask[0, x]:
            queue.append((x, 0))
        if height > 1 and background_mask[height - 1, x]:
            queue.append((x, height - 1))
    for y in range(1, max(height - 1, 1)):
        if background_mask[y, 0]:
            queue.append((0, y))
        if width > 1 and background_mask[y, width - 1]:
            queue.append((width - 1, y))

    removed = 0
    while queue:
        x, y = queue.popleft()
        if visited[y, x] or not background_mask[y, x]:
            continue
        visited[y, x] = True
        arr[y, x, 3] = 0
        removed += 1
        for next_x, next_y in pixel_neighbors(x, y, width, height):
            if not visited[next_y, next_x]:
                queue.append((next_x, next_y))

    if removed == 0:
        return image, False
    return Image.fromarray(arr), True


def dominant_edge_background(arr: np.ndarray) -> tuple[int, int, int] | None:
    height, width = arr.shape[:2]
    if height == 0 or width == 0:
        return None
    edge_pixels = np.concatenate(
        (
            arr[0, :, :],
            arr[height - 1, :, :],
            arr[:, 0, :],
            arr[:, width - 1, :],
        ),
        axis=0,
    )
    edge_pixels = edge_pixels[edge_pixels[:, 3] >= OPAQUE_ALPHA_THRESHOLD]
    if len(edge_pixels) == 0:
        return None
    bins = (edge_pixels[:, :3] // EDGE_BACKGROUND_BIN_SIZE).astype(np.uint16)
    _unique_bins, inverse, counts = np.unique(bins, axis=0, return_inverse=True, return_counts=True)
    best = int(np.argmax(counts))
    if counts[best] / len(edge_pixels) < EDGE_BACKGROUND_MIN_DOMINANCE:
        return None
    members = edge_pixels[inverse == best, :3].astype(np.float64)
    mean = np.rint(members.mean(axis=0)).astype(int)
    return (int(mean[0]), int(mean[1]), int(mean[2]))


def is_removable_background(rgb: tuple[int, int, int], tolerance_delta_e: float) -> bool:
    if ciede2000_distance(rgb, WHITE_RGB) <= tolerance_delta_e:
        return True
    return min(rgb) >= LIGHT_BACKGROUND_MIN_CHANNEL and max(rgb) - min(rgb) <= LIGHT_BACKGROUND_MAX_SPREAD


def background_similarity_mask(arr: np.ndarray, background_rgb: tuple[int, int, int], tolerance_delta_e: float) -> np.ndarray:
    rgb = arr[:, :, :3].astype(np.float64)
    lab = rgb_to_lab(rgb)
    background_lab = rgb_to_lab(np.array(background_rgb, dtype=np.float64).reshape(1, 1, 3)).reshape(3)
    distance = delta_e_ciede2000(lab, background_lab)
    return (arr[:, :, 3] >= OPAQUE_ALPHA_THRESHOLD) & (distance <= tolerance_delta_e)


def average_corner_delta_e_to_white(image: Image.Image, sample_size: int = 5) -> float:
    rgba = image.convert("RGBA")
    arr = np.array(rgba, dtype=np.uint8)
    height, width = arr.shape[:2]
    box = min(sample_size, width, height)
    regions = (
        arr[:box, :box, :3],
        arr[:box, width - box : width, :3],
        arr[height - box : height, :box, :3],
        arr[height - box : height, width - box : width, :3],
    )
    distances = []
    for region in regions:
        mean = region.reshape(-1, 3).mean(axis=0)
        rgb = (int(round(mean[0])), int(round(mean[1])), int(round(mean[2])))
        distances.append(ciede2000_distance(rgb, WHITE_RGB))
    return float(sum(distances) / len(distances))


def pixel_neighbors(x: int, y: int, width: int, height: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nx = x + dx
        ny = y + dy
        if 0 <= nx < width and 0 <= ny < height:
            out.append((nx, ny))
    return out


def collect_component(
    codes: GridCodes,
    visited: list[list[bool]],
    start_row: int,
    start_col: int,
    code: str,
) -> list[tuple[int, int]]:
    height = len(codes)
    width = len(codes[0])
    queue: deque[tuple[int, int]] = deque([(start_row, start_col)])
    visited[start_row][start_col] = True
    component: list[tuple[int, int]] = []

    while queue:
        row, col = queue.popleft()
        component.append((row, col))
        for n_row, n_col in neighbors(row, col, height, width):
            if visited[n_row][n_col] or codes[n_row][n_col] != code:
                continue
            visited[n_row][n_col] = True
            queue.append((n_row, n_col))
    return component


def choose_replacement_code(
    codes: GridCodes,
    component: list[tuple[int, int]],
    palette_by_code: dict[str, ColorRef],
    original_code: str,
) -> str | None:
    height = len(codes)
    width = len(codes[0])
    component_set = set(component)
    neighbor_codes: list[str] = []
    for row, col in component:
        for n_row, n_col in neighbors(row, col, height, width):
            if (n_row, n_col) in component_set:
                continue
            neighbor_code = codes[n_row][n_col]
            if neighbor_code is not None and neighbor_code in palette_by_code:
                neighbor_codes.append(neighbor_code)
    candidates = [palette_by_code[code] for code in dict.fromkeys(neighbor_codes)]
    if not candidates:
        return None
    return nearest_color_code(palette_by_code[original_code].rgb, candidates)


def is_black_outline(color: ColorRef) -> bool:
    r, g, b = color.rgb
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return luminance <= 45 or max(color.rgb) <= 55


def neighbors(row: int, col: int, height: int, width: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for d_row, d_col in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        n_row = row + d_row
        n_col = col + d_col
        if 0 <= n_row < height and 0 <= n_col < width:
            out.append((n_row, n_col))
    return out


def neighbors8(row: int, col: int, height: int, width: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for d_row in (-1, 0, 1):
        for d_col in (-1, 0, 1):
            if d_row == 0 and d_col == 0:
                continue
            n_row = row + d_row
            n_col = col + d_col
            if 0 <= n_row < height and 0 <= n_col < width:
                out.append((n_row, n_col))
    return out
