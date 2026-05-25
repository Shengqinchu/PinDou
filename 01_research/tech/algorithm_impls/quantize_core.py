#!/usr/bin/env python3
"""Shared quantization primitives for PinDou Phase 0 algorithm comparison."""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image
from sklearn.cluster import MiniBatchKMeans


ROOT = Path(__file__).resolve().parents[3]
PALETTE_PATH = ROOT / "01_research" / "colormap" / "mard.json"


@dataclass(frozen=True)
class Palette:
    codes: list[str]
    rgb: np.ndarray
    lab: np.ndarray


@dataclass(frozen=True)
class QuantizeResult:
    image: Image.Image
    selected_codes: list[str]
    runtime_ms: float


def load_palette(path: Path = PALETTE_PATH) -> Palette:
    data = json.loads(path.read_text(encoding="utf-8"))
    codes = [row["code"] for row in data]
    rgb = np.array([row["rgb"] for row in data], dtype=np.float64)
    lab = np.array([row["lab"] for row in data], dtype=np.float64)
    return Palette(codes=codes, rgb=rgb, lab=lab)


def prepare_image(path: Path, size: int = 100) -> Image.Image:
    return Image.open(path).convert("RGB").resize((size, size), Image.Resampling.LANCZOS)


def srgb_to_xyz(rgb: np.ndarray) -> np.ndarray:
    arr = rgb.astype(np.float64) / 255.0
    arr = np.where(arr <= 0.04045, arr / 12.92, ((arr + 0.055) / 1.055) ** 2.4)
    matrix = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ]
    )
    return arr @ matrix.T * 100.0


def xyz_to_lab(xyz: np.ndarray) -> np.ndarray:
    white = np.array([95.047, 100.0, 108.883])
    t = xyz / white
    f = np.where(t > 0.008856, np.cbrt(t), 7.787 * t + 16 / 116)
    l = 116 * f[:, 1] - 16
    a = 500 * (f[:, 0] - f[:, 1])
    b = 200 * (f[:, 1] - f[:, 2])
    return np.stack([l, a, b], axis=1)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    flat = rgb.reshape(-1, 3)
    return xyz_to_lab(srgb_to_xyz(flat)).reshape(rgb.shape)


def delta_e_ciede2000(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    l1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    l2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]
    c1 = np.sqrt(a1**2 + b1**2)
    c2 = np.sqrt(a2**2 + b2**2)
    c_bar = (c1 + c2) / 2
    g = 0.5 * (1 - np.sqrt((c_bar**7) / (c_bar**7 + 25**7 + 1e-12)))
    a1p = (1 + g) * a1
    a2p = (1 + g) * a2
    c1p = np.sqrt(a1p**2 + b1**2)
    c2p = np.sqrt(a2p**2 + b2**2)
    h1p = (np.degrees(np.arctan2(b1, a1p)) + 360) % 360
    h2p = (np.degrees(np.arctan2(b2, a2p)) + 360) % 360
    dl = l2 - l1
    dc = c2p - c1p
    dhp = h2p - h1p
    dhp = np.where((c1p * c2p) == 0, 0, dhp)
    dhp = np.where(dhp > 180, dhp - 360, dhp)
    dhp = np.where(dhp < -180, dhp + 360, dhp)
    dh = 2 * np.sqrt(c1p * c2p) * np.sin(np.radians(dhp / 2))
    l_bar = (l1 + l2) / 2
    cp_bar = (c1p + c2p) / 2
    hp_sum = h1p + h2p
    hp_bar = np.where(
        (c1p * c2p) == 0,
        hp_sum,
        np.where(
            np.abs(h1p - h2p) <= 180,
            hp_sum / 2,
            np.where(hp_sum < 360, (hp_sum + 360) / 2, (hp_sum - 360) / 2),
        ),
    )
    t = (
        1
        - 0.17 * np.cos(np.radians(hp_bar - 30))
        + 0.24 * np.cos(np.radians(2 * hp_bar))
        + 0.32 * np.cos(np.radians(3 * hp_bar + 6))
        - 0.20 * np.cos(np.radians(4 * hp_bar - 63))
    )
    delta_theta = 30 * np.exp(-(((hp_bar - 275) / 25) ** 2))
    rc = 2 * np.sqrt((cp_bar**7) / (cp_bar**7 + 25**7 + 1e-12))
    sl = 1 + (0.015 * ((l_bar - 50) ** 2)) / np.sqrt(20 + ((l_bar - 50) ** 2))
    sc = 1 + 0.045 * cp_bar
    sh = 1 + 0.015 * cp_bar * t
    rt = -np.sin(np.radians(2 * delta_theta)) * rc
    return np.sqrt((dl / sl) ** 2 + (dc / sc) ** 2 + (dh / sh) ** 2 + rt * (dc / sc) * (dh / sh))


def delta_e_cie94(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    dl = lab1[..., 0] - lab2[..., 0]
    c1 = np.sqrt(lab1[..., 1] ** 2 + lab1[..., 2] ** 2)
    c2 = np.sqrt(lab2[..., 1] ** 2 + lab2[..., 2] ** 2)
    dc = c1 - c2
    da = lab1[..., 1] - lab2[..., 1]
    db = lab1[..., 2] - lab2[..., 2]
    dh_sq = np.maximum(0, da**2 + db**2 - dc**2)
    return np.sqrt((dl / 1.0) ** 2 + (dc / (1 + 0.045 * c1)) ** 2 + dh_sq / ((1 + 0.015 * c1) ** 2))


def distances(points_rgb: np.ndarray, palette_rgb: np.ndarray, metric: str) -> np.ndarray:
    points = np.clip(points_rgb.reshape(-1, 3).astype(np.float64), 0, 255)
    pal = np.clip(palette_rgb.astype(np.float64), 0, 255)
    if metric == "rgb":
        return np.linalg.norm(points[:, None, :] - pal[None, :, :], axis=2)
    points_lab = rgb_to_lab(points.reshape(-1, 1, 3)).reshape(-1, 3)
    pal_lab = rgb_to_lab(pal.reshape(-1, 1, 3)).reshape(-1, 3)
    if metric == "cie76":
        return np.linalg.norm(points_lab[:, None, :] - pal_lab[None, :, :], axis=2)
    if metric == "cie94":
        return delta_e_cie94(points_lab[:, None, :], pal_lab[None, :, :])
    if metric == "ciede2000":
        return delta_e_ciede2000(points_lab[:, None, :], pal_lab[None, :, :])
    raise ValueError(f"Unknown metric: {metric}")


def nearest_indices(points_rgb: np.ndarray, palette_rgb: np.ndarray, metric: str) -> np.ndarray:
    return np.argmin(distances(points_rgb, palette_rgb, metric), axis=1)


def select_palette_colors(image_rgb: np.ndarray, palette: Palette, quantizer: str, metric: str, n_colors: int = 24) -> np.ndarray:
    pixels = image_rgb.reshape(-1, 3).astype(np.float64)
    unique_count = min(n_colors, len(np.unique(pixels.astype(np.uint8), axis=0)))
    if quantizer == "kmeans":
        model = MiniBatchKMeans(n_clusters=unique_count, random_state=24, n_init=8, batch_size=2048)
        centers = model.fit(pixels).cluster_centers_
    elif quantizer in {"median_cut", "octree"}:
        method = Image.Quantize.MEDIANCUT if quantizer == "median_cut" else Image.Quantize.FASTOCTREE
        quantized = Image.fromarray(image_rgb.astype(np.uint8)).quantize(colors=unique_count, method=method)
        raw_palette = quantized.getpalette()[: unique_count * 3]
        centers = np.array(raw_palette, dtype=np.float64).reshape(-1, 3)
    elif quantizer == "neural":
        centers = neural_gas(pixels, unique_count)
    else:
        raise ValueError(f"Unknown quantizer: {quantizer}")
    mapped = nearest_indices(centers, palette.rgb, metric)
    # Keep deterministic order while removing duplicates.
    return np.array(list(dict.fromkeys(mapped.tolist())), dtype=int)


def neural_gas(pixels: np.ndarray, n_colors: int, epochs: int = 10) -> np.ndarray:
    rng = np.random.default_rng(24)
    sample_size = min(6000, len(pixels))
    sample = pixels[rng.choice(len(pixels), size=sample_size, replace=False)].astype(np.float64)
    centers = sample[rng.choice(sample_size, size=n_colors, replace=False)].copy()
    for epoch in range(epochs):
        rate = 0.35 * (1 - epoch / epochs) + 0.03
        radius = max(0.6, n_colors * (1 - epoch / epochs) / 2)
        rng.shuffle(sample)
        for pix in sample[::2]:
            dist = np.linalg.norm(centers - pix, axis=1)
            order = np.argsort(dist)
            influence = np.exp(-np.arange(n_colors) / radius)[:, None]
            centers[order] += rate * influence * (pix - centers[order])
    return np.clip(centers, 0, 255)


def apply_no_dither(image_rgb: np.ndarray, palette_rgb: np.ndarray, metric: str) -> np.ndarray:
    idx = nearest_indices(image_rgb, palette_rgb, metric)
    return palette_rgb[idx].reshape(image_rgb.shape).astype(np.uint8)


def apply_error_diffusion(image_rgb: np.ndarray, palette_rgb: np.ndarray, metric: str, kernel: Iterable[tuple[int, int, float]]) -> np.ndarray:
    arr = image_rgb.astype(np.float64).copy()
    h, w, _ = arr.shape
    out = np.zeros_like(arr)
    for y in range(h):
        x_range = range(w) if y % 2 == 0 else range(w - 1, -1, -1)
        direction = 1 if y % 2 == 0 else -1
        for x in x_range:
            idx = nearest_indices(arr[y, x].reshape(1, 3), palette_rgb, metric)[0]
            new = palette_rgb[idx]
            out[y, x] = new
            err = arr[y, x] - new
            for dx, dy, weight in kernel:
                nx = x + dx * direction
                ny = y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    arr[ny, nx] += err * weight
    return np.clip(out, 0, 255).astype(np.uint8)


def apply_bayer(image_rgb: np.ndarray, palette_rgb: np.ndarray, metric: str) -> np.ndarray:
    matrix = np.array(
        [
            [0, 8, 2, 10],
            [12, 4, 14, 6],
            [3, 11, 1, 9],
            [15, 7, 13, 5],
        ],
        dtype=np.float64,
    )
    threshold = (matrix + 0.5) / 16 - 0.5
    arr = image_rgb.astype(np.float64).copy()
    h, w, _ = arr.shape
    for y in range(h):
        for x in range(w):
            arr[y, x] = np.clip(arr[y, x] + threshold[y % 4, x % 4] * 36, 0, 255)
    return apply_no_dither(arr, palette_rgb, metric)


def dither(image_rgb: np.ndarray, palette_rgb: np.ndarray, metric: str, mode: str) -> np.ndarray:
    if mode == "none":
        return apply_no_dither(image_rgb, palette_rgb, metric)
    if mode == "floyd":
        return apply_error_diffusion(
            image_rgb,
            palette_rgb,
            metric,
            [(1, 0, 7 / 16), (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16)],
        )
    if mode == "atkinson":
        return apply_error_diffusion(
            image_rgb,
            palette_rgb,
            metric,
            [(1, 0, 1 / 8), (2, 0, 1 / 8), (-1, 1, 1 / 8), (0, 1, 1 / 8), (1, 1, 1 / 8), (0, 2, 1 / 8)],
        )
    if mode == "bayer":
        return apply_bayer(image_rgb, palette_rgb, metric)
    if mode == "riemersma":
        return apply_error_diffusion(
            image_rgb,
            palette_rgb,
            metric,
            [(1, 0, 0.35), (1, 1, 0.20), (0, 1, 0.25), (-1, 1, 0.10)],
        )
    raise ValueError(f"Unknown dither mode: {mode}")


def quantize_image(image: Image.Image, palette: Palette, quantizer: str, metric: str, dither_mode: str, n_colors: int = 24) -> QuantizeResult:
    start = time.perf_counter()
    image_rgb = np.array(image, dtype=np.uint8)
    selected = select_palette_colors(image_rgb, palette, quantizer, metric, n_colors)
    if len(selected) < min(n_colors, 12):
        # Add nearest global palette colors to avoid degenerate tiny palettes on flat images.
        selected = np.array(list(dict.fromkeys(selected.tolist() + list(range(len(palette.codes))))))[:n_colors]
    selected_rgb = palette.rgb[selected]
    output = dither(image_rgb, selected_rgb, metric, dither_mode)
    elapsed = (time.perf_counter() - start) * 1000
    return QuantizeResult(
        image=Image.fromarray(output, "RGB"),
        selected_codes=[palette.codes[i] for i in selected],
        runtime_ms=elapsed,
    )


def metric_values(original: Image.Image, output: Image.Image) -> dict[str, float]:
    from skimage.metrics import peak_signal_noise_ratio, structural_similarity

    orig = np.array(original, dtype=np.uint8)
    out = np.array(output, dtype=np.uint8)
    psnr = peak_signal_noise_ratio(orig, out, data_range=255)
    ssim = structural_similarity(orig, out, channel_axis=2, data_range=255)
    orig_lab = rgb_to_lab(orig)
    out_lab = rgb_to_lab(out)
    delta = delta_e_ciede2000(orig_lab, out_lab)
    return {
        "psnr": float(psnr),
        "ssim": float(ssim),
        "mean_ciede2000": float(np.mean(delta)),
    }
