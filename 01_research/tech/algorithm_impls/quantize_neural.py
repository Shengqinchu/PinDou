#!/usr/bin/env python3
"""Standalone neural-gas-style color quantizer + MARD palette mapper."""

from __future__ import annotations

import argparse
from pathlib import Path

from quantize_core import load_palette, prepare_image, quantize_image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--metric", default="ciede2000", choices=["rgb", "cie76", "cie94", "ciede2000"])
    parser.add_argument("--dither", default="floyd", choices=["none", "floyd", "atkinson", "bayer", "riemersma"])
    args = parser.parse_args()
    result = quantize_image(prepare_image(Path(args.input)), load_palette(), "neural", args.metric, args.dither)
    result.image.save(args.output)


if __name__ == "__main__":
    main()
