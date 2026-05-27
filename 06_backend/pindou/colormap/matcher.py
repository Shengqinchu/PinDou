"""Color matching helpers."""

import numpy as np

from pindou.pattern.builder import ColorRef
from pindou.pattern.quantize_core import delta_e_ciede2000, rgb_to_lab


def ciede2000_distance(rgb_a: tuple[int, int, int], rgb_b: tuple[int, int, int]) -> float:
    arr_a = np.array(rgb_a, dtype=np.float64).reshape(1, 1, 3)
    arr_b = np.array(rgb_b, dtype=np.float64).reshape(1, 1, 3)
    lab_a = rgb_to_lab(arr_a).reshape(1, 3)
    lab_b = rgb_to_lab(arr_b).reshape(1, 3)
    return float(delta_e_ciede2000(lab_a, lab_b)[0])


def nearest_color(rgb: tuple[int, int, int], palette: list[ColorRef] | tuple[ColorRef, ...]) -> ColorRef:
    if not palette:
        raise ValueError("Palette cannot be empty.")
    rgb_arr = np.array(rgb, dtype=np.float64).reshape(1, 1, 3)
    palette_rgb = np.array([color.rgb for color in palette], dtype=np.float64)
    target_lab = rgb_to_lab(rgb_arr).reshape(1, 3)
    palette_lab = rgb_to_lab(palette_rgb.reshape(-1, 1, 3)).reshape(-1, 3)
    distances = delta_e_ciede2000(target_lab[:, None, :], palette_lab[None, :, :])
    return palette[int(np.argmin(distances[0]))]


def nearest_color_code(
    rgb: tuple[int, int, int],
    candidates: list[ColorRef] | tuple[ColorRef, ...],
) -> str:
    return nearest_color(rgb, candidates).code
