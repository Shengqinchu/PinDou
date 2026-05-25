"""Post-processing rules for bead-friendly pattern grids."""

from __future__ import annotations

from collections import deque

import numpy as np
from PIL import Image

from pindou.colormap.matcher import ciede2000_distance
from pindou.colormap.matcher import nearest_color_code
from pindou.pattern.builder import ColorRef


GridCodes = list[list[str | None]]
WHITE_RGB = (255, 255, 255)
FLOOD_FILL_WHITE_DELTA_E = 15.0


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
    tolerance_delta_e: float = 8.0,
) -> tuple[Image.Image, bool]:
    rgba = image.convert("RGBA")
    corner_delta = average_corner_delta_e_to_white(rgba)
    if corner_delta >= tolerance_delta_e:
        return image, False

    arr = np.array(rgba, dtype=np.uint8)
    height, width = arr.shape[:2]
    visited = np.zeros((height, width), dtype=bool)
    queue: deque[tuple[int, int]] = deque(
        [
            (0, 0),
            (width - 1, 0),
            (0, height - 1),
            (width - 1, height - 1),
        ]
    )

    while queue:
        x, y = queue.popleft()
        if visited[y, x]:
            continue
        visited[y, x] = True
        rgb = (int(arr[y, x, 0]), int(arr[y, x, 1]), int(arr[y, x, 2]))
        if ciede2000_distance(rgb, WHITE_RGB) >= FLOOD_FILL_WHITE_DELTA_E:
            continue
        arr[y, x, 3] = 0
        for next_x, next_y in pixel_neighbors(x, y, width, height):
            if not visited[next_y, next_x]:
                queue.append((next_x, next_y))

    return Image.fromarray(arr), True


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
