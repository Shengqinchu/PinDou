#!/usr/bin/env python3
"""Build the Phase 0 full bead brand-size palette database.

The generated JSON files keep Task D's row shape and add the required
`bead_diameter_mm` field. Public sources do not expose uniform official
HEX, stock, and pricing data, so per-row notes preserve source confidence.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

from build_colormap import ciede2000, color_category, hex_to_rgb, rgb_to_lab


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "01_research" / "colormap"
CAPTURED_AT = "2026-05-24"
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

GET_COLORS_SOURCE = OUT_DIR / "_source_get-colors.json"


@dataclass(frozen=True)
class PriceHint:
    price_per_100g: float | None
    price_per_1000pcs: float | None
    confidence: str
    notes: str


@dataclass(frozen=True)
class PaletteSpec:
    filename: str
    title: str
    brand: str
    bead_diameter_mm: float
    rows: list[dict[str, object]]


SOURCE_LINKS: dict[str, list[dict[str, str]]] = {
    "mard": [
        {
            "platform": "Gitea",
            "url": "https://git.xiongxiao.me/abearxiong/get-colors-from-beans",
            "shop_name": "abearxiong/get-colors-from-beans",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "Pixel Pattern",
            "url": "https://www.pixel-pattern.com/color-converter",
            "shop_name": "Pixel Pattern MARD color reference",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "拼豆工具站",
            "url": "https://www.pindou.online/colors",
            "shop_name": "Mard public palette reference",
            "captured_at": CAPTURED_AT,
        },
    ],
    "mard_2_6": [
        {
            "platform": "Gitea",
            "url": "https://git.xiongxiao.me/abearxiong/get-colors-from-beans",
            "shop_name": "abearxiong/get-colors-from-beans",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "Artkalbeads/Ukenn",
            "url": "https://artkalbeads.com/artkal_beads/527.html",
            "shop_name": "Mard 221 colors 2.6mm product evidence",
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
            "platform": "拼豆大师 App Store",
            "url": "https://apps.apple.com/nz/app/%E6%8B%BC%E8%B1%86%E5%A4%A7%E5%B8%88/id6760127746",
            "shop_name": "COCO palette support statement",
            "captured_at": CAPTURED_AT,
        },
    ],
    "hama": [
        {
            "platform": "Hama official",
            "url": "https://hama.dk/en/pages/the-foundation-stones-of-hama",
            "shop_name": "Hama bead size and range overview",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "Hama official",
            "url": "https://www.hama.dk/en/hama-info/colour-chart/",
            "shop_name": "Hama colour chart overview",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "Bitbead",
            "url": "https://bitbead.pomodiary.com/en/colors/hama",
            "shop_name": "Bitbead Hama HEX reference",
            "captured_at": CAPTURED_AT,
        },
    ],
    "perler": [
        {
            "platform": "Perler official",
            "url": "https://perler.com/products/1-000-perler-beads-white",
            "shop_name": "Perler 1,000ct 5mm sample SKU",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "Perler official",
            "url": "https://perler.com/content/downloads/perler-bead-color-reference-jan2020.pdf",
            "shop_name": "Perler bead color reference guide",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "Bitbead",
            "url": "https://bitbead.pomodiary.com/en/colors/perler",
            "shop_name": "Bitbead Perler HEX reference",
            "captured_at": CAPTURED_AT,
        },
    ],
    "artkal": [
        {
            "platform": "Artkal official",
            "url": "https://www.artkalfusebeads.com/blogs/faq/artkal-beads-size",
            "shop_name": "Artkal series and bead size overview",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "Artkal official",
            "url": "https://www.artkalfusebeads.com/collections/mini-c-2-6mm-artkal-beads/artkal-beads",
            "shop_name": "Artkal C/M mini 2.6mm collection",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "Pixel Pattern",
            "url": "https://www.pixel-pattern.com/color-converter",
            "shop_name": "Pixel Pattern Artkal public table",
            "captured_at": CAPTURED_AT,
        },
        {
            "platform": "Bitbead",
            "url": "https://bitbead.pomodiary.com/en/colors/artkal-mini",
            "shop_name": "Bitbead Artkal Mini HEX reference",
            "captured_at": CAPTURED_AT,
        },
    ],
    "other_domestic": [
        {
            "platform": "Gitea",
            "url": "https://git.xiongxiao.me/abearxiong/get-colors-from-beans",
            "shop_name": "abearxiong/get-colors-from-beans",
            "captured_at": CAPTURED_AT,
        }
    ],
}

PRICE_HINTS: dict[tuple[str, float], PriceHint] = {
    ("MARD", 5.0): PriceHint(
        10.8,
        1.08,
        "low",
        "CNY estimate from public 221-color set benchmark; not a live SKU quote.",
    ),
    ("COCO", 5.0): PriceHint(
        12.0,
        1.20,
        "low",
        "CNY same-class estimate; no stable public single-color SKU captured.",
    ),
    ("Hama", 2.5): PriceHint(
        None,
        1.40,
        "medium",
        "EUR benchmark: official Mini sample 2,000-bead bag at 2.80 EUR.",
    ),
    ("Hama", 5.0): PriceHint(
        None,
        2.50,
        "medium",
        "EUR benchmark: official Midi 1,000-bead bag sample at 2.50 EUR.",
    ),
    ("Hama", 10.0): PriceHint(
        None,
        None,
        "missing",
        "Official pages confirm Maxi range and 10mm size; no normalized per-1000 sample in current schema.",
    ),
    ("Perler", 5.0): PriceHint(
        None,
        3.69,
        "medium",
        "USD benchmark: official 1,000ct classic bead sample at 3.69 USD.",
    ),
}


def normalize_hex(hex_color: str) -> str:
    clean = hex_color.strip().lstrip("#")
    if len(clean) != 6:
        raise ValueError(f"Unsupported HEX color: {hex_color!r}")
    return f"#{clean.upper()}"


def natural_key(code: str) -> list[object]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", code)]


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HTTP_HEADERS, timeout=45)
    response.raise_for_status()
    return response.text


def load_get_colors() -> dict[str, list[dict[str, str]]]:
    return json.loads(GET_COLORS_SOURCE.read_text(encoding="utf-8"))


def split_display_name(name: str) -> tuple[str, str]:
    if "/" in name:
        left, right = [part.strip() for part in name.split("/", 1)]
        return left, right
    return name, name


def build_row(
    *,
    brand: str,
    bead_diameter_mm: float,
    code: str,
    name_cn: str,
    name_en: str,
    hex_color: str,
    stock_status: str,
    price: PriceHint,
    buy_links: list[dict[str, str]],
    notes: str,
    verified_sources: list[str],
) -> dict[str, object]:
    hex_norm = normalize_hex(hex_color)
    rgb = hex_to_rgb(hex_norm)
    lab = rgb_to_lab(rgb)
    return {
        "brand": brand,
        "bead_diameter_mm": bead_diameter_mm,
        "code": code,
        "name_cn": name_cn,
        "name_en": name_en,
        "hex": hex_norm,
        "rgb": list(rgb),
        "lab": [round(v, 4) for v in lab],
        "category": color_category(rgb),
        "stock_status": stock_status,
        "price_per_100g": price.price_per_100g,
        "price_per_1000pcs": price.price_per_1000pcs,
        "price_confidence": price.confidence,
        "buy_links": buy_links,
        "notes": f"{notes} Price note: {price.notes}",
        "verified_sources": verified_sources,
    }


def parse_bitbead_palette(slug: str, brand_label: str) -> list[dict[str, str]]:
    html = fetch_html(f"https://bitbead.pomodiary.com/en/colors/{slug}")
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    href_re = re.compile(rf"/en/colors/{re.escape(slug)}/")
    for anchor in soup.find_all("a", href=href_re):
        href = anchor.get("href", "")
        code = href.rsplit("/", 1)[-1].strip()
        if not code or code in seen:
            continue
        swatch = anchor.find(style=re.compile(r"background:\s*#[0-9A-Fa-f]{6}", re.I))
        if swatch is None:
            continue
        match = re.search(r"background:\s*(#[0-9A-Fa-f]{6})", swatch.get("style", ""))
        if match is None:
            continue
        parts = [part.strip() for part in anchor.stripped_strings if part.strip() and part.strip() != "·"]
        name = code
        if len(parts) >= 4:
            name = parts[2]
        elif len(parts) >= 3 and parts[1].lower().startswith(brand_label.lower()):
            name = parts[2]
        rows.append({"code": code, "name": name, "hex": match.group(1)})
        seen.add(code)
    return sorted(rows, key=lambda row: natural_key(row["code"]))


def parse_pixel_pattern_tables() -> dict[str, list[dict[str, str]]]:
    html = fetch_html("https://www.pixel-pattern.com/color-converter")
    soup = BeautifulSoup(html, "html.parser")
    tables: dict[str, list[dict[str, str]]] = {}
    for table in soup.find_all("table"):
        text = " ".join(table.stripped_strings)[:120]
        key = None
        if "Artkal bead color chart" in text:
            key = "artkal"
        elif "Perler bead color chart" in text:
            key = "perler"
        elif "MARD bead color chart" in text:
            key = "mard"
        elif "Hama bead color chart" in text:
            key = "hama"
        if key is None:
            continue
        rows: list[dict[str, str]] = []
        for tr in table.find_all("tr")[1:]:
            cols = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"])]
            if len(cols) < 4:
                continue
            code, name, hex_color, rgb = cols[:4]
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", hex_color):
                continue
            rows.append({"code": code, "name": name, "hex": hex_color, "rgb": rgb})
        tables[key] = sorted(rows, key=lambda row: natural_key(row["code"]))
    return tables


def source_codes(data: dict[str, list[dict[str, str]]], title: str | None) -> set[str]:
    if title is None:
        return set()
    return {row["color-name"].strip() for row in data.get(title, [])}


def build_from_getcolors(
    *,
    data: dict[str, list[dict[str, str]]],
    title: str,
    brand: str,
    bead_diameter_mm: float,
    common_title: str | None,
    name_map: dict[str, str],
    price: PriceHint,
    buy_links: list[dict[str, str]],
    notes: str,
    verified_sources: list[str],
) -> list[dict[str, object]]:
    common_codes = source_codes(data, common_title)
    seen: set[str] = set()
    rows: list[dict[str, object]] = []
    for item in data[title]:
        code = item["color-name"].strip()
        if code in seen:
            continue
        seen.add(code)
        name = name_map.get(code, f"{brand} {code}")
        stock = "common" if common_codes and code in common_codes else "rare" if common_codes else "common"
        rows.append(
            build_row(
                brand=brand,
                bead_diameter_mm=bead_diameter_mm,
                code=code,
                name_cn=name,
                name_en=name,
                hex_color=item["color"],
                stock_status=stock,
                price=price,
                buy_links=buy_links,
                notes=notes,
                verified_sources=verified_sources,
            )
        )
    return sorted(rows, key=lambda row: natural_key(str(row["code"])))


def build_from_simple_rows(
    *,
    rows: Iterable[dict[str, str]],
    brand: str,
    bead_diameter_mm: float,
    price: PriceHint,
    buy_links: list[dict[str, str]],
    notes: str,
    verified_sources: list[str],
    rare_prefixes: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in rows:
        code = item["code"].strip()
        if code in seen:
            continue
        seen.add(code)
        name_cn, name_en = split_display_name(item.get("name", code).strip())
        stock = "rare" if rare_prefixes and code.startswith(rare_prefixes) else "common"
        result.append(
            build_row(
                brand=brand,
                bead_diameter_mm=bead_diameter_mm,
                code=code,
                name_cn=name_cn,
                name_en=name_en,
                hex_color=item["hex"],
                stock_status=stock,
                price=price,
                buy_links=buy_links,
                notes=notes,
                verified_sources=verified_sources,
            )
        )
    return sorted(result, key=lambda row: natural_key(str(row["code"])))


def empty_palette_notice(brand: str, bead_diameter_mm: float, reason: str) -> list[dict[str, object]]:
    # Empty arrays keep per-color JSON clean; README records the missing brand-size reason.
    _ = (brand, bead_diameter_mm, reason)
    return []


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def draw_palette(path: Path, rows: list[dict[str, object]], title: str) -> None:
    swatch = 50
    label_h = 18
    pad = 18
    cols = 18
    if not rows:
        image = Image.new("RGB", (820, 180), "white")
        draw = ImageDraw.Draw(image)
        try:
            title_font = ImageFont.truetype("arial.ttf", 18)
            font = ImageFont.truetype("arial.ttf", 13)
        except OSError:
            title_font = ImageFont.load_default()
            font = ImageFont.load_default()
        draw.text((pad, pad), title, fill=(30, 30, 30), font=title_font)
        draw.text(
            (pad, pad + 42),
            "No reliable public per-color palette data confirmed for this brand-size combination.",
            fill=(90, 90, 90),
            font=font,
        )
        image.save(path)
        return

    ordered = sorted(rows, key=lambda row: (str(row["category"]), natural_key(str(row["code"]))))
    rows_count = (len(ordered) + cols - 1) // cols
    width = cols * swatch + pad * 2
    height = rows_count * (swatch + label_h) + pad * 3 + 32
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 10)
        title_font = ImageFont.truetype("arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()
    draw.text((pad, pad), title, fill=(30, 30, 30), font=title_font)
    y0 = pad * 2 + 28
    for idx, row in enumerate(ordered):
        col = idx % cols
        line = idx // cols
        x = pad + col * swatch
        y = y0 + line * (swatch + label_h)
        rgb = tuple(row["rgb"])  # type: ignore[arg-type]
        draw.rectangle([x, y, x + swatch - 6, y + swatch - 6], fill=rgb, outline=(210, 210, 210))
        draw.text((x, y + swatch - 4), str(row["code"])[:8], fill=(20, 20, 20), font=font)
    image.save(path)


def write_crossref(palettes: list[PaletteSpec], path: Path) -> int:
    by_diameter: dict[float, list[dict[str, object]]] = {}
    for spec in palettes:
        by_diameter.setdefault(spec.bead_diameter_mm, []).extend(spec.rows)

    count = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "source_brand",
                "source_diameter",
                "source_code",
                "target_brand",
                "target_code",
                "ciede2000",
                "rank",
            ]
        )
        for diameter, rows in sorted(by_diameter.items()):
            for src in rows:
                distances: list[tuple[float, dict[str, object]]] = []
                src_lab = tuple(src["lab"])  # type: ignore[arg-type]
                for target in rows:
                    if target["brand"] == src["brand"]:
                        continue
                    target_lab = tuple(target["lab"])  # type: ignore[arg-type]
                    distances.append((ciede2000(src_lab, target_lab), target))
                distances.sort(key=lambda item: item[0])
                for rank, (distance, target) in enumerate(distances[:3], start=1):
                    writer.writerow(
                        [
                            src["brand"],
                            f"{diameter:g}",
                            src["code"],
                            target["brand"],
                            target["code"],
                            f"{distance:.4f}",
                            rank,
                        ]
                    )
                    count += 1
    return count


def build_palettes() -> list[PaletteSpec]:
    get_colors = load_get_colors()
    pixel_tables = parse_pixel_pattern_tables()
    mard_names = {row["code"]: row["name"] for row in pixel_tables.get("mard", [])}

    hama_rows = parse_bitbead_palette("hama", "Hama")
    perler_rows = parse_bitbead_palette("perler", "Perler")
    artkal_mini_rows = parse_bitbead_palette("artkal-mini", "Artkal Mini")
    artkal_all_pixel = pixel_tables.get("artkal", [])
    artkal_5_rows = [row for row in artkal_all_pixel if str(row["code"]).startswith("S")]

    other_specs = [
        ("other_huangdoudou_5mm.json", "黄豆豆", "黄豆豆-291"),
        ("other_mixiaowo_5mm.json", "咪小窝", "咪小窝-290"),
        ("other_panpan_5mm.json", "盼盼", "盼盼-289"),
    ]

    palettes: list[PaletteSpec] = []

    palettes.append(
        PaletteSpec(
            "mard_5mm.json",
            "MARD 5mm 291 palette",
            "MARD",
            5.0,
            build_from_getcolors(
                data=get_colors,
                title="Mard-291",
                brand="MARD",
                bead_diameter_mm=5.0,
                common_title="Mard-221",
                name_map=mard_names,
                price=PRICE_HINTS[("MARD", 5.0)],
                buy_links=SOURCE_LINKS["mard"],
                notes=(
                    "5mm production default inherited from Task D. HEX is public tool extraction; "
                    "official color names still need physical card verification."
                ),
                verified_sources=["get-colors-from-beans", "Pixel Pattern", "pindou.online colors"],
            ),
        )
    )
    palettes.append(
        PaletteSpec(
            "mard_2_6mm.json",
            "MARD 2.6mm 221 palette",
            "MARD",
            2.6,
            build_from_getcolors(
                data=get_colors,
                title="Mard-221",
                brand="MARD",
                bead_diameter_mm=2.6,
                common_title="Mard-221",
                name_map=mard_names,
                price=PriceHint(None, None, "missing", "2.6mm SKU price not stable in public sources."),
                buy_links=SOURCE_LINKS["mard_2_6"],
                notes=(
                    "Public product evidence confirms MARD 221 colors at 2.6mm; no reliable public "
                    "MARD 291 mini SKU coverage found."
                ),
                verified_sources=["get-colors-from-beans", "Artkalbeads/Ukenn product page"],
            ),
        )
    )
    palettes.append(
        PaletteSpec(
            "mard_10mm.json",
            "MARD 10mm palette",
            "MARD",
            10.0,
            empty_palette_notice("MARD", 10.0, "No reliable public MARD 10mm per-color palette found."),
        )
    )

    palettes.append(
        PaletteSpec(
            "coco_5mm.json",
            "COCO 5mm 291 palette",
            "COCO",
            5.0,
            build_from_getcolors(
                data=get_colors,
                title="COCO-291",
                brand="COCO",
                bead_diameter_mm=5.0,
                common_title="COCO-221",
                name_map={},
                price=PRICE_HINTS[("COCO", 5.0)],
                buy_links=SOURCE_LINKS["coco"],
                notes=(
                    "COCO 291 inherited from Task D public extraction. Complete official HEX source "
                    "not found; needs physical or authorized card verification."
                ),
                verified_sources=["get-colors-from-beans", "public tool/app support statements"],
            ),
        )
    )
    palettes.append(
        PaletteSpec(
            "coco_2_6mm.json",
            "COCO 2.6mm 291 palette",
            "COCO",
            2.6,
            build_from_getcolors(
                data=get_colors,
                title="COCO-291",
                brand="COCO",
                bead_diameter_mm=2.6,
                common_title="COCO-221",
                name_map={},
                price=PriceHint(None, None, "missing", "2.6mm COCO SKU price not stable in public sources."),
                buy_links=SOURCE_LINKS["coco"],
                notes=(
                    "Public mentions indicate COCO/MARD-compatible 2.6mm market availability, but "
                    "complete official per-color mini SKU coverage was not found."
                ),
                verified_sources=["get-colors-from-beans", "public COCO palette mentions"],
            ),
        )
    )
    palettes.append(
        PaletteSpec(
            "coco_10mm.json",
            "COCO 10mm palette",
            "COCO",
            10.0,
            empty_palette_notice("COCO", 10.0, "No reliable public COCO 10mm per-color palette found."),
        )
    )

    for filename, title, diameter, price in [
        ("hama_2_5mm.json", "Hama Mini 2.5mm colour-system palette", 2.5, PRICE_HINTS[("Hama", 2.5)]),
        ("hama_5mm.json", "Hama Midi 5mm 89 palette", 5.0, PRICE_HINTS[("Hama", 5.0)]),
        ("hama_10mm.json", "Hama Maxi 10mm colour-system palette", 10.0, PRICE_HINTS[("Hama", 10.0)]),
    ]:
        palettes.append(
            PaletteSpec(
                filename,
                title,
                "Hama",
                diameter,
                build_from_simple_rows(
                    rows=hama_rows,
                    brand="Hama",
                    bead_diameter_mm=diameter,
                    price=price,
                    buy_links=SOURCE_LINKS["hama"],
                    notes=(
                        "Hama official sources confirm Mini/Midi/Maxi sizes and shared colour codes; "
                        "HEX values are third-party approximations. Per-diameter product availability "
                        "needs official PDF/SKU extraction before production ordering."
                    ),
                    verified_sources=["Hama official size/colour-code pages", "Bitbead Hama HEX reference"],
                    rare_prefixes=("H101", "H102", "H103", "H104", "H105", "H106", "H107", "H108", "H109"),
                ),
            )
        )

    palettes.append(
        PaletteSpec(
            "perler_5mm.json",
            "Perler 5mm 117 palette",
            "Perler",
            5.0,
            build_from_simple_rows(
                rows=perler_rows,
                brand="Perler",
                bead_diameter_mm=5.0,
                price=PRICE_HINTS[("Perler", 5.0)],
                buy_links=SOURCE_LINKS["perler"],
                notes=(
                    "Perler official pages confirm 5mm classic size and sample SKU prices. "
                    "Bitbead provides normalized P-codes and HEX; official SKU/HEX crosswalk remains incomplete."
                ),
                verified_sources=["Perler official product/color reference pages", "Bitbead Perler HEX reference"],
                rare_prefixes=("P100", "P200", "P300", "P900"),
            ),
        )
    )

    palettes.append(
        PaletteSpec(
            "artkal_2_6mm.json",
            "Artkal M Mini 2.6mm 221 palette",
            "Artkal",
            2.6,
            build_from_simple_rows(
                rows=artkal_mini_rows,
                brand="Artkal",
                bead_diameter_mm=2.6,
                price=PriceHint(None, None, "missing", "Artkal mini price varies by region/SKU; no stable benchmark set."),
                buy_links=SOURCE_LINKS["artkal"],
                notes=(
                    "Artkal official pages confirm 2.6mm mini series. Bitbead Artkal Mini rows are "
                    "used as structured HEX/name reference for the M-series colour set."
                ),
                verified_sources=["Artkal official mini pages", "Bitbead Artkal Mini HEX reference"],
            ),
        )
    )
    palettes.append(
        PaletteSpec(
            "artkal_5mm.json",
            "Artkal S 5mm public palette",
            "Artkal",
            5.0,
            build_from_simple_rows(
                rows=artkal_5_rows,
                brand="Artkal",
                bead_diameter_mm=5.0,
                price=PriceHint(None, None, "missing", "Artkal 5mm price varies by region/SKU; no stable benchmark set."),
                buy_links=SOURCE_LINKS["artkal"],
                notes=(
                    "Artkal official pages confirm S/R 5mm ranges but current public counts conflict by page. "
                    "Pixel Pattern structured S-prefixed rows are used for Phase 0 same-diameter matching."
                ),
                verified_sources=["Artkal official series pages", "Pixel Pattern Artkal table"],
                rare_prefixes=("SE", "SP", "ST", "SL", "SN", "SG"),
            ),
        )
    )
    palettes.append(
        PaletteSpec(
            "artkal_10mm.json",
            "Artkal X 10mm palette",
            "Artkal",
            10.0,
            empty_palette_notice("Artkal", 10.0, "Official X 10mm range exists, but no structured public HEX table found."),
        )
    )

    for filename, brand, title in other_specs:
        palettes.append(
            PaletteSpec(
                filename,
                f"{brand} 5mm public palette",
                brand,
                5.0,
                build_from_getcolors(
                    data=get_colors,
                    title=title,
                    brand=brand,
                    bead_diameter_mm=5.0,
                    common_title=None,
                    name_map={},
                    price=PriceHint(None, None, "missing", "Other domestic brand price/SKU not reliably captured."),
                    buy_links=SOURCE_LINKS["other_domestic"],
                    notes=(
                        "Other domestic public palette from get-colors-from-beans. Brand ownership, "
                        "official status, physical diameter, and SKU availability need manual verification."
                    ),
                    verified_sources=["get-colors-from-beans"],
                ),
            )
        )

    return palettes


def main() -> None:
    palettes = build_palettes()
    for spec in palettes:
        path = OUT_DIR / spec.filename
        write_json(path, spec.rows)
        palette_path = OUT_DIR / spec.filename.replace(".json", "_palette.png")
        draw_palette(palette_path, spec.rows, spec.title)
    crossref_count = write_crossref(palettes, OUT_DIR / "crossref_full.csv")
    nonempty = sum(1 for spec in palettes if spec.rows)
    total_colors = sum(len(spec.rows) for spec in palettes)
    print(
        f"Built {len(palettes)} brand-size files, {nonempty} non-empty palettes, "
        f"{total_colors} color rows, {crossref_count} crossref rows"
    )


if __name__ == "__main__":
    main()
