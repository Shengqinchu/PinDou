"""Post-processing rules for bead-friendly pattern grids."""

from __future__ import annotations

from collections import deque

from pindou.colormap.matcher import nearest_color_code
from pindou.pattern.builder import ColorRef


GridCodes = list[list[str | None]]


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
