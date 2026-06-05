<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';

import { saveArtworkPattern } from '../api';
import PatternEditorCanvas from '../components/PatternEditor.vue';
import type { ColorRef, PatternSheet } from '../api/types';
import { useGenerationStore } from '../stores/generation';
import { useSWRCacheStore } from '../stores/swrCache';
import {
  applyCellPatch,
  cloneColor,
  cloneColorOrNull,
  clonePattern,
  paletteRowsForPattern,
  recalculatePattern,
  type CellPatch
} from '../utils/patternEditing';

type SaveStatus = 'idle' | 'dirty' | 'saving' | 'saved' | 'error';

const AUTOSAVE_DELAY_MS = 1600;
const MAX_PATCH_STACK = 240;

const route = useRoute();
const router = useRouter();
const generation = useGenerationStore();
const swrCache = useSWRCacheStore();
const editorRef = ref<InstanceType<typeof PatternEditorCanvas> | null>(null);
const loading = ref(false);
const error = ref('');
const editablePattern = ref<PatternSheet | null>(null);
const availablePalette = ref<ColorRef[]>([]);
const selectedColor = ref<ColorRef | null>(null);
const cursorInfo = ref<{ row: number; col: number; cell: ColorRef | null }>({ row: 0, col: 0, cell: null });
const undoStack = ref<CellPatch[]>([]);
const redoStack = ref<CellPatch[]>([]);
const isDirty = ref(false);
const saveStatus = ref<SaveStatus>('idle');
const saveError = ref('');
const continuousPaint = ref(false);
const patternKey = ref(0);
const paintRevision = ref(0);
const lastPatch = ref<CellPatch | null>(null);
const dirtyVersion = ref(0);
const savedVersion = ref(0);

let autosaveTimer: number | undefined;

const artworkId = computed(() => String(route.params.id || ''));
const pattern = computed(() => editablePattern.value);
const rows = computed(() => pattern.value?.grid.length || 0);
const cols = computed(() => Math.max(...(pattern.value?.grid.map((row) => row.length) || [0]), 0));
const beadTotal = computed(() => pattern.value?.bead_total || 0);
const colorTotal = computed(() => pattern.value?.palette_used.length || 0);
const paletteRows = computed(() => paletteRowsForPattern(pattern.value));
const canUndo = computed(() => undoStack.value.length > 0);
const canRedo = computed(() => redoStack.value.length > 0);
const saveStatusText = computed(() => {
  if (saveStatus.value === 'saving') {
    return '保存中';
  }
  if (saveStatus.value === 'saved') {
    return '已保存';
  }
  if (saveStatus.value === 'error') {
    return '保存失败';
  }
  if (isDirty.value) {
    return '有未保存修改';
  }
  return '已同步';
});

onMounted(() => {
  void loadArtwork();
  window.addEventListener('beforeunload', handleBeforeUnload);
  window.addEventListener('keydown', handleKeydown);
});

onBeforeUnmount(() => {
  clearAutosaveTimer();
  window.removeEventListener('beforeunload', handleBeforeUnload);
  window.removeEventListener('keydown', handleKeydown);
});

onBeforeRouteLeave(() => {
  if (isDirty.value && saveStatus.value !== 'saving') {
    return window.confirm('图纸还有未保存的修改，确定要离开吗？');
  }
  return true;
});

async function loadArtwork(): Promise<void> {
  const id = artworkId.value;
  if (!id || isDirty.value) {
    return;
  }
  const snapshot = swrCache.getArtworkSnapshot(id);
  if (snapshot) {
    applyLoadedPattern(snapshot.data.pattern_data);
    generation.applyArtwork(snapshot.data);
    void swrCache.revalidateArtwork(id).then((artwork) => {
      if (!isDirty.value) {
        generation.applyArtwork(artwork);
        applyLoadedPattern(artwork.pattern_data);
      }
    }).catch(() => undefined);
    return;
  }

  loading.value = true;
  error.value = '';
  try {
    const artwork = await generation.loadArtwork(id);
    applyLoadedPattern(artwork.pattern_data);
  } catch (loadError) {
    error.value = loadError instanceof Error ? loadError.message : '编辑器加载失败，请回到作品集重新打开。';
  } finally {
    loading.value = false;
  }
}

function applyLoadedPattern(nextPattern: PatternSheet): void {
  const normalized = recalculatePattern(clonePattern(nextPattern));
  editablePattern.value = normalized;
  availablePalette.value = uniquePalette(normalized.palette_used);
  selectedColor.value = availablePalette.value[0] ? cloneColor(availablePalette.value[0]) : null;
  undoStack.value = [];
  redoStack.value = [];
  isDirty.value = false;
  saveStatus.value = 'idle';
  saveError.value = '';
  dirtyVersion.value = 0;
  savedVersion.value = 0;
  lastPatch.value = null;
  paintRevision.value = 0;
  patternKey.value += 1;
}

function handlePaint(payload: { row: number; col: number; color: ColorRef }): void {
  applyPaint(payload.row, payload.col, payload.color);
}

function applyPaint(row: number, col: number, color: ColorRef): void {
  const sheet = editablePattern.value;
  const current = sheet?.grid[row]?.[col];
  if (!sheet || !sheet.grid[row] || col < 0 || col >= sheet.grid[row].length) {
    return;
  }
  if (current?.code === color.code) {
    return;
  }
  const patch: CellPatch = {
    row,
    col,
    before: cloneColorOrNull(current || null),
    after: cloneColor(color)
  };
  editablePattern.value = applyCellPatch(sheet, patch, true);
  availablePalette.value = uniquePalette([...availablePalette.value, cloneColor(color)]);
  selectedColor.value = cloneColor(color);
  undoStack.value.push(patch);
  if (undoStack.value.length > MAX_PATCH_STACK) {
    undoStack.value.shift();
  }
  redoStack.value = [];
  markEdited(patch);
}

function undoEdit(): void {
  const patch = undoStack.value.pop();
  const sheet = editablePattern.value;
  if (!patch || !sheet) {
    return;
  }
  editablePattern.value = applyCellPatch(sheet, patch, false);
  redoStack.value.push(patch);
  markEdited({ ...patch, before: patch.after, after: patch.before });
}

function redoEdit(): void {
  const patch = redoStack.value.pop();
  const sheet = editablePattern.value;
  if (!patch || !sheet) {
    return;
  }
  editablePattern.value = applyCellPatch(sheet, patch, true);
  undoStack.value.push(patch);
  markEdited(patch);
}

function markEdited(patch: CellPatch): void {
  lastPatch.value = patch;
  paintRevision.value += 1;
  dirtyVersion.value += 1;
  isDirty.value = true;
  saveStatus.value = 'dirty';
  saveError.value = '';
  scheduleAutosave();
}

function chooseColor(color: ColorRef): void {
  selectedColor.value = cloneColor(color);
}

function paintCursor(): void {
  editorRef.value?.paintAtCursor();
}

function zoomIn(): void {
  editorRef.value?.zoomIn();
}

function zoomOut(): void {
  editorRef.value?.zoomOut();
}

function resetView(): void {
  editorRef.value?.resetView();
}

function updateCursor(payload: { row: number; col: number; cell: ColorRef | null }): void {
  cursorInfo.value = payload;
}

function scheduleAutosave(): void {
  clearAutosaveTimer();
  autosaveTimer = window.setTimeout(() => {
    void saveNow(false);
  }, AUTOSAVE_DELAY_MS);
}

async function saveNow(manual: boolean): Promise<void> {
  const id = artworkId.value;
  const sheet = editablePattern.value;
  if (!id || !sheet) {
    return;
  }
  if (!isDirty.value && !manual) {
    return;
  }
  clearAutosaveTimer();
  const versionAtStart = dirtyVersion.value;
  saveStatus.value = 'saving';
  saveError.value = '';
  try {
    const saved = await saveArtworkPattern(id, recalculatePattern(clonePattern(sheet)));
    swrCache.setArtwork(saved.artwork);
    swrCache.invalidateGallery();
    generation.applyArtwork(saved.artwork);
    if (dirtyVersion.value === versionAtStart) {
      savedVersion.value = versionAtStart;
      isDirty.value = false;
      saveStatus.value = 'saved';
      saveError.value = '';
    } else {
      saveStatus.value = 'dirty';
      scheduleAutosave();
    }
  } catch (saveFailure) {
    saveStatus.value = 'error';
    saveError.value = saveFailure instanceof Error ? saveFailure.message : '保存失败，请稍后再试。';
  }
}

async function goBackToResult(): Promise<void> {
  if (isDirty.value) {
    await saveNow(true);
  }
  await router.push({ name: 'result', params: { id: artworkId.value } });
}

function handleBeforeUnload(event: BeforeUnloadEvent): void {
  if (!isDirty.value) {
    return;
  }
  event.preventDefault();
  event.returnValue = '';
}

function handleKeydown(event: KeyboardEvent): void {
  const key = event.key.toLowerCase();
  if ((event.ctrlKey || event.metaKey) && key === 'z') {
    event.preventDefault();
    if (event.shiftKey) {
      redoEdit();
    } else {
      undoEdit();
    }
    return;
  }
  if ((event.ctrlKey || event.metaKey) && key === 'y') {
    event.preventDefault();
    redoEdit();
    return;
  }
  if ((event.ctrlKey || event.metaKey) && key === 's') {
    event.preventDefault();
    void saveNow(true);
    return;
  }
  if (key === '+' || key === '=') {
    zoomIn();
    return;
  }
  if (key === '-') {
    zoomOut();
  }
}

function clearAutosaveTimer(): void {
  if (autosaveTimer) {
    window.clearTimeout(autosaveTimer);
    autosaveTimer = undefined;
  }
}

function uniquePalette(colors: ColorRef[]): ColorRef[] {
  const seen = new Set<string>();
  const result: ColorRef[] = [];
  for (const color of colors) {
    if (!seen.has(color.code)) {
      seen.add(color.code);
      result.push(cloneColor(color));
    }
  }
  return result;
}
</script>

<template>
  <section class="editor-page">
    <template v-if="loading">
      <div class="editor-state">
        <p class="eyebrow">正在打开</p>
        <h1>读取图纸中</h1>
      </div>
    </template>

    <template v-else-if="error">
      <div class="editor-state">
        <p class="eyebrow">编辑器加载失败</p>
        <h1>暂时打不开这个图纸</h1>
        <p>{{ error }}</p>
        <RouterLink class="pd-btn pd-btn--primary" to="/works">回作品集</RouterLink>
      </div>
    </template>

    <template v-else-if="pattern">
      <header class="editor-topbar">
        <button class="editor-back" type="button" @click="goBackToResult">返回</button>
        <div class="editor-title">
          <strong>图纸编辑器</strong>
          <span>{{ cols }} × {{ rows }} · {{ beadTotal }} 豆 · {{ colorTotal }} 色</span>
        </div>
        <div class="editor-topbar__actions">
          <button type="button" :disabled="!canUndo" @click="undoEdit">撤销</button>
          <button type="button" :disabled="!canRedo" @click="redoEdit">重做</button>
          <button type="button" class="editor-save" :disabled="saveStatus === 'saving'" @click="saveNow(true)">
            {{ saveStatus === 'saving' ? '保存中' : '保存' }}
          </button>
        </div>
      </header>

      <main class="editor-canvas-shell">
        <PatternEditorCanvas
          ref="editorRef"
          :pattern="pattern"
          :palette="availablePalette"
          :selected-color="selectedColor"
          :continuous-paint="continuousPaint"
          :pattern-key="patternKey"
          :paint-revision="paintRevision"
          :last-patch="lastPatch"
          @paint="handlePaint"
          @cursor-change="updateCursor"
        />
      </main>

      <footer class="editor-tray">
        <section class="editor-tray__status">
          <div>
            <strong>{{ cursorInfo.row + 1 }}行 {{ cursorInfo.col + 1 }}列</strong>
            <span>{{ cursorInfo.cell?.code || '空格' }} · {{ saveStatusText }}</span>
          </div>
          <p v-if="saveError">{{ saveError }}</p>
        </section>

        <section class="editor-tools" aria-label="编辑工具">
          <button type="button" @click="zoomOut">-</button>
          <button type="button" @click="zoomIn">+</button>
          <button type="button" @click="resetView">复位</button>
          <button
            type="button"
            class="editor-tool-toggle"
            :class="{ 'editor-tool-toggle--active': continuousPaint }"
            :aria-pressed="continuousPaint"
            @click="continuousPaint = !continuousPaint"
          >
            连续涂
          </button>
        </section>

        <section class="editor-palette" aria-label="色盘">
          <button
            v-for="color in availablePalette"
            :key="color.code"
            type="button"
            class="editor-color"
            :class="{ 'editor-color--active': selectedColor?.code === color.code }"
            :title="`${color.code} · ${color.name_cn}`"
            @click="chooseColor(color)"
          >
            <span :style="{ backgroundColor: color.hex }"></span>
            <strong>{{ color.code }}</strong>
          </button>
        </section>

        <section class="editor-place">
          <button class="editor-place__button" type="button" :disabled="!selectedColor" @click="paintCursor">
            上色
          </button>
          <div class="editor-place__selected">
            <span :style="{ backgroundColor: selectedColor?.hex || '#fff' }"></span>
            <strong>{{ selectedColor?.code || '未选色' }}</strong>
          </div>
        </section>
      </footer>

      <aside class="editor-mini" aria-label="色号清单">
        <div v-for="row in paletteRows.slice(0, 6)" :key="row.color.code">
          <span :style="{ backgroundColor: row.color.hex }"></span>
          <strong>{{ row.color.code }}</strong>
          <em>{{ row.count }}</em>
        </div>
      </aside>
    </template>
  </section>
</template>

<style scoped>
.editor-page {
  width: 100%;
  min-height: 100dvh;
  height: 100dvh;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
  background:
    radial-gradient(circle at 12% 12%, rgba(255, 176, 136, 0.24), transparent 28%),
    radial-gradient(circle at 92% 10%, rgba(184, 230, 201, 0.24), transparent 30%),
    var(--pd-bg);
  overscroll-behavior: none;
}

.editor-state {
  width: min(100% - 32px, 620px);
  align-self: center;
  justify-self: center;
  border: 1px solid rgba(237, 228, 218, 0.86);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--pd-shadow-float);
  padding: 34px;
  text-align: center;
}

.editor-state h1 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(30px, 5vw, 42px);
}

.editor-topbar {
  min-width: 0;
  min-height: 62px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(237, 228, 218, 0.82);
  background: rgba(255, 249, 245, 0.92);
  padding: 10px clamp(12px, 3vw, 22px);
  backdrop-filter: blur(16px);
}

.editor-back,
.editor-topbar__actions button,
.editor-tools button,
.editor-color,
.editor-place__button {
  cursor: pointer;
  font: inherit;
  font-weight: 900;
  transition:
    border-color 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    color 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.editor-back,
.editor-topbar__actions button,
.editor-tools button {
  min-height: 40px;
  border: 1px solid rgba(255, 142, 83, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  color: var(--pd-fg-1);
  padding: 0 14px;
}

.editor-back:hover,
.editor-topbar__actions button:hover:not(:disabled),
.editor-tools button:hover {
  border-color: rgba(255, 142, 83, 0.5);
  box-shadow: 0 10px 22px rgba(255, 142, 83, 0.13);
  transform: translateY(-1px);
}

.editor-title {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.editor-title strong {
  overflow: hidden;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: 20px;
  font-weight: 900;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-title span,
.editor-tray__status span,
.editor-tray__status p {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
}

.editor-topbar__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.editor-topbar__actions button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
  transform: none;
}

.editor-save {
  border-color: transparent !important;
  background: var(--pd-gradient-warm) !important;
  color: #fff !important;
  box-shadow: var(--pd-shadow-cta);
}

.editor-canvas-shell {
  min-height: 0;
  padding: 10px;
}

.editor-tray {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(150px, 0.8fr) auto minmax(0, 1.4fr) minmax(132px, auto);
  align-items: center;
  gap: 10px;
  border-top: 1px solid rgba(237, 228, 218, 0.86);
  background: rgba(255, 249, 245, 0.94);
  padding: 10px clamp(10px, 3vw, 20px);
  box-shadow: 0 -12px 28px rgba(45, 45, 45, 0.06);
}

.editor-tray__status {
  min-width: 0;
}

.editor-tray__status strong,
.editor-tray__status span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-tray__status strong {
  color: var(--pd-fg-1);
  font-size: 14px;
  font-weight: 900;
}

.editor-tray__status p {
  margin: 2px 0 0;
  color: #c42535;
}

.editor-tools {
  display: flex;
  align-items: center;
  gap: 7px;
}

.editor-tools button {
  min-width: 42px;
  padding: 0 12px;
}

.editor-tool-toggle--active {
  border-color: transparent !important;
  background: var(--pd-gradient-warm) !important;
  color: #fff !important;
}

.editor-palette {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  overscroll-behavior-x: contain;
  padding: 3px 2px;
  scrollbar-width: thin;
}

.editor-color {
  flex: 0 0 auto;
  min-width: 62px;
  min-height: 52px;
  display: grid;
  place-items: center;
  gap: 3px;
  border: 1px solid var(--pd-stroke);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.86);
  color: var(--pd-fg-1);
  padding: 6px 8px;
}

.editor-color:hover,
.editor-color--active {
  border-color: rgba(255, 142, 83, 0.56);
  background: #fff;
  box-shadow: 0 10px 22px rgba(255, 142, 83, 0.13);
  transform: translateY(-1px);
}

.editor-color span,
.editor-place__selected span,
.editor-mini span {
  display: block;
  border: 1px solid rgba(45, 45, 45, 0.1);
  border-radius: 999px;
  box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.65);
}

.editor-color span {
  width: 24px;
  height: 24px;
}

.editor-color strong {
  font-size: 11px;
  line-height: 1;
  white-space: nowrap;
}

.editor-place {
  display: grid;
  grid-template-columns: minmax(86px, 1fr) auto;
  align-items: center;
  gap: 8px;
}

.editor-place__button {
  min-height: 54px;
  border: 1px solid transparent;
  border-radius: 20px;
  background: var(--pd-gradient);
  box-shadow: var(--pd-shadow-cta);
  color: #fff;
  padding: 0 20px;
}

.editor-place__button:hover:not(:disabled) {
  filter: brightness(1.03);
  transform: translateY(-1px);
}

.editor-place__button:disabled {
  cursor: not-allowed;
  opacity: 0.52;
}

.editor-place__selected {
  min-width: 52px;
  display: grid;
  justify-items: center;
  gap: 3px;
  color: var(--pd-fg-2);
  font-size: 11px;
  font-weight: 900;
}

.editor-place__selected span {
  width: 28px;
  height: 28px;
}

.editor-place__selected strong {
  white-space: nowrap;
}

.editor-mini {
  position: fixed;
  right: 14px;
  top: 76px;
  z-index: 3;
  width: 104px;
  display: grid;
  gap: 6px;
  border: 1px solid rgba(237, 228, 218, 0.76);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 14px 30px rgba(45, 45, 45, 0.1);
  padding: 8px;
  pointer-events: none;
}

.editor-mini div {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  align-items: center;
  gap: 5px;
  min-width: 0;
}

.editor-mini span {
  width: 18px;
  height: 18px;
}

.editor-mini strong,
.editor-mini em {
  overflow: hidden;
  color: var(--pd-fg-2);
  font-size: 10px;
  font-style: normal;
  font-weight: 900;
  line-height: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 860px) {
  .editor-topbar {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .editor-topbar__actions {
    grid-column: 1 / -1;
    justify-content: stretch;
  }

  .editor-topbar__actions button {
    flex: 1 1 0;
  }

  .editor-tray {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .editor-tools {
    justify-content: flex-end;
  }

  .editor-palette,
  .editor-place {
    grid-column: 1 / -1;
  }

  .editor-mini {
    display: none;
  }
}

@media (max-width: 560px) {
  .editor-page {
    grid-template-rows: auto minmax(0, 1fr) auto;
  }

  .editor-topbar {
    min-height: 54px;
    gap: 8px;
    padding: 8px 10px;
  }

  .editor-back,
  .editor-topbar__actions button,
  .editor-tools button {
    min-height: 38px;
    padding: 0 11px;
  }

  .editor-title strong {
    font-size: 18px;
  }

  .editor-title span {
    font-size: 11px;
  }

  .editor-canvas-shell {
    padding: 6px;
  }

  .editor-tray {
    gap: 8px;
    padding: 8px 8px max(8px, env(safe-area-inset-bottom));
  }

  .editor-tools {
    gap: 5px;
  }

  .editor-tools button {
    min-width: 38px;
  }

  .editor-color {
    min-width: 58px;
    min-height: 48px;
    border-radius: 14px;
    padding: 5px 7px;
  }

  .editor-place {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .editor-place__button {
    min-height: 52px;
    border-radius: 18px;
    font-size: 18px;
  }
}
</style>
