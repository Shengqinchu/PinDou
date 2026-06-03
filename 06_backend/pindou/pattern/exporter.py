"""Pattern export helpers."""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from pindou.pattern.builder import NoBead, PatternSheet


@dataclass(frozen=True)
class PartitionImage:
    index: int
    key: str
    label: str
    total: int
    row_start: int
    row_end: int
    col_start: int
    col_end: int
    rows: int
    cols: int
    image: bytes


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
        cell_size = labeled_cell_size(cols, rows)
        legend_lines = legend_text_lines(pattern, max_chars=max(30, cols * cell_size // 7))
        legend_font = load_font(15)
        legend_line_height = font_line_height(legend_font) + 8
        legend_height = legend_line_height * max(1, len(legend_lines)) + 16
        width = cols * cell_size + self.padding * 2
        height = rows * cell_size + self.padding * 2 + legend_height
        image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)

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
                if code and should_draw_cell_code(row_idx, col_idx, cols, rows):
                    draw_centered_cell_code(draw, code, x0, y0, cell_size, fill=text_fill)

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
            draw.text((self.padding, legend_y), line, font=legend_font, fill=(45, 45, 45, 255))
            legend_y += legend_line_height

        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def to_pdf(self, pattern: PatternSheet) -> bytes:
        raise NotImplementedError("PDF export is reserved for the advanced package task.")

    def to_excel(self, pattern: PatternSheet) -> bytes:
        raise NotImplementedError("Excel export is reserved for the advanced package task.")

    def to_partition_images(self, pattern: PatternSheet, block_size: int = 20) -> list[bytes]:
        _ = block_size
        return [partition.image for partition in self.export_partitions(pattern)]

    def export_partitions(self, pattern: PatternSheet, partition_size: int | None = None) -> list[PartitionImage]:
        _ = partition_size
        return export_partitions(pattern)


def export_partitions(pattern: PatternSheet, partition_size: int | None = None) -> list[PartitionImage]:
    _ = partition_size
    grid = pattern.grid
    if not grid or not grid[0]:
        return []

    rows = len(grid)
    cols = max(len(row) for row in grid)
    row_mid = (rows + 1) // 2
    col_mid = (cols + 1) // 2
    total = 4
    partitions: list[PartitionImage] = []

    quadrants = [
        (1, "top_left", "左上区", 0, row_mid, 0, col_mid),
        (2, "top_right", "右上区", 0, row_mid, col_mid, cols),
        (3, "bottom_left", "左下区", row_mid, rows, 0, col_mid),
        (4, "bottom_right", "右下区", row_mid, rows, col_mid, cols),
    ]
    for index, key, label, row_start, row_end, col_start, col_end in quadrants:
        image = render_partition_image(
            pattern,
            index=index,
            title=label,
            total=total,
            row_start=row_start,
            row_end=row_end,
            col_start=col_start,
            col_end=col_end,
        )
        partitions.append(
            PartitionImage(
                index=index,
                key=key,
                label=label,
                total=total,
                row_start=row_start,
                row_end=row_end,
                col_start=col_start,
                col_end=col_end,
                rows=row_end - row_start,
                cols=col_end - col_start,
                image=image,
            )
        )
    return partitions


def render_partition_image(
    pattern: PatternSheet,
    *,
    index: int,
    title: str,
    total: int,
    row_start: int,
    row_end: int,
    col_start: int,
    col_end: int,
) -> bytes:
    padding = 18
    title_height = 58
    legend_height = 34
    rows = row_end - row_start
    cols = col_end - col_start
    cell_size = partition_cell_size(rows, cols)
    grid_width = cols * cell_size
    grid_height = rows * cell_size
    width = max(grid_width + padding * 2, 430)
    height = title_height + grid_height + legend_height + padding
    image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)

    title_font = load_font(24)
    subtitle_font = load_font(14)
    draw.text((padding, 14), f"{title} · 第 {index}/{total} 区", font=title_font, fill=(31, 31, 31, 255))
    draw.text(
        (padding, 42),
        f"行 {row_start + 1}-{row_end} / 列 {col_start + 1}-{col_end}",
        font=subtitle_font,
        fill=(118, 118, 118, 255),
    )

    draw_partition_minimap(
        draw,
        width - padding - 84,
        12,
        84,
        38,
        rows_total=len(pattern.grid),
        cols_total=max(len(row) for row in pattern.grid),
        row_start=row_start,
        row_end=row_end,
        col_start=col_start,
        col_end=col_end,
    )

    grid_left = padding
    grid_top = title_height
    draw_pegboard_background(
        draw,
        grid_left,
        grid_top,
        cols,
        rows,
        cell_size,
        board_interval=None,
    )

    for local_row, source_row in enumerate(range(row_start, row_end)):
        row = pattern.grid[source_row]
        for local_col, source_col in enumerate(range(col_start, col_end)):
            bead = row[source_col] if source_col < len(row) else NoBead()
            x0 = grid_left + local_col * cell_size
            y0 = grid_top + local_row * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            if isinstance(bead, NoBead):
                draw.rectangle([x0, y0, x1, y1], fill=(255, 255, 255, 255))
                continue
            draw_bead_square(draw, x0, y0, x1, y1, fill=(*bead.rgb, 255), outline=darken(bead.rgb, factor=0.72))
            code = bead.code
            draw_centered_cell_code(draw, code, x0, y0, cell_size, fill=contrast_text(bead.rgb))

    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    for col in range(cols + 1):
        x = grid_left + col * cell_size
        overlay_draw.line([(x, grid_top), (x, grid_top + grid_height)], fill=(96, 96, 96, 80), width=1)
    for row in range(rows + 1):
        y = grid_top + row * cell_size
        overlay_draw.line([(grid_left, y), (grid_left + grid_width, y)], fill=(96, 96, 96, 80), width=1)
    image.alpha_composite(overlay)

    footer = f"{cols}x{rows} 格 · 点击图片可放大查看"
    draw.text((padding, grid_top + grid_height + 10), footer, font=subtitle_font, fill=(90, 90, 90, 255))

    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def partition_cell_size(rows: int, cols: int) -> int:
    max_dim = max(rows, cols, 1)
    if max_dim <= 13:
        return 30
    if max_dim <= 26:
        return 24
    if max_dim <= 39:
        return 20
    if max_dim <= 52:
        return 18
    return max(14, min(30, 900 // max_dim))


def draw_partition_minimap(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    rows_total: int,
    cols_total: int,
    row_start: int,
    row_end: int,
    col_start: int,
    col_end: int,
) -> None:
    draw.rounded_rectangle([x, y, x + width, y + height], radius=5, fill=(248, 249, 250, 255), outline=(190, 190, 190, 255))
    hx0 = x + int((col_start / cols_total) * width)
    hx1 = x + max(2, int((col_end / cols_total) * width))
    hy0 = y + int((row_start / rows_total) * height)
    hy1 = y + max(2, int((row_end / rows_total) * height))
    draw.rectangle([hx0, hy0, hx1, hy1], fill=(255, 107, 157, 130), outline=(255, 107, 157, 255), width=2)


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
    radius = 1
    box = [x0 + inset, y0 + inset, x1 - inset, y1 - inset]
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline)


def labeled_cell_size(cols: int, rows: int) -> int:
    max_dim = max(cols, rows)
    if max_dim <= 52:
        return 24
    return 18


def should_draw_cell_code(row_idx: int, col_idx: int, cols: int, rows: int) -> bool:
    if max(cols, rows) <= 52:
        return True
    return row_idx % 10 == 0 and col_idx % 10 == 0


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


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def load_monospace_font(size: int) -> ImageFont.ImageFont:
    for name in ("DejaVuSansMono.ttf", "consola.ttf", "Consolas.ttf", "cour.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return load_font(size)


def draw_centered_cell_code(
    draw: ImageDraw.ImageDraw,
    code: str,
    x0: int,
    y0: int,
    cell_size: int,
    *,
    fill: tuple[int, int, int, int],
) -> bool:
    code_font = fit_cell_code_font(draw, code, cell_size)
    if code_font is None:
        return False
    text_box = draw.textbbox((0, 0), code, font=code_font)
    text_w = text_box[2] - text_box[0]
    text_h = text_box[3] - text_box[1]
    text_x = x0 + (cell_size - text_w) / 2 - text_box[0]
    text_y = y0 + (cell_size - text_h) / 2 - text_box[1]
    draw.text((text_x, text_y), code, font=code_font, fill=fill)
    return True


def fit_cell_code_font(draw: ImageDraw.ImageDraw, code: str, cell_size: int) -> ImageFont.ImageFont | None:
    cell_padding = max(2, int(cell_size * 0.12))
    max_width = max(4, cell_size - cell_padding * 2)
    max_height = max(4, cell_size - cell_padding * 2)
    font_size = max(7, int(cell_size * 0.46))

    while font_size >= 7:
        font = load_monospace_font(font_size)
        text_box = draw.textbbox((0, 0), code, font=font)
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
        if text_width <= max_width and text_height <= max_height:
            return font
        font_size -= 1
    return None


def font_line_height(font: ImageFont.ImageFont) -> int:
    bbox = font.getbbox("Hg")
    return bbox[3] - bbox[1]


def contrast_text(rgb: tuple[int, int, int]) -> tuple[int, int, int, int]:
    luminance = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    return (0, 0, 0, 255) if luminance > 128 else (255, 255, 255, 255)


def legend_text_lines(pattern: PatternSheet, *, max_chars: int) -> list[str]:
    counts = sorted(pattern.color_counts.items(), key=lambda item: item[1], reverse=True)
    chunks = [f"{code} ({count})" for code, count in counts]
    if not chunks:
        return ["无豆"]
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


def partition_filename(artwork_id: str, index: int) -> str:
    safe_id = "".join(ch for ch in artwork_id if ch.isalnum() or ch in {"_", "-"})
    return f"pattern_{safe_id}_partition_{index:02d}.png"


def empty_png() -> bytes:
    image = Image.new("RGBA", (1, 1), (255, 255, 255, 0))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
