import type { ColorRef, PatternSheet } from '../api/types';

export interface PaletteRow {
  color: ColorRef;
  count: number;
  percent: number;
}

export interface CellPatch {
  row: number;
  col: number;
  before: ColorRef | null;
  after: ColorRef | null;
}

export function recalculatePattern(sheet: PatternSheet): PatternSheet {
  const grid = sheet.grid.map((row) => row.map((cell) => (cell ? cloneColor(cell) : null)));
  const counts: Record<string, number> = {};
  const coords: [number, number, string | null][] = [];
  const noBeadMask: boolean[][] = [];
  const paletteIndex = new Map(sheet.palette_used.map((color, index) => [color.code, index]));
  const colorByCode = new Map<string, ColorRef>();

  for (const color of sheet.palette_used) {
    colorByCode.set(color.code, cloneColor(color));
  }

  grid.forEach((row, rowIndex) => {
    const maskRow: boolean[] = [];
    row.forEach((cell, colIndex) => {
      if (!cell) {
        maskRow.push(true);
        return;
      }
      counts[cell.code] = (counts[cell.code] || 0) + 1;
      coords.push([rowIndex, colIndex, cell.code]);
      colorByCode.set(cell.code, cloneColor(cell));
      maskRow.push(false);
    });
    noBeadMask.push(maskRow);
  });

  const paletteUsed = Array.from(colorByCode.values())
    .filter((color) => counts[color.code] > 0)
    .sort((left, right) => {
      const leftIndex = paletteIndex.get(left.code) ?? Number.MAX_SAFE_INTEGER;
      const rightIndex = paletteIndex.get(right.code) ?? Number.MAX_SAFE_INTEGER;
      return leftIndex - rightIndex || left.code.localeCompare(right.code);
    });

  return {
    ...sheet,
    grid,
    color_counts: counts,
    bead_total: Object.values(counts).reduce((sum, count) => sum + count, 0),
    coords,
    no_bead_mask: noBeadMask,
    palette_used: paletteUsed
  };
}

export function paletteRowsForPattern(sheet: PatternSheet | null): PaletteRow[] {
  if (!sheet) {
    return [];
  }
  return sheet.palette_used
    .map((color) => {
      const count = sheet.color_counts[color.code] || 0;
      const percent = sheet.bead_total > 0 ? Math.round((count / sheet.bead_total) * 100) : 0;
      return { color, count, percent };
    })
    .sort((left, right) => right.count - left.count);
}

export function applyCellPatch(sheet: PatternSheet, patch: CellPatch, useAfter = true): PatternSheet {
  const grid = sheet.grid.map((row, rowIndex) => (
    rowIndex === patch.row ? [...row] : row
  ));
  const row = grid[patch.row];
  if (!row || patch.col < 0 || patch.col >= row.length) {
    return sheet;
  }
  row[patch.col] = cloneColorOrNull(useAfter ? patch.after : patch.before);
  return recalculatePattern({ ...sheet, grid });
}

export function clonePattern(sheet: PatternSheet): PatternSheet {
  return JSON.parse(JSON.stringify(sheet)) as PatternSheet;
}

export function cloneColor(color: ColorRef): ColorRef {
  return {
    ...color,
    rgb: [...color.rgb] as [number, number, number]
  };
}

export function cloneColorOrNull(color: ColorRef | null): ColorRef | null {
  return color ? cloneColor(color) : null;
}

export function uniqueColors(colors: ColorRef[]): ColorRef[] {
  const seen = new Set<string>();
  const unique: ColorRef[] = [];
  for (const color of colors) {
    if (!seen.has(color.code)) {
      seen.add(color.code);
      unique.push(cloneColor(color));
    }
  }
  return unique;
}

export function colorTextFill(cell: ColorRef | null): string {
  if (!cell) {
    return '#8b8178';
  }
  const [r, g, b] = cell.rgb;
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return luminance < 145 ? '#ffffff' : '#282828';
}

export function fontSizeForCode(code: string, cellPx: number): number {
  if (code.length <= 2) {
    return Math.max(8, cellPx * 0.38);
  }
  if (code.length === 3) {
    return Math.max(7, cellPx * 0.31);
  }
  return Math.max(6, Math.min(cellPx * 0.28, (cellPx * 0.78) / Math.max(code.length, 1)));
}
