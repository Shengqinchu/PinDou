"""Pattern export helpers."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw

from pindou.pattern.builder import NoBead, PatternSheet


class PatternExporter:
    def __init__(self, cell_size: int = 10, padding: int = 12) -> None:
        self.cell_size = cell_size
        self.padding = padding

    def to_simple_grid_png(self, pattern: PatternSheet) -> bytes:
        grid = pattern.grid
        if not grid or not grid[0]:
            return empty_png()
        rows = len(grid)
        cols = max(len(row) for row in grid)
        width = cols * self.cell_size + self.padding * 2
        height = rows * self.cell_size + self.padding * 2
        image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(image)

        for row_idx, row in enumerate(grid):
            for col_idx, bead in enumerate(row):
                x0 = self.padding + col_idx * self.cell_size
                y0 = self.padding + row_idx * self.cell_size
                x1 = x0 + self.cell_size - 1
                y1 = y0 + self.cell_size - 1
                if isinstance(bead, NoBead):
                    continue
                fill = (*bead.rgb, 255)
                outline = darken(bead.rgb, factor=0.65)
                draw.ellipse([x0 + 1, y0 + 1, x1 - 1, y1 - 1], fill=fill, outline=outline)

        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def to_pdf(self, pattern: PatternSheet) -> bytes:
        raise NotImplementedError("PDF export is reserved for the advanced package task.")

    def to_excel(self, pattern: PatternSheet) -> bytes:
        raise NotImplementedError("Excel export is reserved for the advanced package task.")

    def to_partition_images(self, pattern: PatternSheet, block_size: int = 20) -> list[bytes]:
        raise NotImplementedError("Partition image export is reserved for the advanced package task.")


def darken(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int, int]:
    return (int(rgb[0] * factor), int(rgb[1] * factor), int(rgb[2] * factor), 255)


def empty_png() -> bytes:
    image = Image.new("RGBA", (1, 1), (255, 255, 255, 0))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
