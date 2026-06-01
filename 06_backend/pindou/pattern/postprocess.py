"""Post-processing rules for bead-friendly pattern grids."""

from __future__ import annotations

from collections import deque

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


def merge_small_components(
    codes: GridCodes,
    palette_by_code: dict[str, ColorRef],
    *,
    min_component_size: int = 3,
) -> GridCodes:
    if not codes or not codes[0]:
        return codes

    height = len(codes)
    width = len(codes[0])
    result = [row[:] for row in codes]
    visited = [[False for _ in range(width)] for _ in range(height)]

    for row in range(height):
        for col in range(width):
            code = result[row][col]
            if code is None or visited[row][col]:
                continue
            component = collect_component(result, visited, row, col, code)
            if len(component) >= min_component_size or is_black_outline(palette_by_code[code]):
                continue
            replacement = choose_replacement_code(result, component, palette_by_code, code)
            if replacement is None:
                continue
            for y, x in component:
                result[y][x] = replacement
    return result


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
