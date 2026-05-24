#!/usr/bin/env python3
"""Build PinDou Phase 0 palette artifacts from public color-card sources."""

from __future__ import annotations

import csv
import json
import math
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "01_research" / "colormap"
SOURCE_URL = (
    "https://git.xiongxiao.me/abearxiong/get-colors-from-beans/raw/branch/main/"
    "get-colors.json"
)
CAPTURED_AT = "2026-05-24"

SOURCE_LINKS = {
    "mard": [
        {
            "platform": "Gitea",
            "url": "https://git.xiongxiao.me/abearxiong/get-colors-from-beans",
            "shop_name": "abearxiong/get-colors-from-beans",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "Pixel Beads",
            "url": "https://www.pixel-beads.com/zh/mard-bead-color-chart",
            "shop_name": "pixel-beads MARD color chart",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "Bitbead",
            "url": "https://bitbead.pomodiary.com/colors",
            "shop_name": "Bitbead MARD palettes",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "拼豆工具站",
            "url": "https://www.pindou.online/shop",
            "shop_name": "Mard 221色标准拼豆套装",
            "captured_at": CAPTURED_AT,
        },
    ],
    "coco": [
        {
            "platform": "Gitea",
            "url": "https://git.xiongxiao.me/abearxiong/get-colors-from-beans",
            "shop_name": "abearxiong/get-colors-from-beans",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "拼豆星球",
            "url": "https://pindou.cn/",
            "shop_name": "COCO palette support statement",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "Crapark manual",
            "url": "https://pd.crapark.com/manual-tablet.html",
            "shop_name": "COCO color-card support manual",
            "captured_at": CAPTURED_AT,
        },
    ],
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    clean = hex_color.strip().lstrip("#")
    return tuple(int(clean[i : i + 2], 16) for i in (0, 2, 4))


def srgb_to_xyz(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    vals = []
    for channel in rgb:
        c = channel / 255.0
        vals.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = vals
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    return x * 100.0, y * 100.0, z * 100.0


def xyz_to_lab(xyz: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = xyz
    xr, yr, zr = x / 95.047, y / 100.0, z / 108.883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(xr), f(yr), f(zr)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def rgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    return xyz_to_lab(srgb_to_xyz(rgb))


def ciede2000(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2
    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    c_bar = (c1 + c2) / 2
    g = 0.5 * (1 - math.sqrt((c_bar**7) / (c_bar**7 + 25**7))) if c_bar else 0
    a1p = (1 + g) * a1
    a2p = (1 + g) * a2
    c1p = math.hypot(a1p, b1)
    c2p = math.hypot(a2p, b2)

    def hp(ap: float, bp: float) -> float:
        if ap == 0 and bp == 0:
            return 0.0
        angle = math.degrees(math.atan2(bp, ap))
        return angle + 360 if angle < 0 else angle

    h1p = hp(a1p, b1)
    h2p = hp(a2p, b2)
    dl = l2 - l1
    dc = c2p - c1p
    if c1p * c2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p <= h1p:
        dhp = h2p - h1p + 360
    else:
        dhp = h2p - h1p - 360
    dh = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(dhp / 2))
    l_bar = (l1 + l2) / 2
    cp_bar = (c1p + c2p) / 2
    if c1p * c2p == 0:
        hp_bar = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hp_bar = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hp_bar = (h1p + h2p + 360) / 2
    else:
        hp_bar = (h1p + h2p - 360) / 2
    t = (
        1
        - 0.17 * math.cos(math.radians(hp_bar - 30))
        + 0.24 * math.cos(math.radians(2 * hp_bar))
        + 0.32 * math.cos(math.radians(3 * hp_bar + 6))
        - 0.20 * math.cos(math.radians(4 * hp_bar - 63))
    )
    delta_theta = 30 * math.exp(-(((hp_bar - 275) / 25) ** 2))
    rc = 2 * math.sqrt((cp_bar**7) / (cp_bar**7 + 25**7)) if cp_bar else 0
    sl = 1 + (0.015 * ((l_bar - 50) ** 2)) / math.sqrt(20 + ((l_bar - 50) ** 2))
    sc = 1 + 0.045 * cp_bar
    sh = 1 + 0.015 * cp_bar * t
    rt = -math.sin(math.radians(2 * delta_theta)) * rc
    return math.sqrt(
        (dl / sl) ** 2
        + (dc / sc) ** 2
        + (dh / sh) ** 2
        + rt * (dc / sc) * (dh / sh)
    )


def color_category(rgb: tuple[int, int, int]) -> str:
    r, g, b = [v / 255 for v in rgb]
    mx, mn = max(r, g, b), min(r, g, b)
    light = (mx + mn) / 2
    if mx - mn < 0.08:
        if light > 0.9:
            return "白色系"
        if light < 0.15:
            return "黑色系"
        return "灰色系"
    if mx == r:
        hue = (60 * ((g - b) / (mx - mn)) + 360) % 360
    elif mx == g:
        hue = 60 * ((b - r) / (mx - mn)) + 120
    else:
        hue = 60 * ((r - g) / (mx - mn)) + 240
    if hue < 20 or hue >= 345:
        return "红色系"
    if hue < 45:
        return "橙色系"
    if hue < 70:
        return "黄色系"
    if hue < 165:
        return "绿色系"
    if hue < 200:
        return "青色系"
    if hue < 255:
        return "蓝色系"
    if hue < 300:
        return "紫色系"
    return "粉色系"


def load_source() -> dict[str, list[dict[str, str]]]:
    cache = OUT_DIR / "_source_get-colors.json"
    if not cache.exists():
        with urllib.request.urlopen(SOURCE_URL, timeout=30) as response:
            cache.write_bytes(response.read())
    return json.loads(cache.read_text(encoding="utf-8"))


def source_codes(data: dict[str, list[dict[str, str]]], title: str) -> set[str]:
    return {row["color-name"] for row in data.get(title, [])}


def build_palette(
    data: dict[str, list[dict[str, str]]],
    brand: str,
    full_title: str,
    common_title: str,
) -> list[dict[str, object]]:
    common_codes = source_codes(data, common_title)
    rows = []
    seen = set()
    for item in data[full_title]:
        code = item["color-name"].strip()
        if code in seen:
            continue
        seen.add(code)
        hex_color = item["color"].upper()
        rgb = hex_to_rgb(hex_color)
        lab = rgb_to_lab(rgb)
        price_per_1000 = 1.08 if brand == "MARD" else 1.20
        rows.append(
            {
                "brand": brand,
                "code": code,
                "name_cn": f"{brand} {code}",
                "name_en": f"{brand} {code}",
                "hex": hex_color,
                "rgb": list(rgb),
                "lab": [round(v, 4) for v in lab],
                "category": color_category(rgb),
                "stock_status": "common" if code in common_codes else "rare",
                "price_per_100g": round(price_per_1000 * 10, 2),
                "price_per_1000pcs": round(price_per_1000, 2),
                "price_confidence": "low",
                "buy_links": SOURCE_LINKS[brand.lower()],
                "notes": (
                    "HEX from public palette extraction; official color name not confirmed. "
                    "Price is a same-class public listing benchmark, not a live SKU quote."
                ),
                "verified_sources": [
                    "get-colors-from-beans",
                    "pixel-beads/Bitbead or public tool pages",
                ],
            }
        )
    return sorted(rows, key=lambda x: x["code"])


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_crossref(source: list[dict[str, object]], target: list[dict[str, object]], writer: csv.writer) -> None:
    for src in source:
        distances = []
        src_lab = tuple(src["lab"])  # type: ignore[arg-type]
        for tgt in target:
            tgt_lab = tuple(tgt["lab"])  # type: ignore[arg-type]
            distances.append((ciede2000(src_lab, tgt_lab), tgt))
        distances.sort(key=lambda item: item[0])
        for rank, (distance, tgt) in enumerate(distances[:3], start=1):
            writer.writerow([src["brand"], src["code"], tgt["brand"], tgt["code"], f"{distance:.4f}", rank])


def draw_palette(path: Path, rows: list[dict[str, object]], title: str) -> None:
    swatch = 54
    label_h = 18
    pad = 18
    cols = 18
    rows_count = math.ceil(len(rows) / cols)
    width = cols * swatch + pad * 2
    height = rows_count * (swatch + label_h) + pad * 3 + 32
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 11)
        title_font = ImageFont.truetype("arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()
    draw.text((pad, pad), title, fill=(30, 30, 30), font=title_font)
    y0 = pad * 2 + 28
    for idx, row in enumerate(rows):
        col = idx % cols
        line = idx // cols
        x = pad + col * swatch
        y = y0 + line * (swatch + label_h)
        rgb = tuple(row["rgb"])  # type: ignore[arg-type]
        draw.rectangle([x, y, x + swatch - 6, y + swatch - 6], fill=rgb, outline=(210, 210, 210))
        draw.text((x, y + swatch - 3), str(row["code"]), fill=(20, 20, 20), font=font)
    image.save(path)


def main() -> None:
    data = load_source()
    mard = build_palette(data, "MARD", "Mard-291", "Mard-221")
    coco = build_palette(data, "COCO", "COCO-291", "COCO-221")
    write_json(OUT_DIR / "mard.json", mard)
    write_json(OUT_DIR / "coco.json", coco)
    with (OUT_DIR / "crossref.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source_brand", "source_code", "target_brand", "target_code", "ciede2000", "rank"])
        write_crossref(mard, coco, writer)
        write_crossref(coco, mard, writer)
    draw_palette(OUT_DIR / "mard_palette.png", mard, "MARD 291 palette")
    draw_palette(OUT_DIR / "coco_palette.png", coco, "COCO 291 palette")
    print(f"Built {len(mard)} MARD colors and {len(coco)} COCO colors")


if __name__ == "__main__":
    main()
