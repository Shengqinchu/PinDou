"""Pattern export helpers."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

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
                draw_bead_square(draw, x0, y0, x1, y1, fill=fill, outline=outline)

        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def to_labeled_grid_png(self, pattern: PatternSheet) -> bytes:
        grid = pattern.grid
        if not grid or not grid[0]:
            return empty_png()
        rows = len(grid)
        cols = max(len(row) for row in grid)
        cell_size = max(self.cell_size, 18)
        legend_lines = legend_text_lines(pattern, max_chars=max(30, cols * cell_size // 7))
        legend_height = 18 * max(1, len(legend_lines)) + 12
        width = cols * cell_size + self.padding * 2
        height = rows * cell_size + self.padding * 2 + legend_height
        image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        grid_left = self.padding
        grid_top = self.padding
        grid_right = grid_left + cols * cell_size
        grid_bottom = grid_top + rows * cell_size
        board_interval = infer_board_interval(cols, rows)

        draw_pegboard_background(
            draw,
            grid_left,
            grid_top,
            cols,
            rows,
            cell_size,
            board_interval=board_interval,
        )

        for row_idx, row in enumerate(grid):
            for col_idx, bead in enumerate(row):
                x0 = grid_left + col_idx * cell_size
                y0 = grid_top + row_idx * cell_size
                x1 = x0 + cell_size
                y1 = y0 + cell_size
                if isinstance(bead, NoBead):
                    fill = (255, 255, 255, 255)
                    code = ""
                    text_fill = (45, 45, 45, 255)
                else:
                    fill = (*bead.rgb, 255)
                    code = bead.code
                    text_fill = contrast_text(bead.rgb)
                if isinstance(bead, NoBead):
                    draw.rectangle([x0, y0, x1, y1], fill=fill)
                else:
                    draw_bead_square(draw, x0, y0, x1, y1, fill=fill, outline=darken(bead.rgb, factor=0.72))
                if code:
                    text_box = draw.textbbox((0, 0), code, font=font)
                    text_w = text_box[2] - text_box[0]
                    text_h = text_box[3] - text_box[1]
                    draw.text(
                        (x0 + (cell_size - text_w) / 2, y0 + (cell_size - text_h) / 2 - 1),
                        code,
                        font=font,
                        fill=text_fill,
                    )

        overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        small_line = (96, 96, 96, 64)
        big_line = (220, 40, 40, 128)
        for col in range(cols + 1):
            x = grid_left + col * cell_size
            color = big_line if col % 10 == 0 else small_line
            width_px = 2 if col % 10 == 0 else 1
            overlay_draw.line([(x, grid_top), (x, grid_bottom)], fill=color, width=width_px)
        for row in range(rows + 1):
            y = grid_top + row * cell_size
            color = big_line if row % 10 == 0 else small_line
            width_px = 2 if row % 10 == 0 else 1
            overlay_draw.line([(grid_left, y), (grid_right, y)], fill=color, width=width_px)
        image.alpha_composite(overlay)

        legend_y = grid_bottom + 8
        for line in legend_lines:
            draw.text((self.padding, legend_y), line, font=font, fill=(45, 45, 45, 255))
            legend_y += 18

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


def draw_bead_square(
    draw: ImageDraw.ImageDraw,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    *,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
) -> None:
    inset = 1
    radius = 2 if (x1 - x0) >= 12 else 1
    box = [x0 + inset, y0 + inset, x1 - inset, y1 - inset]
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline)


def draw_pegboard_background(
    draw: ImageDraw.ImageDraw,
    grid_left: int,
    grid_top: int,
    cols: int,
    rows: int,
    cell_size: int,
    *,
    board_interval: int | None,
) -> None:
    grid_right = grid_left + cols * cell_size
    grid_bottom = grid_top + rows * cell_size
    draw.rectangle([grid_left, grid_top, grid_right, grid_bottom], fill=(248, 249, 250, 255))

    peg_radius = max(2, cell_size // 7)
    peg_outline = (194, 199, 204, 150)
    peg_fill = (255, 255, 255, 180)
    for row in range(rows):
        cy = grid_top + row * cell_size + cell_size / 2
        for col in range(cols):
            cx = grid_left + col * cell_size + cell_size / 2
            draw.ellipse(
                [cx - peg_radius, cy - peg_radius, cx + peg_radius, cy + peg_radius],
                fill=peg_fill,
                outline=peg_outline,
            )

    if board_interval:
        boundary = (126, 134, 142, 180)
        for col in range(board_interval, cols, board_interval):
            x = grid_left + col * cell_size
            draw.line([(x, grid_top), (x, grid_bottom)], fill=boundary, width=3)
        for row in range(board_interval, rows, board_interval):
            y = grid_top + row * cell_size
            draw.line([(grid_left, y), (grid_right, y)], fill=boundary, width=3)
    draw.rectangle([grid_left, grid_top, grid_right, grid_bottom], outline=(160, 166, 173, 180), width=2)


def infer_board_interval(cols: int, rows: int) -> int | None:
    for interval in (26, 29, 27):
        if cols >= interval and rows >= interval and cols % interval == 0 and rows % interval == 0:
            return interval
    return None


def contrast_text(rgb: tuple[int, int, int]) -> tuple[int, int, int, int]:
    luminance = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    return (255, 255, 255, 255) if luminance < 140 else (0, 0, 0, 255)


def legend_text_lines(pattern: PatternSheet, *, max_chars: int) -> list[str]:
    counts = sorted(pattern.color_counts.items(), key=lambda item: item[1], reverse=True)
    chunks = [f"{code} ({count})" for code, count in counts]
    if not chunks:
        return ["No beads"]
    lines: list[str] = []
    current = ""
    for chunk in chunks:
        candidate = chunk if not current else f"{current} / {chunk}"
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = chunk
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def labeled_grid_filename(artwork_id: str) -> str:
    safe_id = "".join(ch for ch in artwork_id if ch.isalnum() or ch in {"_", "-"})
    return f"pattern_{safe_id}_with_grid.png"


def empty_png() -> bytes:
    image = Image.new("RGBA", (1, 1), (255, 255, 255, 0))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
