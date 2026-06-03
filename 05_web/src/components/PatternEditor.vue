<script setup lang="ts">
import { computed, ref } from 'vue';

import type { ColorRef, PatternSheet } from '../api/types';

const MIN_ZOOM = 1;
const MAX_ZOOM = 12;
const ZOOM_STEP = 1.25;

const props = defineProps<{
  pattern: PatternSheet;
  palette: ColorRef[];
}>();

const emit = defineEmits<{
  recolor: [payload: { row: number; col: number; color: ColorRef }];
}>();

interface DragState {
  pointerId: number;
  startX: number;
  startY: number;
  panX: number;
  panY: number;
  moved: boolean;
}

interface ActiveCell {
  row: number;
  col: number;
  x: number;
  y: number;
}

const svgRef = ref<SVGSVGElement | null>(null);
const frameRef = ref<HTMLElement | null>(null);
const zoom = ref(1);
const pan = ref({ x: 0, y: 0 });
const drag = ref<DragState | null>(null);
const activeCell = ref<ActiveCell | null>(null);
const emptyPatternId = `pd-empty-cell-${Math.random().toString(36).slice(2)}`;

const rows = computed(() => props.pattern.grid.length);
const cols = computed(() => Math.max(...props.pattern.grid.map((row) => row.length), 0));
const viewWidth = computed(() => Math.max(cols.value / zoom.value, 1));
const viewHeight = computed(() => Math.max(rows.value / zoom.value, 1));
const viewBox = computed(() => `${pan.value.x} ${pan.value.y} ${viewWidth.value} ${viewHeight.value}`);
const zoomLabel = computed(() => `${Math.round(zoom.value * 100)}%`);
const showCellCodes = computed(() => Math.max(rows.value, cols.value) <= 52 || zoom.value >= 1.7);
const paletteOptions = computed(() => uniqueColors(props.palette));
const activeCellLabel = computed(() => {
  const cell = activeCell.value;
  if (!cell) {
    return '';
  }
  return `${cell.row + 1} 行 · ${cell.col + 1} 列`;
});
const activeCellCode = computed(() => {
  const cell = activeCell.value;
  if (!cell) {
    return '';
  }
  return props.pattern.grid[cell.row]?.[cell.col]?.code || '空';
});
const paletteStyle = computed(() => {
  const cell = activeCell.value;
  return cell ? { left: `${cell.x}px`, top: `${cell.y}px` } : {};
});

function zoomIn(): void {
  setZoom(zoom.value * ZOOM_STEP);
}

function zoomOut(): void {
  setZoom(zoom.value / ZOOM_STEP);
}

function resetView(): void {
  zoom.value = 1;
  pan.value = { x: 0, y: 0 };
  activeCell.value = null;
}

function handleWheel(event: WheelEvent): void {
  const svg = svgRef.value;
  if (!svg || rows.value === 0 || cols.value === 0) {
    return;
  }
  const rect = svg.getBoundingClientRect();
  const relX = rect.width > 0 ? (event.clientX - rect.left) / rect.width : 0.5;
  const relY = rect.height > 0 ? (event.clientY - rect.top) / rect.height : 0.5;
  const oldWidth = viewWidth.value;
  const oldHeight = viewHeight.value;
  const centerX = pan.value.x + relX * oldWidth;
  const centerY = pan.value.y + relY * oldHeight;
  const nextZoom = event.deltaY < 0 ? zoom.value * 1.16 : zoom.value / 1.16;
  setZoom(nextZoom, { x: centerX, y: centerY, relX, relY });
}

function handlePointerDown(event: PointerEvent): void {
  if (event.button !== 0) {
    return;
  }
  activeCell.value = null;
  const svg = svgRef.value;
  svg?.setPointerCapture(event.pointerId);
  drag.value = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    panX: pan.value.x,
    panY: pan.value.y,
    moved: false
  };
}

function handlePointerMove(event: PointerEvent): void {
  const currentDrag = drag.value;
  const svg = svgRef.value;
  if (!currentDrag || !svg || currentDrag.pointerId !== event.pointerId) {
    return;
  }
  const rect = svg.getBoundingClientRect();
  const dx = event.clientX - currentDrag.startX;
  const dy = event.clientY - currentDrag.startY;
  if (Math.hypot(dx, dy) > 4) {
    currentDrag.moved = true;
  }
  const nextX = currentDrag.panX - (dx / Math.max(rect.width, 1)) * viewWidth.value;
  const nextY = currentDrag.panY - (dy / Math.max(rect.height, 1)) * viewHeight.value;
  pan.value = clampPan(nextX, nextY, zoom.value);
}

function handlePointerUp(event: PointerEvent): void {
  const currentDrag = drag.value;
  const svg = svgRef.value;
  if (!currentDrag || currentDrag.pointerId !== event.pointerId) {
    return;
  }
  svg?.releasePointerCapture(event.pointerId);
  drag.value = null;
  if (!currentDrag.moved) {
    openCellPalette(event);
  }
}

function openCellPalette(event: PointerEvent): void {
  const point = svgPointFromEvent(event);
  const row = Math.floor(point.y);
  const col = Math.floor(point.x);
  if (row < 0 || col < 0 || row >= rows.value || col >= (props.pattern.grid[row]?.length || 0)) {
    activeCell.value = null;
    return;
  }
  const frame = frameRef.value;
  const rect = frame?.getBoundingClientRect();
  const x = rect ? clamp(event.clientX - rect.left + 12, 12, Math.max(rect.width - 292, 12)) : 12;
  const y = rect ? clamp(event.clientY - rect.top + 12, 12, Math.max(rect.height - 250, 12)) : 12;
  activeCell.value = { row, col, x, y };
}

function chooseColor(color: ColorRef): void {
  const cell = activeCell.value;
  if (!cell) {
    return;
  }
  emit('recolor', { row: cell.row, col: cell.col, color: cloneColor(color) });
  activeCell.value = null;
}

function setZoom(
  rawZoom: number,
  anchor: { x: number; y: number; relX: number; relY: number } | null = null
): void {
  const nextZoom = clamp(rawZoom, MIN_ZOOM, MAX_ZOOM);
  const oldWidth = viewWidth.value;
  const oldHeight = viewHeight.value;
  zoom.value = nextZoom;
  const newWidth = viewWidth.value;
  const newHeight = viewHeight.value;
  const anchorX = anchor?.x ?? pan.value.x + oldWidth / 2;
  const anchorY = anchor?.y ?? pan.value.y + oldHeight / 2;
  const relX = anchor?.relX ?? 0.5;
  const relY = anchor?.relY ?? 0.5;
  pan.value = clampPan(anchorX - relX * newWidth, anchorY - relY * newHeight, nextZoom);
}

function clampPan(x: number, y: number, targetZoom: number): { x: number; y: number } {
  const width = Math.max(cols.value / targetZoom, 1);
  const height = Math.max(rows.value / targetZoom, 1);
  return {
    x: clamp(x, 0, Math.max(cols.value - width, 0)),
    y: clamp(y, 0, Math.max(rows.value - height, 0))
  };
}

function svgPointFromEvent(event: PointerEvent): { x: number; y: number } {
  const svg = svgRef.value;
  if (!svg) {
    return { x: 0, y: 0 };
  }
  const rect = svg.getBoundingClientRect();
  const relX = rect.width > 0 ? (event.clientX - rect.left) / rect.width : 0;
  const relY = rect.height > 0 ? (event.clientY - rect.top) / rect.height : 0;
  return {
    x: pan.value.x + relX * viewWidth.value,
    y: pan.value.y + relY * viewHeight.value
  };
}

function cellFill(cell: ColorRef | null): string {
  return cell?.hex || `url(#${emptyPatternId})`;
}

function textFill(cell: ColorRef | null): string {
  if (!cell) {
    return '#8b8178';
  }
  const [r, g, b] = cell.rgb;
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return luminance < 145 ? '#ffffff' : '#282828';
}

function fontSizeForCode(code: string): number {
  if (code.length <= 2) {
    return 0.38;
  }
  if (code.length === 3) {
    return 0.31;
  }
  return Math.max(0.2, 0.78 / Math.max(code.length, 1));
}

function uniqueColors(colors: ColorRef[]): ColorRef[] {
  const seen = new Set<string>();
  const unique: ColorRef[] = [];
  for (const color of colors) {
    if (!seen.has(color.code)) {
      seen.add(color.code);
      unique.push(color);
    }
  }
  return unique;
}

function cloneColor(color: ColorRef): ColorRef {
  return {
    ...color,
    rgb: [...color.rgb] as [number, number, number]
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
</script>

<template>
  <div class="pattern-editor">
    <div class="pattern-editor__toolbar" aria-label="图纸缩放">
      <button type="button" class="pattern-editor__tool" aria-label="缩小" @click="zoomOut">-</button>
      <span class="pattern-editor__zoom">{{ zoomLabel }}</span>
      <button type="button" class="pattern-editor__tool" aria-label="放大" @click="zoomIn">+</button>
      <button type="button" class="pattern-editor__reset" @click="resetView">复位</button>
    </div>

    <div ref="frameRef" class="pattern-editor__frame">
      <svg
        ref="svgRef"
        class="pattern-editor__svg"
        :viewBox="viewBox"
        role="img"
        aria-label="可编辑拼豆图纸"
        @wheel.prevent="handleWheel"
        @pointerdown="handlePointerDown"
        @pointermove="handlePointerMove"
        @pointerup="handlePointerUp"
        @pointercancel="handlePointerUp"
      >
        <defs>
          <pattern :id="emptyPatternId" width="1" height="1" patternUnits="userSpaceOnUse">
            <rect width="1" height="1" fill="#fffaf5"></rect>
            <path d="M0 1 L1 0" stroke="#eadfd4" stroke-width="0.04"></path>
          </pattern>
        </defs>
        <rect :width="cols" :height="rows" fill="#fff"></rect>
        <g>
          <g v-for="(row, rowIndex) in pattern.grid" :key="rowIndex">
            <g v-for="(cell, colIndex) in row" :key="`${rowIndex}-${colIndex}`">
              <rect
                :x="colIndex"
                :y="rowIndex"
                width="1"
                height="1"
                :fill="cellFill(cell)"
                stroke="rgba(45, 45, 45, 0.28)"
                stroke-width="0.025"
                vector-effect="non-scaling-stroke"
              ></rect>
              <text
                v-if="cell && showCellCodes"
                :x="colIndex + 0.5"
                :y="rowIndex + 0.56"
                :font-size="fontSizeForCode(cell.code)"
                :fill="textFill(cell)"
                text-anchor="middle"
                dominant-baseline="middle"
                paint-order="stroke"
                stroke="rgba(255, 255, 255, 0.5)"
                stroke-width="0.025"
                vector-effect="non-scaling-stroke"
              >
                {{ cell.code }}
              </text>
            </g>
          </g>
        </g>
      </svg>

      <div v-if="activeCell" class="pattern-editor__palette" :style="paletteStyle">
        <div class="pattern-editor__palette-head">
          <strong>{{ activeCellLabel }}</strong>
          <span>{{ activeCellCode }}</span>
        </div>
        <div class="pattern-editor__palette-grid">
          <button
            v-for="color in paletteOptions"
            :key="color.code"
            type="button"
            class="pattern-editor__color"
            :class="{ 'pattern-editor__color--active': color.code === activeCellCode }"
            :title="`${color.code} · ${color.name_cn}`"
            @click="chooseColor(color)"
          >
            <span :style="{ backgroundColor: color.hex }"></span>
            <strong>{{ color.code }}</strong>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pattern-editor {
  width: 100%;
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
}

.pattern-editor__toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pattern-editor__tool,
.pattern-editor__reset {
  appearance: none;
  min-width: 38px;
  height: 38px;
  border: 1px solid rgba(255, 142, 83, 0.28);
  border-radius: 12px;
  background: #fff;
  color: var(--pd-fg-1);
  cursor: pointer;
  font: inherit;
  font-weight: 900;
}

.pattern-editor__tool:hover,
.pattern-editor__reset:hover {
  border-color: rgba(255, 142, 83, 0.52);
  color: var(--pd-orange);
}

.pattern-editor__reset {
  padding: 0 14px;
}

.pattern-editor__zoom {
  min-width: 58px;
  color: var(--pd-fg-2);
  font-size: 13px;
  font-weight: 900;
  text-align: center;
}

.pattern-editor__frame {
  position: relative;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--pd-stroke);
  border-radius: 18px;
  background: #fff;
}

.pattern-editor__svg {
  width: 100%;
  height: 100%;
  display: block;
  cursor: grab;
  touch-action: none;
  user-select: none;
}

.pattern-editor__svg:active {
  cursor: grabbing;
}

.pattern-editor__palette {
  position: absolute;
  z-index: 3;
  width: min(280px, calc(100% - 24px));
  max-height: min(360px, calc(100% - 24px));
  overflow: auto;
  border: 1px solid rgba(237, 228, 218, 0.92);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 18px 45px rgba(45, 45, 45, 0.16);
  padding: 12px;
}

.pattern-editor__palette-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.pattern-editor__palette-head strong {
  color: var(--pd-fg-1);
  font-size: 13px;
  font-weight: 900;
}

.pattern-editor__palette-head span {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
}

.pattern-editor__palette-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.pattern-editor__color {
  appearance: none;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 7px;
  min-width: 0;
  min-height: 38px;
  border: 1px solid var(--pd-stroke);
  border-radius: 12px;
  background: var(--pd-peach-50);
  color: var(--pd-fg-1);
  cursor: pointer;
  font: inherit;
  padding: 6px;
}

.pattern-editor__color:hover,
.pattern-editor__color--active {
  border-color: rgba(255, 142, 83, 0.58);
  background: #fff;
}

.pattern-editor__color span {
  width: 22px;
  height: 22px;
  border: 1px solid rgba(45, 45, 45, 0.12);
  border-radius: 50%;
  box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.7);
}

.pattern-editor__color strong {
  min-width: 0;
  overflow: hidden;
  font-size: 12px;
  font-weight: 900;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
