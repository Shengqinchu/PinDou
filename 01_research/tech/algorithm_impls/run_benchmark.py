#!/usr/bin/env python3
"""Run the 12 representative PinDou quantization combinations."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.append(str(Path(__file__).resolve().parent))
from quantize_core import load_palette, metric_values, prepare_image, quantize_image


ROOT = Path(__file__).resolve().parents[3]
INPUT_DIR = ROOT / "01_research" / "tech" / "test_inputs"
SAMPLE_DIR = ROOT / "01_research" / "tech" / "algorithm_samples"
METRICS_PATH = ROOT / "01_research" / "tech" / "algorithm_metrics.csv"


COMBOS = [
    ("C01", "kmeans", "rgb", "none"),
    ("C02", "kmeans", "ciede2000", "none"),
    ("C03", "kmeans", "ciede2000", "floyd"),
    ("C04", "median_cut", "ciede2000", "floyd"),
    ("C05", "octree", "ciede2000", "floyd"),
    ("C06", "kmeans", "ciede2000", "atkinson"),
    ("C07", "kmeans", "ciede2000", "bayer"),
    ("C08", "kmeans", "ciede2000", "riemersma"),
    ("C09", "kmeans", "cie94", "floyd"),
    ("C10", "kmeans", "cie76", "floyd"),
    ("C11", "neural", "ciede2000", "floyd"),
    ("C12", "kmeans", "ciede2000", "none"),
]

INPUTS = {
    "portrait": INPUT_DIR / "portrait_synthetic.png",
    "pet": INPUT_DIR / "pet_synthetic.png",
    "cartoon": INPUT_DIR / "cartoon_synthetic.png",
}


def label_image(image: Image.Image, label: str) -> Image.Image:
    tile = Image.new("RGB", (150, 190), "white")
    resized = image.resize((140, 140), Image.Resampling.NEAREST)
    tile.paste(resized, (5, 5))
    draw = ImageDraw.Draw(tile)
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        font = ImageFont.load_default()
    draw.multiline_text((6, 148), label, fill=(20, 20, 20), font=font, spacing=2)
    return tile


def make_compare(name: str, images: dict[str, Image.Image]) -> None:
    cols = 4
    rows = 3
    canvas = Image.new("RGB", (cols * 150, rows * 190 + 52), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    draw.text((8, 8), f"{name} - 12 algorithm combinations (100x100, MARD 24 colors)", fill=(20, 20, 20), font=font)
    for idx, combo in enumerate(COMBOS):
        combo_id, quantizer, metric, dither = combo
        tile = label_image(images[combo_id], f"{combo_id} {quantizer}\n{metric}/{dither}")
        x = (idx % cols) * 150
        y = 52 + (idx // cols) * 190
        canvas.paste(tile, (x, y))
    canvas.save(SAMPLE_DIR / f"compare_{name}.png")


def main() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    palette = load_palette()
    rows: list[dict[str, object]] = []
    for input_name, input_path in INPUTS.items():
        original = prepare_image(input_path)
        output_images: dict[str, Image.Image] = {}
        for combo_id, quantizer, metric, dither_mode in COMBOS:
            result = quantize_image(original, palette, quantizer, metric, dither_mode)
            values = metric_values(original, result.image)
            output_path = SAMPLE_DIR / f"{input_name}_{combo_id}.png"
            result.image.save(output_path)
            output_images[combo_id] = result.image
            rows.append(
                {
                    "input": input_name,
                    "combo_id": combo_id,
                    "quantizer": quantizer,
                    "metric": metric,
                    "dither": dither_mode,
                    "psnr": f"{values['psnr']:.4f}",
                    "ssim": f"{values['ssim']:.4f}",
                    "mean_ciede2000": f"{values['mean_ciede2000']:.4f}",
                    "runtime_ms": f"{result.runtime_ms:.2f}",
                    "selected_color_count": len(result.selected_codes),
                    "selected_codes": " ".join(result.selected_codes),
                    "output": str(output_path.relative_to(ROOT)).replace("\\", "/"),
                }
            )
        make_compare(input_name, output_images)
    with METRICS_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} metric rows to {METRICS_PATH}")


if __name__ == "__main__":
    main()
