#!/usr/bin/env python3
"""Generate non-identifying synthetic test inputs for Phase 0 algorithm baselines."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "01_research" / "tech" / "test_inputs"


def gradient_background(size: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        t = y / (size - 1)
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        for x in range(size):
            px[x, y] = color
    return img


def portrait() -> Image.Image:
    img = gradient_background(1024, (230, 242, 255), (248, 236, 224))
    d = ImageDraw.Draw(img)
    d.ellipse([262, 136, 762, 840], fill=(238, 186, 148), outline=(145, 96, 76), width=6)
    d.pieslice([236, 72, 788, 476], 180, 360, fill=(62, 45, 38))
    d.rectangle([306, 116, 718, 310], fill=(62, 45, 38))
    d.ellipse([344, 382, 430, 456], fill=(48, 38, 34))
    d.ellipse([594, 382, 680, 456], fill=(48, 38, 34))
    d.ellipse([374, 406, 402, 434], fill=(245, 245, 245))
    d.ellipse([624, 406, 652, 434], fill=(245, 245, 245))
    d.line([512, 448, 486, 560, 540, 560], fill=(150, 92, 75), width=8)
    d.arc([404, 596, 620, 712], 10, 170, fill=(145, 54, 66), width=12)
    d.ellipse([220, 416, 286, 548], fill=(232, 176, 138), outline=(145, 96, 76), width=4)
    d.ellipse([738, 416, 804, 548], fill=(232, 176, 138), outline=(145, 96, 76), width=4)
    d.rounded_rectangle([330, 770, 694, 1024], radius=92, fill=(72, 124, 188))
    d.polygon([(424, 768), (600, 768), (552, 892), (472, 892)], fill=(228, 174, 140))
    return img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=80))


def pet() -> Image.Image:
    img = gradient_background(1024, (232, 245, 229), (255, 245, 218))
    d = ImageDraw.Draw(img)
    d.ellipse([214, 222, 810, 860], fill=(204, 134, 78), outline=(92, 62, 42), width=8)
    d.polygon([(270, 300), (158, 104), (424, 230)], fill=(184, 104, 62), outline=(92, 62, 42))
    d.polygon([(754, 300), (866, 104), (600, 230)], fill=(184, 104, 62), outline=(92, 62, 42))
    d.polygon([(282, 272), (210, 154), (390, 236)], fill=(244, 181, 130))
    d.polygon([(742, 272), (814, 154), (634, 236)], fill=(244, 181, 130))
    d.ellipse([338, 432, 444, 526], fill=(38, 35, 30))
    d.ellipse([580, 432, 686, 526], fill=(38, 35, 30))
    d.ellipse([376, 456, 404, 484], fill=(255, 255, 238))
    d.ellipse([618, 456, 646, 484], fill=(255, 255, 238))
    d.polygon([(512, 548), (454, 610), (570, 610)], fill=(80, 48, 42))
    d.line([512, 610, 512, 690], fill=(80, 48, 42), width=8)
    d.arc([396, 630, 512, 736], 0, 120, fill=(80, 48, 42), width=8)
    d.arc([512, 630, 628, 736], 60, 180, fill=(80, 48, 42), width=8)
    for x in (320, 704):
        d.line([x, 584, x - 150, 536], fill=(80, 48, 42), width=4)
        d.line([x, 626, x - 160, 626], fill=(80, 48, 42), width=4)
        d.line([x, 666, x - 146, 724], fill=(80, 48, 42), width=4)
    for x in (704,):
        d.line([x, 584, x + 150, 536], fill=(80, 48, 42), width=4)
        d.line([x, 626, x + 160, 626], fill=(80, 48, 42), width=4)
        d.line([x, 666, x + 146, 724], fill=(80, 48, 42), width=4)
    d.ellipse([414, 712, 610, 778], fill=(230, 154, 106))
    return img.filter(ImageFilter.GaussianBlur(0.3))


def cartoon() -> Image.Image:
    img = Image.new("RGB", (1024, 1024), (34, 39, 62))
    d = ImageDraw.Draw(img)
    for i, color in enumerate([(245, 95, 86), (255, 195, 66), (73, 190, 142), (88, 166, 255), (174, 111, 255)]):
        x0 = 80 + i * 182
        d.rounded_rectangle([x0, 90, x0 + 126, 920], radius=54, fill=color)
    d.ellipse([256, 214, 768, 726], fill=(255, 243, 117), outline=(255, 255, 255), width=10)
    d.ellipse([364, 370, 450, 456], fill=(42, 45, 65))
    d.ellipse([574, 370, 660, 456], fill=(42, 45, 65))
    d.pieslice([364, 470, 660, 722], 0, 180, fill=(244, 80, 101))
    d.rectangle([418, 471, 606, 530], fill=(255, 255, 255))
    for cx, cy in [(168, 178), (848, 216), (166, 798), (846, 820)]:
        d.regular_polygon((cx, cy, 56), 5, rotation=18, fill=(255, 255, 255))
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    portrait().save(OUT / "portrait_synthetic.png")
    pet().save(OUT / "pet_synthetic.png")
    cartoon().save(OUT / "cartoon_synthetic.png")
    print(f"Wrote synthetic test inputs to {OUT}")


if __name__ == "__main__":
    main()
