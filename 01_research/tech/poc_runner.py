#!/usr/bin/env python3
"""PinDou Task C API PoC runner.

The runner intentionally reads API keys only from .env / environment variables
and never prints key values.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import shutil
import sys
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter

sys.path.append(str(Path(__file__).resolve().parent / "algorithm_impls"))
from quantize_core import load_palette, metric_values, prepare_image, quantize_image


ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = ROOT / "01_research" / "tech" / "test_inputs_poc"
SAMPLE_DIR = ROOT / "01_research" / "tech" / "poc_samples"
RESULTS_CSV = ROOT / "01_research" / "tech" / "poc_results.csv"
VOTE_TEMPLATE = ROOT / "01_research" / "tech" / "subjective_vote_template.csv"

STYLE_PROMPTS = {
    "realistic_portrait": (
        "preserve exact facial features, identity, expression, and proportions of the input person. "
        "only change the rendering style to clean N-bit pixel art suitable for perler bead patterns. "
        "do not alter face shape, eye spacing, nose, mouth shape, or skin tone. "
        "plain background, centered subject, 1024x1024."
    ),
    "chibi_portrait": (
        "chibi cute cartoon version of the input person, big head, simplified features, "
        "N-bit pixel art style. preserve hair color, skin tone, and general identity hints, "
        "but allow stylized exaggeration. plain background, 1024x1024."
    ),
    "pet": (
        "turn the pet in the input image into clean pixel art suitable for perler bead patterns. "
        "preserve species, fur color blocks, eye shape, nose position, and distinctive markings. "
        "plain background, 1024x1024."
    ),
    "cartoon": (
        "convert the image into bold readable pixel art suitable for perler bead patterns. "
        "preserve the main silhouette and color identity, simplify small details, plain background, 1024x1024."
    ),
}


def load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def gradient(size: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", (size, size))
    pix = image.load()
    for y in range(size):
        t = y / (size - 1)
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        for x in range(size):
            pix[x, y] = color
    return image


def draw_face(seed: int, glasses: bool = False, side: bool = False) -> Image.Image:
    hue = seed * 23
    bg1 = ((210 + hue) % 255, 232, 245)
    bg2 = (248, (224 + hue) % 255, 214)
    img = gradient(1024, bg1, bg2)
    d = ImageDraw.Draw(img)
    skin = [(238, 186, 148), (226, 166, 126), (196, 130, 92), (246, 204, 166)][seed % 4]
    hair = [(54, 38, 32), (84, 54, 34), (30, 28, 32), (130, 78, 45)][seed % 4]
    if side:
        d.ellipse([310, 150, 766, 838], fill=skin, outline=(140, 90, 70), width=6)
        d.pieslice([292, 70, 770, 486], 180, 360, fill=hair)
        d.ellipse([604, 404, 690, 482], fill=(45, 38, 34))
        d.line([642, 494, 706, 560, 632, 576], fill=(150, 92, 75), width=8)
        d.arc([516, 620, 704, 726], 20, 145, fill=(145, 54, 66), width=12)
    else:
        d.ellipse([262, 136, 762, 840], fill=skin, outline=(145, 96, 76), width=6)
        d.pieslice([236, 72, 788, 476], 180, 360, fill=hair)
        d.rectangle([306, 116, 718, 310], fill=hair)
        for x in (386, 636):
            d.ellipse([x - 44, 386, x + 44, 468], fill=(45, 38, 34))
            d.ellipse([x - 12, 410, x + 12, 434], fill=(245, 245, 245))
        d.line([512, 448, 486, 560, 540, 560], fill=(150, 92, 75), width=8)
        d.arc([404, 596, 620, 712], 10, 170, fill=(145, 54, 66), width=12)
        if glasses:
            d.rounded_rectangle([326, 368, 458, 488], radius=28, outline=(20, 28, 36), width=8)
            d.rounded_rectangle([566, 368, 698, 488], radius=28, outline=(20, 28, 36), width=8)
            d.line([458, 430, 566, 430], fill=(20, 28, 36), width=8)
    d.rounded_rectangle([330, 770, 694, 1024], radius=92, fill=((60 + hue) % 255, 124, 188))
    return img.filter(ImageFilter.UnsharpMask(radius=1.1, percent=70))


def draw_pet(seed: int) -> Image.Image:
    img = gradient(1024, (232, 245, 229), (255, 245, 218))
    d = ImageDraw.Draw(img)
    fur = [(204, 134, 78), (225, 220, 205), (48, 48, 52), (148, 96, 64), (210, 170, 100)][seed % 5]
    d.ellipse([214, 222, 810, 860], fill=fur, outline=(92, 62, 42), width=8)
    d.polygon([(270, 300), (158, 104), (424, 230)], fill=fur, outline=(92, 62, 42))
    d.polygon([(754, 300), (866, 104), (600, 230)], fill=fur, outline=(92, 62, 42))
    d.ellipse([338, 432, 444, 526], fill=(35, 35, 35))
    d.ellipse([580, 432, 686, 526], fill=(35, 35, 35))
    d.polygon([(512, 548), (454, 610), (570, 610)], fill=(80, 48, 42))
    d.line([512, 610, 512, 690], fill=(80, 48, 42), width=8)
    d.arc([396, 630, 512, 736], 0, 120, fill=(80, 48, 42), width=8)
    d.arc([512, 630, 628, 736], 60, 180, fill=(80, 48, 42), width=8)
    if seed % 2:
        d.ellipse([450, 260, 610, 420], fill=(255, 255, 245))
    return img


def make_inputs() -> None:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    for i in range(5):
        draw_face(i, glasses=(i == 2), side=(i == 1)).save(INPUT_DIR / f"portrait_{i+1:02d}.png")
        draw_pet(i).save(INPUT_DIR / f"pet_{i+1:02d}.png")
    for i in range(5):
        canvas = Image.new("RGB", (1024, 1024), (232, 238, 248))
        left = draw_face(i).resize((520, 520), Image.Resampling.LANCZOS)
        right = draw_face(i + 2, glasses=(i % 2 == 0)).resize((520, 520), Image.Resampling.LANCZOS)
        canvas.paste(left, (40, 270))
        canvas.paste(right, (464, 270))
        ImageDraw.Draw(canvas).rounded_rectangle([210, 780, 814, 1024], radius=90, fill=(118, 86, 166))
        canvas.save(INPUT_DIR / f"couple_{i+1:02d}.png")
    print(f"Wrote synthetic PoC inputs to {INPUT_DIR}")


def write_vote_template() -> None:
    rows = []
    for subject in [f"voter_{i}" for i in range(1, 6)]:
        for image_path in sorted(SAMPLE_DIR.glob("*/*_quantized.png")):
            rows.append(
                {
                    "voter_id": subject,
                    "sample_id": image_path.stem,
                    "score_1_5": "",
                    "is_worth_paid": "",
                    "notes": "",
                }
            )
    if not rows:
        rows = [
            {
                "voter_id": "voter_1",
                "sample_id": "P1_realistic_portrait_01_quantized",
                "score_1_5": "",
                "is_worth_paid": "",
                "notes": "Fill after API samples are generated.",
            }
        ]
    with VOTE_TEMPLATE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote vote template to {VOTE_TEMPLATE}")


def provider1_edit(image_path: Path, prompt: str) -> Image.Image:
    base_url = os.environ.get("XIAOCHI_GPT_BASE_URL", "https://gpt.xiaochisaascn.org/v1").rstrip("/")
    key = os.environ.get("XIAOCHI_GPT_API_KEY")
    if not key:
        raise RuntimeError("Missing XIAOCHI_GPT_API_KEY in .env or environment.")
    with image_path.open("rb") as image_file:
        response = requests.post(
            f"{base_url}/images/edits",
            headers={"Authorization": f"Bearer {key}"},
            files={"image": (image_path.name, image_file, "image/png")},
            data={
                "model": "gpt-image-2",
                "prompt": prompt,
                "size": "1024x1024",
                "response_format": "b64_json",
            },
            timeout=180,
        )
    response.raise_for_status()
    payload = response.json()
    item = payload["data"][0]
    if "b64_json" in item:
        return Image.open(Path(write_temp_image(item["b64_json"]))).convert("RGB")
    if "url" in item:
        content = requests.get(item["url"], timeout=60).content
        tmp = SAMPLE_DIR / "_downloaded_provider_image.png"
        tmp.write_bytes(content)
        return Image.open(tmp).convert("RGB")
    raise RuntimeError(f"Unexpected image API response keys: {list(item.keys())}")


def write_temp_image(b64: str) -> str:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    path = SAMPLE_DIR / "_provider_tmp.png"
    path.write_bytes(base64.b64decode(b64))
    return str(path)


def run_provider1(limit: int | None = None) -> None:
    load_env()
    palette = load_palette()
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    input_paths = sorted(INPUT_DIR.glob("*.png"))
    if limit:
        input_paths = input_paths[:limit]
    for input_path in input_paths:
        if input_path.name.startswith("pet"):
            styles = ["pet"]
        elif input_path.name.startswith("couple"):
            styles = ["realistic_portrait", "chibi_portrait"]
        else:
            styles = ["realistic_portrait", "chibi_portrait"]
        for style in styles:
            out_dir = SAMPLE_DIR / f"P1_{style}"
            out_dir.mkdir(parents=True, exist_ok=True)
            seq = input_path.stem.split("_")[-1]
            original_path = out_dir / f"P1_{style}_{seq}_original.png"
            ai_path = out_dir / f"P1_{style}_{seq}_ai.png"
            quant_path = out_dir / f"P1_{style}_{seq}_quantized.png"
            shutil.copyfile(input_path, original_path)
            started = time.perf_counter()
            ai_image = provider1_edit(input_path, STYLE_PROMPTS[style])
            ai_image.save(ai_path)
            prepared = prepare_image(ai_path)
            result = quantize_image(prepared, palette, "kmeans", "ciede2000", "none")
            result.image.save(quant_path)
            metrics = metric_values(prepare_image(original_path), result.image)
            rows.append(
                {
                    "provider": "P1",
                    "style": style,
                    "input": input_path.name,
                    "ai_output": str(ai_path.relative_to(ROOT)).replace("\\", "/"),
                    "quantized_output": str(quant_path.relative_to(ROOT)).replace("\\", "/"),
                    "latency_ms": f"{(time.perf_counter() - started) * 1000:.2f}",
                    "mean_ciede2000": f"{metrics['mean_ciede2000']:.4f}",
                    "ssim": f"{metrics['ssim']:.4f}",
                    "psnr": f"{metrics['psnr']:.4f}",
                }
            )
    if rows:
        with RESULTS_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} rows to {RESULTS_CSV}")
    write_vote_template()


def status() -> None:
    load_env()
    providers = {
        "P1_gpt_image_2": bool(os.environ.get("XIAOCHI_GPT_API_KEY")),
        "P2_volc_jimeng": bool(os.environ.get("VOLC_ACCESS_KEY") and os.environ.get("VOLC_SECRET_KEY")),
        "P3_tongyi_wanxiang": bool(os.environ.get("ALIYUN_DASHSCOPE_API_KEY")),
    }
    print(json.dumps(providers, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["make-inputs", "status", "run-p1", "vote-template"])
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    if args.command == "make-inputs":
        make_inputs()
    elif args.command == "status":
        status()
    elif args.command == "run-p1":
        run_provider1(limit=args.limit)
    elif args.command == "vote-template":
        write_vote_template()


if __name__ == "__main__":
    main()
