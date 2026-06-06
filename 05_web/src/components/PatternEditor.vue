<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';

import type { ColorRef, PatternSheet } from '../api/types';
import type { CellPatch } from '../utils/patternEditing';
import { cloneColorOrNull, colorTextFill, fontSizeForCode } from '../utils/patternEditing';

const CACHE_CELL_PX = 18;
const MAX_SCALE = 82;
const LABEL_MIN_CELL_PX = 18;
const PINCH_SETTLE_MS = 260;

const props = defineProps<{
  pattern: PatternSheet;
  palette: ColorRef[];
  selectedColor: ColorRef | null;
  activeTool: 'none' | 'paint' | 'erase';
  paintEnabled: boolean;
  showGridLines: boolean;
  patternKey: number;
  paintRevision: number;
  lastPatch: CellPatch | null;
}>();

const emit = defineEmits<{
  applyCell: [payload: { row: number; col: number; color: ColorRef | null }];
  cursorChange: [payload: { row: number; col: number; cell: ColorRef | null }];
}>();

interface Point {
  x: number;
  y: number;
}

interface PointerPoint extends Point {
  pointerType: string;
}

interface MouseDrag {
  pointerId: number;
  button: number;
  mode: 'pan' | 'paint';
  start: Point;
  startOffsetX: number;
  startOffsetY: number;
  moved: boolean;
  lastPaintedKey: string;
}

interface PinchState {
  pointerIds: [number, number];
  startDistance: number;
  startScale: number;
  anchorGrid: Point;
}

const frameRef = ref<HTMLElement | null>(null);
const baseCanvasRef = ref<HTMLCanvasElement | null>(null);
const overlayCanvasRef = ref<HTMLCanvasElement | null>(null);
const canvasSize = reactive({ width: 1, height: 1, dpr: 1 });
const view = reactive({ scale: 10, offsetX: 0, offsetY: 0 });
const cursor = ref({ row: 0, col: 0 });
const pointers = new Map<number, PointerPoint>();
const mouseDrag = ref<MouseDrag | null>(null);
const pinch = ref<PinchState | null>(null);
const pinchSettledAt = ref(0);
const multiTouchLocked = ref(false);
const touchGestureHadMultiTouch = ref(false);
const hoverCell = ref<{ row: number; col: number } | null>(null);
let lastTouchPaintKey = '';
let pendingTouchPaintTimer: number | undefined;

let staticCanvas: HTMLCanvasElement | null = null;
let resizeObserver: ResizeObserver | null = null;
let baseFrame = 0;
let overlayFrame = 0;

const rows = computed(() => props.pattern.grid.length);
const cols = computed(() => Math.max(...props.pattern.grid.map((row) => row.length), 0));
const minScale = computed(() => {
  if (!rows.value || !cols.value) {
    return 1;
  }
  return Math.max(2, Math.min(canvasSize.width / cols.value, canvasSize.height / rows.value) * 0.92);
});
const scaleLabel = computed(() => `${Math.round((view.scale / Math.max(minScale.value, 1)) * 100)}%`);
const cursorCell = computed(() => props.pattern.grid[cursor.value.row]?.[cursor.value.col] || null);
const cursorCode = computed(() => cursorCell.value?.code || '空');
const selectedCode = computed(() => {
  if (props.activeTool === 'none') {
    return '浏览';
  }
  return props.activeTool === 'erase' ? '橡皮擦' : props.selectedColor?.code || '未选';
});

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    resizeCanvases();
  });
  if (frameRef.value) {
    resizeObserver.observe(frameRef.value);
  }
  void nextTick(() => {
    resizeCanvases();
    rebuildStaticCache();
    resetView();
  });
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  resizeObserver = null;
  if (baseFrame) {
    cancelAnimationFrame(baseFrame);
  }
  if (overlayFrame) {
    cancelAnimationFrame(overlayFrame);
  }
  clearPendingTouchPaint();
});

watch(
  () => props.patternKey,
  () => {
    rebuildStaticCache();
    clampCurrentView();
    cursor.value = clampCursor(cursor.value.row, cursor.value.col);
    emitCursor();
    scheduleBaseDraw();
    scheduleOverlayDraw();
  }
);

watch(
  () => props.paintRevision,
  () => {
    const patch = props.lastPatch;
    if (patch) {
      updateCachedCell(patch.row, patch.col, cloneColorOrNull(patch.after));
      if (patch.row === cursor.value.row && patch.col === cursor.value.col) {
        emitCursor();
      }
      scheduleBaseDraw();
      scheduleOverlayDraw();
    }
  }
);

watch(
  () => props.selectedColor?.code,
  () => {
    scheduleOverlayDraw();
  }
);

watch(
  () => props.showGridLines,
  () => {
    scheduleBaseDraw();
  }
);

function zoomIn(): void {
  zoomAt(canvasSize.width / 2, canvasSize.height / 2, view.scale * 1.22);
}

function zoomOut(): void {
  zoomAt(canvasSize.width / 2, canvasSize.height / 2, view.scale / 1.22);
}

function resetView(): void {
  const nextScale = minScale.value;
  view.scale = nextScale;
  view.offsetX = (canvasSize.width - cols.value * nextScale) / 2;
  view.offsetY = (canvasSize.height - rows.value * nextScale) / 2;
  cursor.value = clampCursor(Math.floor(rows.value / 2), Math.floor(cols.value / 2));
  emitCursor();
  scheduleBaseDraw();
  scheduleOverlayDraw();
}

function paintAtCursor(): void {
  applyCell(cursor.value.row, cursor.value.col);
}

function resizeCanvases(): void {
  const frame = frameRef.value;
  if (!frame) {
    return;
  }
  const rect = frame.getBoundingClientRect();
  canvasSize.width = Math.max(1, rect.width);
  canvasSize.height = Math.max(1, rect.height);
  canvasSize.dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 3));
  setupCanvas(baseCanvasRef.value);
  setupCanvas(overlayCanvasRef.value);
  clampCurrentView();
  scheduleBaseDraw();
  scheduleOverlayDraw();
}

function setupCanvas(canvas: HTMLCanvasElement | null): void {
  if (!canvas) {
    return;
  }
  const width = Math.round(canvasSize.width * canvasSize.dpr);
  const height = Math.round(canvasSize.height * canvasSize.dpr);
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
}

function rebuildStaticCache(): void {
  if (!rows.value || !cols.value) {
    staticCanvas = null;
    return;
  }
  staticCanvas = document.createElement('canvas');
  staticCanvas.width = Math.max(1, cols.value * CACHE_CELL_PX);
  staticCanvas.height = Math.max(1, rows.value * CACHE_CELL_PX);
  const ctx = staticCanvas.getContext('2d');
  if (!ctx) {
    return;
  }
  ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = '#fffaf5';
  ctx.fillRect(0, 0, staticCanvas.width, staticCanvas.height);
  for (let row = 0; row < rows.value; row += 1) {
    for (let col = 0; col < cols.value; col += 1) {
      drawCacheCell(ctx, row, col, props.pattern.grid[row]?.[col] || null);
    }
  }
}

function updateCachedCell(row: number, col: number, color: ColorRef | null): void {
  const ctx = staticCanvas?.getContext('2d');
  if (!ctx) {
    rebuildStaticCache();
    return;
  }
  drawCacheCell(ctx, row, col, color);
}

function drawCacheCell(ctx: CanvasRenderingContext2D, row: number, col: number, color: ColorRef | null): void {
  const x = col * CACHE_CELL_PX;
  const y = row * CACHE_CELL_PX;
  ctx.fillStyle = color?.hex || '#fffaf5';
  ctx.fillRect(x, y, CACHE_CELL_PX, CACHE_CELL_PX);
  if (!color) {
    ctx.strokeStyle = '#efe4da';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, y + CACHE_CELL_PX);
    ctx.lineTo(x + CACHE_CELL_PX, y);
    ctx.stroke();
  }
}

function scheduleBaseDraw(): void {
  if (baseFrame) {
    return;
  }
  baseFrame = requestAnimationFrame(() => {
    baseFrame = 0;
    drawBase();
  });
}

function scheduleOverlayDraw(): void {
  if (overlayFrame) {
    return;
  }
  overlayFrame = requestAnimationFrame(() => {
    overlayFrame = 0;
    drawOverlay();
  });
}

function drawBase(): void {
  const canvas = baseCanvasRef.value;
  const ctx = canvas?.getContext('2d');
  if (!canvas || !ctx) {
    return;
  }
  ctx.setTransform(canvasSize.dpr, 0, 0, canvasSize.dpr, 0, 0);
  ctx.clearRect(0, 0, canvasSize.width, canvasSize.height);
  ctx.fillStyle = '#fffaf5';
  ctx.fillRect(0, 0, canvasSize.width, canvasSize.height);
  if (!staticCanvas || !rows.value || !cols.value) {
    return;
  }

  ctx.imageSmoothingEnabled = false;
  const visible = visibleBounds(1);
  const sx = visible.colStart * CACHE_CELL_PX;
  const sy = visible.rowStart * CACHE_CELL_PX;
  const sw = Math.max(1, (visible.colEnd - visible.colStart) * CACHE_CELL_PX);
  const sh = Math.max(1, (visible.rowEnd - visible.rowStart) * CACHE_CELL_PX);
  const dx = view.offsetX + visible.colStart * view.scale;
  const dy = view.offsetY + visible.rowStart * view.scale;
  const dw = (visible.colEnd - visible.colStart) * view.scale;
  const dh = (visible.rowEnd - visible.rowStart) * view.scale;
  ctx.drawImage(staticCanvas, sx, sy, sw, sh, dx, dy, dw, dh);

  if (props.showGridLines && view.scale >= 6) {
    drawGridLines(ctx, visible);
  }
  if (view.scale >= LABEL_MIN_CELL_PX) {
    drawCellLabels(ctx, visible);
  }
}

function drawGridLines(ctx: CanvasRenderingContext2D, bounds: ReturnType<typeof visibleBounds>): void {
  ctx.save();
  ctx.strokeStyle = view.scale >= 18 ? 'rgba(45,45,45,0.3)' : 'rgba(45,45,45,0.18)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let col = bounds.colStart; col <= bounds.colEnd; col += 1) {
    const x = crisp(view.offsetX + col * view.scale);
    ctx.moveTo(x, view.offsetY + bounds.rowStart * view.scale);
    ctx.lineTo(x, view.offsetY + bounds.rowEnd * view.scale);
  }
  for (let row = bounds.rowStart; row <= bounds.rowEnd; row += 1) {
    const y = crisp(view.offsetY + row * view.scale);
    ctx.moveTo(view.offsetX + bounds.colStart * view.scale, y);
    ctx.lineTo(view.offsetX + bounds.colEnd * view.scale, y);
  }
  ctx.stroke();
  ctx.restore();
}

function drawCellLabels(ctx: CanvasRenderingContext2D, bounds: ReturnType<typeof visibleBounds>): void {
  ctx.save();
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  for (let row = bounds.rowStart; row < bounds.rowEnd; row += 1) {
    for (let col = bounds.colStart; col < bounds.colEnd; col += 1) {
      const cell = props.pattern.grid[row]?.[col] || null;
      if (!cell) {
        continue;
      }
      const x = view.offsetX + (col + 0.5) * view.scale;
      const y = view.offsetY + (row + 0.54) * view.scale;
      const fontSize = fontSizeForCode(cell.code, view.scale);
      ctx.font = `900 ${fontSize}px ${getComputedStyle(document.documentElement).getPropertyValue('--pd-font-mono') || 'monospace'}`;
      ctx.lineWidth = Math.max(2, view.scale * 0.08);
      ctx.strokeStyle = 'rgba(255,255,255,0.62)';
      ctx.fillStyle = colorTextFill(cell);
      ctx.strokeText(cell.code, x, y);
      ctx.fillText(cell.code, x, y);
    }
  }
  ctx.restore();
}

function drawOverlay(): void {
  const canvas = overlayCanvasRef.value;
  const ctx = canvas?.getContext('2d');
  if (!canvas || !ctx) {
    return;
  }
  ctx.setTransform(canvasSize.dpr, 0, 0, canvasSize.dpr, 0, 0);
  ctx.clearRect(0, 0, canvasSize.width, canvasSize.height);
  drawCellMarker(ctx, cursor.value.row, cursor.value.col, '#ff6b9d', 3);
  const hover = hoverCell.value;
  if (hover && (hover.row !== cursor.value.row || hover.col !== cursor.value.col)) {
    drawCellMarker(ctx, hover.row, hover.col, 'rgba(255,142,83,0.72)', 2);
  }
  const center = cellCenterToScreen(cursor.value.row, cursor.value.col);
  ctx.save();
  ctx.fillStyle = props.selectedColor?.hex || '#fff';
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(center.x, center.y, Math.max(5, Math.min(12, view.scale * 0.22)), 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

function drawCellMarker(
  ctx: CanvasRenderingContext2D,
  row: number,
  col: number,
  color: string,
  width: number
): void {
  if (row < 0 || col < 0 || row >= rows.value || col >= cols.value) {
    return;
  }
  const x = view.offsetX + col * view.scale;
  const y = view.offsetY + row * view.scale;
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.setLineDash([Math.max(4, view.scale * 0.25), Math.max(3, view.scale * 0.14)]);
  ctx.strokeRect(x + width / 2, y + width / 2, Math.max(1, view.scale - width), Math.max(1, view.scale - width));
  ctx.restore();
}

function handleWheel(event: WheelEvent): void {
  event.preventDefault();
  const point = localPoint(event.clientX, event.clientY);
  const multiplier = event.deltaY < 0 ? 1.16 : 1 / 1.16;
  zoomAt(point.x, point.y, view.scale * multiplier);
}

function handlePointerDown(event: PointerEvent): void {
  event.preventDefault();
  frameRef.value?.setPointerCapture(event.pointerId);
  const point = localPoint(event.clientX, event.clientY);
  pointers.set(event.pointerId, { ...point, pointerType: event.pointerType });

  if (pointers.size >= 2 && event.pointerType !== 'mouse') {
    clearPendingTouchPaint();
    multiTouchLocked.value = true;
    touchGestureHadMultiTouch.value = true;
    beginPinch();
    return;
  }

  if (event.pointerType === 'mouse') {
    const hit = hitCell(point);
    const mode = event.button === 0 && props.paintEnabled ? 'paint' : 'pan';
    mouseDrag.value = {
      pointerId: event.pointerId,
      button: event.button,
      mode,
      start: point,
      startOffsetX: view.offsetX,
      startOffsetY: view.offsetY,
      moved: false,
      lastPaintedKey: ''
    };
    hoverCell.value = hit;
    if (mode === 'paint' && hit) {
      setCursor(hit.row, hit.col);
      applyCell(hit.row, hit.col, mouseDrag.value);
    }
    scheduleOverlayDraw();
    return;
  }

  const hit = hitCell(point);
  if (hit) {
    setCursor(hit.row, hit.col);
    lastTouchPaintKey = '';
    if (canTouchApply()) {
      schedulePendingTouchPaint(hit.row, hit.col);
    }
  }
}

function handlePointerMove(event: PointerEvent): void {
  event.preventDefault();
  const point = localPoint(event.clientX, event.clientY);
  if (pointers.has(event.pointerId)) {
    pointers.set(event.pointerId, { ...point, pointerType: event.pointerType });
  }

  if (pinch.value && pointers.size >= 2) {
    updatePinch();
    return;
  }

  const drag = mouseDrag.value;
  if (event.pointerType === 'mouse' && drag?.pointerId === event.pointerId) {
    if (drag.mode === 'paint') {
      const hit = hitCell(point);
      hoverCell.value = hit;
      if (hit) {
        setCursor(hit.row, hit.col);
        applyCell(hit.row, hit.col, drag);
      }
      return;
    }
    const dx = point.x - drag.start.x;
    const dy = point.y - drag.start.y;
    if (Math.hypot(dx, dy) > 4 || drag.button !== 0) {
      drag.moved = true;
      view.offsetX = drag.startOffsetX + dx;
      view.offsetY = drag.startOffsetY + dy;
      clampCurrentView();
      scheduleBaseDraw();
      scheduleOverlayDraw();
    }
    return;
  }

  if (event.pointerType === 'mouse') {
    hoverCell.value = hitCell(point);
    scheduleOverlayDraw();
    return;
  }

  const hit = hitCell(point);
  if (hit) {
    setCursor(hit.row, hit.col);
    if (multiTouchLocked.value) {
      return;
    }
    if (pendingTouchPaintTimer !== undefined) {
      flushPendingTouchPaint(hit.row, hit.col);
      return;
    }
    if (canTouchApply()) {
      applyTouchCell(hit.row, hit.col);
    }
  }
}

function handlePointerUp(event: PointerEvent): void {
  event.preventDefault();
  const point = localPoint(event.clientX, event.clientY);
  frameRef.value?.releasePointerCapture(event.pointerId);
  pointers.delete(event.pointerId);
  if (event.pointerType !== 'mouse') {
    const hadPendingTouchPaint = pendingTouchPaintTimer !== undefined;
    lastTouchPaintKey = '';
    if (!touchGestureHadMultiTouch.value && hadPendingTouchPaint) {
      const hit = hitCell(point);
      if (hit) {
        setCursor(hit.row, hit.col);
        flushPendingTouchPaint(hit.row, hit.col);
      }
    } else {
      clearPendingTouchPaint();
    }
  }

  if (pinch.value) {
    if (pointers.size < 2) {
      pinch.value = null;
      pinchSettledAt.value = Date.now() + PINCH_SETTLE_MS;
    }
    if (touchGestureHadMultiTouch.value) {
      finishOrContinueMultiTouchLock();
    }
    return;
  }

  if (event.pointerType !== 'mouse' && touchGestureHadMultiTouch.value) {
    finishOrContinueMultiTouchLock();
    return;
  }

  const drag = mouseDrag.value;
  if (event.pointerType === 'mouse' && drag?.pointerId === event.pointerId) {
    mouseDrag.value = null;
    if (drag.mode === 'paint') {
      return;
    }
    if (!drag.moved && drag.button === 0) {
      const hit = hitCell(point);
      if (hit) {
        setCursor(hit.row, hit.col);
        if (props.paintEnabled) {
          applyCell(hit.row, hit.col);
        }
      }
    }
  }
}

function handlePointerCancel(event: PointerEvent): void {
  pointers.delete(event.pointerId);
  mouseDrag.value = null;
  pinch.value = null;
  clearPendingTouchPaint();
  lastTouchPaintKey = '';
  pinchSettledAt.value = Date.now() + PINCH_SETTLE_MS;
  if (event.pointerType !== 'mouse') {
    finishOrContinueMultiTouchLock();
  }
}

function beginPinch(): void {
  const active = Array.from(pointers.entries()).slice(0, 2);
  if (active.length < 2) {
    return;
  }
  const first = active[0][1];
  const second = active[1][1];
  const center = midpoint(first, second);
  pinch.value = {
    pointerIds: [active[0][0], active[1][0]],
    startDistance: Math.max(1, distance(first, second)),
    startScale: view.scale,
    anchorGrid: screenToGridPoint(center)
  };
}

function updatePinch(): void {
  const state = pinch.value;
  if (!state) {
    return;
  }
  const first = pointers.get(state.pointerIds[0]);
  const second = pointers.get(state.pointerIds[1]);
  if (!first || !second) {
    return;
  }
  const nextDistance = Math.max(1, distance(first, second));
  const center = midpoint(first, second);
  const nextScale = clamp(state.startScale * (nextDistance / state.startDistance), minScale.value, MAX_SCALE);
  view.scale = nextScale;
  view.offsetX = center.x - state.anchorGrid.x * nextScale;
  view.offsetY = center.y - state.anchorGrid.y * nextScale;
  clampCurrentView();
  scheduleBaseDraw();
  scheduleOverlayDraw();
}

function zoomAt(screenX: number, screenY: number, rawScale: number): void {
  const anchor = screenToGridPoint({ x: screenX, y: screenY });
  const nextScale = clamp(rawScale, minScale.value, MAX_SCALE);
  view.scale = nextScale;
  view.offsetX = screenX - anchor.x * nextScale;
  view.offsetY = screenY - anchor.y * nextScale;
  clampCurrentView();
  scheduleBaseDraw();
  scheduleOverlayDraw();
}

function setCursor(row: number, col: number): void {
  const next = clampCursor(row, col);
  if (next.row === cursor.value.row && next.col === cursor.value.col) {
    return;
  }
  cursor.value = next;
  emitCursor();
  scheduleOverlayDraw();
}

function applyCell(row: number, col: number, drag?: MouseDrag): void {
  if (props.activeTool === 'none') {
    return;
  }
  if (props.activeTool === 'paint' && !props.selectedColor) {
    return;
  }
  const color = props.activeTool === 'erase' ? null : props.selectedColor;
  const paintKey = cellPaintKey(row, col, color);
  if (drag) {
    if (drag.lastPaintedKey === paintKey) {
      return;
    }
    drag.lastPaintedKey = paintKey;
  }
  emit('applyCell', { row, col, color });
}

function applyTouchCell(row: number, col: number): void {
  if (props.activeTool === 'none') {
    return;
  }
  if (props.activeTool === 'paint' && !props.selectedColor) {
    return;
  }
  const color = props.activeTool === 'erase' ? null : props.selectedColor;
  const paintKey = cellPaintKey(row, col, color);
  if (lastTouchPaintKey === paintKey) {
    return;
  }
  lastTouchPaintKey = paintKey;
  applyCell(row, col);
}

function canTouchApply(): boolean {
  return props.paintEnabled && !multiTouchLocked.value && Date.now() > pinchSettledAt.value;
}

function cellPaintKey(row: number, col: number, color: ColorRef | null): string {
  return `${row}:${col}:${color?.code || 'erase'}`;
}

function schedulePendingTouchPaint(row: number, col: number): void {
  clearPendingTouchPaint();
  pendingTouchPaintTimer = window.setTimeout(() => {
    pendingTouchPaintTimer = undefined;
    if (pointers.size === 1 && canTouchApply()) {
      applyTouchCell(row, col);
    }
  }, 80);
}

function flushPendingTouchPaint(row: number, col: number): void {
  clearPendingTouchPaint();
  if (pointers.size === 1 && canTouchApply()) {
    applyTouchCell(row, col);
  }
}

function clearPendingTouchPaint(): void {
  if (pendingTouchPaintTimer !== undefined) {
    window.clearTimeout(pendingTouchPaintTimer);
    pendingTouchPaintTimer = undefined;
  }
}

function finishOrContinueMultiTouchLock(): void {
  clearPendingTouchPaint();
  if (pointers.size > 0) {
    multiTouchLocked.value = true;
    return;
  }
  pinchSettledAt.value = Date.now() + PINCH_SETTLE_MS;
  window.setTimeout(() => {
    if (pointers.size === 0 && Date.now() >= pinchSettledAt.value) {
      multiTouchLocked.value = false;
      touchGestureHadMultiTouch.value = false;
      lastTouchPaintKey = '';
    }
  }, PINCH_SETTLE_MS);
}

function emitCursor(): void {
  emit('cursorChange', {
    row: cursor.value.row,
    col: cursor.value.col,
    cell: props.pattern.grid[cursor.value.row]?.[cursor.value.col] || null
  });
}

function localPoint(clientX: number, clientY: number): Point {
  const rect = frameRef.value?.getBoundingClientRect();
  return {
    x: clientX - (rect?.left || 0),
    y: clientY - (rect?.top || 0)
  };
}

function screenToGridPoint(point: Point): Point {
  return {
    x: (point.x - view.offsetX) / view.scale,
    y: (point.y - view.offsetY) / view.scale
  };
}

function hitCell(point: Point): { row: number; col: number } | null {
  const gridPoint = screenToGridPoint(point);
  const col = Math.floor(gridPoint.x);
  const row = Math.floor(gridPoint.y);
  if (row < 0 || col < 0 || row >= rows.value || col >= cols.value) {
    return null;
  }
  return { row, col };
}

function cellCenterToScreen(row: number, col: number): Point {
  return {
    x: view.offsetX + (col + 0.5) * view.scale,
    y: view.offsetY + (row + 0.5) * view.scale
  };
}

function clampCurrentView(): void {
  if (!rows.value || !cols.value) {
    return;
  }
  const gridW = cols.value * view.scale;
  const gridH = rows.value * view.scale;
  if (gridW <= canvasSize.width) {
    view.offsetX = (canvasSize.width - gridW) / 2;
  } else {
    view.offsetX = clamp(view.offsetX, canvasSize.width - gridW, 0);
  }
  if (gridH <= canvasSize.height) {
    view.offsetY = (canvasSize.height - gridH) / 2;
  } else {
    view.offsetY = clamp(view.offsetY, canvasSize.height - gridH, 0);
  }
}

function clampCursor(row: number, col: number): { row: number; col: number } {
  return {
    row: clamp(row, 0, Math.max(rows.value - 1, 0)),
    col: clamp(col, 0, Math.max(cols.value - 1, 0))
  };
}

function visibleBounds(padding = 0): { rowStart: number; rowEnd: number; colStart: number; colEnd: number } {
  const colStart = clamp(Math.floor((-view.offsetX) / view.scale) - padding, 0, cols.value);
  const rowStart = clamp(Math.floor((-view.offsetY) / view.scale) - padding, 0, rows.value);
  const colEnd = clamp(Math.ceil((canvasSize.width - view.offsetX) / view.scale) + padding, 0, cols.value);
  const rowEnd = clamp(Math.ceil((canvasSize.height - view.offsetY) / view.scale) + padding, 0, rows.value);
  return { rowStart, rowEnd, colStart, colEnd };
}

function midpoint(first: Point, second: Point): Point {
  return {
    x: (first.x + second.x) / 2,
    y: (first.y + second.y) / 2
  };
}

function distance(first: Point, second: Point): number {
  return Math.hypot(first.x - second.x, first.y - second.y);
}

function crisp(value: number): number {
  return Math.round(value) + 0.5;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

defineExpose({
  paintAtCursor,
  resetView,
  zoomIn,
  zoomOut,
  scaleLabel
});
</script>

<template>
  <div
    ref="frameRef"
    class="pattern-editor"
    @contextmenu.prevent
    @wheel="handleWheel"
    @pointerdown="handlePointerDown"
    @pointermove="handlePointerMove"
    @pointerup="handlePointerUp"
    @pointercancel="handlePointerCancel"
    @pointerleave="hoverCell = null"
  >
    <canvas ref="baseCanvasRef" class="pattern-editor__canvas" aria-label="拼豆图纸画布"></canvas>
    <canvas ref="overlayCanvasRef" class="pattern-editor__overlay" aria-hidden="true"></canvas>

    <div class="pattern-editor__hud" aria-live="polite">
      <span>{{ cursor.row + 1 }}行 {{ cursor.col + 1 }}列</span>
      <strong>{{ cursorCode }}</strong>
      <em>选中 {{ selectedCode }}</em>
    </div>

    <div v-if="paintEnabled" class="pattern-editor__paint-mode">
      {{ activeTool === 'erase' ? '擦除中' : '上色中' }}
    </div>
  </div>
</template>

<style scoped>
.pattern-editor {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border-radius: 22px;
  background:
    linear-gradient(45deg, rgba(237, 228, 218, 0.34) 25%, transparent 25%),
    linear-gradient(-45deg, rgba(237, 228, 218, 0.34) 25%, transparent 25%),
    #fffaf5;
  touch-action: none;
  overscroll-behavior: none;
  user-select: none;
  -webkit-user-select: none;
}

.pattern-editor__canvas,
.pattern-editor__overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}

.pattern-editor__overlay {
  z-index: 2;
  pointer-events: none;
}

.pattern-editor__hud {
  position: absolute;
  left: 12px;
  top: 12px;
  z-index: 5;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: min(360px, calc(100% - 24px));
  border: 1px solid rgba(255, 142, 83, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 10px 24px rgba(45, 45, 45, 0.1);
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
  padding: 8px 10px;
  pointer-events: none;
}

.pattern-editor__hud strong {
  color: var(--pd-fg-1);
  white-space: nowrap;
}

.pattern-editor__hud em {
  overflow: hidden;
  max-width: 120px;
  color: var(--pd-orange);
  font-style: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pattern-editor__paint-mode {
  position: absolute;
  right: 12px;
  top: 12px;
  z-index: 5;
  border-radius: 999px;
  background: var(--pd-gradient-warm);
  box-shadow: var(--pd-shadow-cta);
  color: #fff;
  font-size: 12px;
  font-weight: 900;
  padding: 8px 11px;
  pointer-events: none;
}

@media (max-width: 560px) {
  .pattern-editor {
    border-radius: 18px;
  }

  .pattern-editor__hud {
    left: 10px;
    top: 10px;
    gap: 6px;
    font-size: 11px;
    padding: 7px 9px;
  }

  .pattern-editor__hud em {
    max-width: 82px;
  }
}
</style>
