<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';

import { saveArtworkPattern } from '../api';
import PatternEditorCanvas from '../components/PatternEditor.vue';
import type { ColorRef, PatternSheet } from '../api/types';
import mardPaletteJson from '../assets/colormap/mard-5mm.json';
import paletteManifestJson from '../assets/colormap/manifest.json';
import { useGenerationStore } from '../stores/generation';
import { useSWRCacheStore } from '../stores/swrCache';
import {
  applyBatchPatch,
  applyCellPatch,
  cloneColor,
  cloneColorOrNull,
  clonePattern,
  paletteRowsForPattern,
  recalculatePattern,
  type CellPatch,
  type EditPatch
} from '../utils/patternEditing';

type SaveStatus = 'idle' | 'dirty' | 'saving' | 'saved' | 'error';
type EditorTool = 'paint' | 'erase';
type CatalogColor = ColorRef & { category: string };
type ColorModalMode = 'choose' | 'replace';

interface PendingReplace {
  source: ColorRef;
  target: ColorRef;
  count: number;
}

const AUTOSAVE_DELAY_MS = 1600;
const MAX_PATCH_STACK = 240;
const COLOR_CATEGORY_ALL = '全部';

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
const activeTool = ref<EditorTool>('paint');
const paintEnabled = ref(false);
const isColorModalOpen = ref(false);
const colorModalMode = ref<ColorModalMode>('choose');
const colorSearch = ref('');
const activeCategory = ref(COLOR_CATEGORY_ALL);
const recentColors = ref<ColorRef[]>([]);
const cursorInfo = ref<{ row: number; col: number; cell: ColorRef | null }>({ row: 0, col: 0, cell: null });
const undoStack = ref<EditPatch[]>([]);
const redoStack = ref<EditPatch[]>([]);
const isDirty = ref(false);
const saveStatus = ref<SaveStatus>('idle');
const saveError = ref('');
const patternKey = ref(0);
const paintRevision = ref(0);
const lastPatch = ref<CellPatch | null>(null);
const dirtyVersion = ref(0);
const savedVersion = ref(0);
const replaceSourceColor = ref<ColorRef | null>(null);
const pendingReplace = ref<PendingReplace | null>(null);
const replaceMessage = ref('');

let autosaveTimer: number | undefined;

const artworkId = computed(() => String(route.params.id || ''));
const pattern = computed(() => editablePattern.value);
const rows = computed(() => pattern.value?.grid.length || 0);
const cols = computed(() => Math.max(...(pattern.value?.grid.map((row) => row.length) || [0]), 0));
const beadTotal = computed(() => pattern.value?.bead_total || 0);
const colorTotal = computed(() => pattern.value?.palette_used.length || 0);
const paletteRows = computed(() => paletteRowsForPattern(pattern.value));
const fullPalette = computed(() => normalizeCatalog(mardPaletteJson as CatalogColor[]));
const paletteManifest = paletteManifestJson as {
  default_palette: string;
  palettes: Array<{ id: string; display_name: string; count: number; categories: string[] }>;
};
const currentPaletteMeta = computed(() => paletteManifest.palettes.find((item) => item.id === paletteManifest.default_palette));
const colorCategories = computed(() => [
  COLOR_CATEGORY_ALL,
  ...Array.from(new Set(fullPalette.value.map((color) => color.category))).sort((left, right) => (
    left.localeCompare(right, 'zh-Hans-CN')
  ))
]);
const filteredFullPalette = computed(() => {
  const keyword = colorSearch.value.trim().toLowerCase();
  return fullPalette.value.filter((color) => {
    const categoryMatched = activeCategory.value === COLOR_CATEGORY_ALL || color.category === activeCategory.value;
    if (!categoryMatched) {
      return false;
    }
    if (!keyword) {
      return true;
    }
    return color.code.toLowerCase().includes(keyword)
      || color.name_cn.toLowerCase().includes(keyword)
      || color.hex.toLowerCase().includes(keyword);
  });
});
const canUndo = computed(() => undoStack.value.length > 0);
const canRedo = computed(() => redoStack.value.length > 0);
const selectedColorUseCount = computed(() => (
  selectedColor.value ? (pattern.value?.color_counts[selectedColor.value.code] || 0) : 0
));
const canReplaceSelectedColor = computed(() => Boolean(selectedColor.value && selectedColorUseCount.value > 0));
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
  selectedColor.value = availablePalette.value[0]
    ? cloneColor(availablePalette.value[0])
    : (fullPalette.value[0] ? cloneColor(fullPalette.value[0]) : null);
  activeTool.value = 'paint';
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

function handleApplyCell(payload: { row: number; col: number; color: ColorRef | null }): void {
  applyCell(payload.row, payload.col, payload.color);
}

function applyCell(row: number, col: number, color: ColorRef | null): void {
  const sheet = editablePattern.value;
  const current = sheet?.grid[row]?.[col];
  if (!sheet || !sheet.grid[row] || col < 0 || col >= sheet.grid[row].length) {
    return;
  }
  if ((current?.code || null) === (color?.code || null)) {
    return;
  }
  const patch: CellPatch = {
    row,
    col,
    before: cloneColorOrNull(current || null),
    after: cloneColorOrNull(color)
  };
  editablePattern.value = applyCellPatch(sheet, patch, true);
  if (color) {
    availablePalette.value = uniquePalette([...availablePalette.value, cloneColor(color)]);
    selectedColor.value = cloneColor(color);
    rememberRecentColor(color);
  }
  syncAvailablePalette();
  undoStack.value.push({ kind: 'cell', patch });
  if (undoStack.value.length > MAX_PATCH_STACK) {
    undoStack.value.shift();
  }
  redoStack.value = [];
  markSingleCellEdited(patch);
}

function undoEdit(): void {
  const edit = undoStack.value.pop();
  const sheet = editablePattern.value;
  if (!edit || !sheet) {
    return;
  }
  editablePattern.value = applyEditPatch(sheet, edit, false);
  syncAvailablePalette();
  redoStack.value.push(edit);
  markAppliedEdit(edit, false);
}

function redoEdit(): void {
  const edit = redoStack.value.pop();
  const sheet = editablePattern.value;
  if (!edit || !sheet) {
    return;
  }
  editablePattern.value = applyEditPatch(sheet, edit, true);
  syncAvailablePalette();
  undoStack.value.push(edit);
  markAppliedEdit(edit, true);
}

function applyEditPatch(sheet: PatternSheet, edit: EditPatch, useAfter: boolean): PatternSheet {
  if (edit.kind === 'cell') {
    return applyCellPatch(sheet, edit.patch, useAfter);
  }
  return applyBatchPatch(sheet, edit.patches, useAfter);
}

function markAppliedEdit(edit: EditPatch, useAfter: boolean): void {
  if (edit.kind === 'cell') {
    const patch = edit.patch;
    markSingleCellEdited({
      ...patch,
      before: useAfter ? patch.before : patch.after,
      after: useAfter ? patch.after : patch.before
    });
    return;
  }
  markBatchEdited();
}

function markSingleCellEdited(patch: CellPatch): void {
  lastPatch.value = patch;
  paintRevision.value += 1;
  markDirty();
}

function markBatchEdited(): void {
  lastPatch.value = null;
  patternKey.value += 1;
  markDirty();
}

function markDirty(): void {
  dirtyVersion.value += 1;
  isDirty.value = true;
  saveStatus.value = 'dirty';
  saveError.value = '';
  scheduleAutosave();
}

function syncAvailablePalette(): void {
  if (!editablePattern.value) {
    availablePalette.value = [];
    return;
  }
  availablePalette.value = uniquePalette(editablePattern.value.palette_used);
}

function chooseColor(color: ColorRef): void {
  selectedColor.value = cloneColor(color);
  activeTool.value = 'paint';
  rememberRecentColor(color);
}

function chooseTool(tool: EditorTool): void {
  activeTool.value = tool;
}

function openColorModal(mode: ColorModalMode = 'choose'): void {
  colorModalMode.value = mode;
  if (mode === 'choose') {
    replaceSourceColor.value = null;
    pendingReplace.value = null;
    replaceMessage.value = '';
  }
  isColorModalOpen.value = true;
}

function closeColorModal(): void {
  isColorModalOpen.value = false;
  colorModalMode.value = 'choose';
  replaceSourceColor.value = null;
  pendingReplace.value = null;
  replaceMessage.value = '';
}

function chooseFullColor(color: ColorRef): void {
  if (colorModalMode.value === 'replace') {
    prepareReplaceTarget(color);
    return;
  }
  chooseColor(color);
  closeColorModal();
}

function openReplaceModal(): void {
  const source = selectedColor.value;
  if (!source || !selectedColorUseCount.value) {
    replaceMessage.value = '请先选中图纸中正在使用的颜色。';
    return;
  }
  replaceSourceColor.value = cloneColor(source);
  pendingReplace.value = null;
  replaceMessage.value = '';
  openColorModal('replace');
}

function prepareReplaceTarget(target: ColorRef): void {
  const source = replaceSourceColor.value;
  if (!source) {
    replaceMessage.value = '请先选择要替换的源色。';
    return;
  }
  if (source.code === target.code) {
    replaceMessage.value = '目标色和源色相同，不需要替换。';
    return;
  }
  const count = pattern.value?.color_counts[source.code] || 0;
  if (!count) {
    replaceMessage.value = `图纸里已经没有 ${source.code} 了。`;
    return;
  }
  pendingReplace.value = {
    source: cloneColor(source),
    target: cloneColor(target),
    count
  };
}

function cancelReplaceConfirm(): void {
  pendingReplace.value = null;
  replaceMessage.value = '';
}

function confirmReplaceColor(): void {
  const pending = pendingReplace.value;
  if (!pending) {
    return;
  }
  replaceColor(pending.source, pending.target);
}

function replaceColor(source: ColorRef, target: ColorRef): void {
  const sheet = editablePattern.value;
  if (!sheet) {
    return;
  }
  const patches: CellPatch[] = [];
  sheet.grid.forEach((row, rowIndex) => {
    row.forEach((cell, colIndex) => {
      if (cell?.code === source.code) {
        patches.push({
          row: rowIndex,
          col: colIndex,
          before: cloneColorOrNull(cell),
          after: cloneColor(target)
        });
      }
    });
  });
  if (!patches.length) {
    replaceMessage.value = `图纸里已经没有 ${source.code} 了。`;
    return;
  }

  editablePattern.value = applyBatchPatch(sheet, patches, true);
  syncAvailablePalette();
  selectedColor.value = cloneColor(target);
  rememberRecentColor(target);
  undoStack.value.push({ kind: 'batch', patches });
  if (undoStack.value.length > MAX_PATCH_STACK) {
    undoStack.value.shift();
  }
  redoStack.value = [];
  markBatchEdited();
  closeColorModal();
}

function rememberRecentColor(color: ColorRef): void {
  const next = [cloneColor(color), ...recentColors.value.filter((item) => item.code !== color.code)];
  recentColors.value = next.slice(0, 10);
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
    const saved = await saveArtworkPattern(id, recalculatePattern(clonePattern(sheet)), {
      renderPreview: manual
    });
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

function normalizeCatalog(colors: CatalogColor[]): CatalogColor[] {
  return colors.map((color) => ({
    ...cloneColor(color),
    category: color.category || '其他'
  }));
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
          :active-tool="activeTool"
          :paint-enabled="paintEnabled"
          :pattern-key="patternKey"
          :paint-revision="paintRevision"
          :last-patch="lastPatch"
          @apply-cell="handleApplyCell"
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
          <button
            type="button"
            class="editor-tool-square"
            :class="{ 'editor-tool-square--active': activeTool === 'paint' }"
            aria-label="画笔"
            :aria-pressed="activeTool === 'paint'"
            @click="chooseTool('paint')"
          >
            画
          </button>
          <button
            type="button"
            class="editor-tool-square"
            :class="{ 'editor-tool-square--active': activeTool === 'erase' }"
            aria-label="橡皮擦"
            :aria-pressed="activeTool === 'erase'"
            @click="chooseTool('erase')"
          >
            擦
          </button>
          <button
            type="button"
            class="editor-tool-toggle"
            :class="{ 'editor-tool-toggle--active': paintEnabled }"
            :aria-pressed="paintEnabled"
            @click="paintEnabled = !paintEnabled"
          >
            {{ paintEnabled ? '停止上色' : '开始上色' }}
          </button>
        </section>

        <section class="editor-palette" aria-label="已用色">
          <button
            v-for="row in paletteRows"
            :key="row.color.code"
            type="button"
            class="editor-color"
            :class="{ 'editor-color--active': activeTool === 'paint' && selectedColor?.code === row.color.code }"
            :title="`${row.color.code} · ${row.color.name_cn}`"
            @click="chooseColor(row.color)"
          >
            <span :style="{ backgroundColor: row.color.hex }"></span>
            <strong>{{ row.color.code }}</strong>
          </button>
          <button
            type="button"
            class="editor-color editor-color--all"
            @click="openColorModal()"
          >
            <span class="editor-color__rainbow"></span>
            <strong>全部颜色</strong>
          </button>
        </section>

        <section class="editor-current" aria-label="当前工具">
          <div class="editor-current__swatch" :class="{ 'editor-current__swatch--erase': activeTool === 'erase' }">
            <span v-if="activeTool === 'paint'" :style="{ backgroundColor: selectedColor?.hex || '#fff' }"></span>
          </div>
          <div>
            <strong>{{ activeTool === 'erase' ? '橡皮擦' : selectedColor?.code || '未选色' }}</strong>
            <span>{{ activeTool === 'erase' ? '点格变空白' : selectedColor?.name_cn || '从全部颜色选择' }}</span>
          </div>
          <button
            v-if="activeTool === 'paint'"
            type="button"
            class="editor-replace-trigger"
            :disabled="!canReplaceSelectedColor"
            @click="openReplaceModal"
          >
            替换为…
          </button>
        </section>
      </footer>

      <Teleport to="body">
        <div v-if="isColorModalOpen" class="editor-modal" @click.self="closeColorModal">
          <div class="editor-color-dialog" role="dialog" aria-modal="true" aria-label="全部颜色">
            <header class="editor-color-dialog__header">
              <div>
                <strong>{{ colorModalMode === 'replace' ? '选择替换目标色' : '全部颜色' }}</strong>
                <span v-if="colorModalMode === 'replace' && replaceSourceColor">
                  将 {{ replaceSourceColor.code }} 替换成新的色号
                </span>
                <span v-else>{{ currentPaletteMeta?.display_name || 'MARD' }} · {{ currentPaletteMeta?.count || fullPalette.length }} 色</span>
              </div>
              <button type="button" aria-label="关闭全部颜色" @click="closeColorModal">×</button>
            </header>

            <label class="editor-color-search">
              <span>搜索色号</span>
              <input v-model="colorSearch" type="search" placeholder="输入 A1 / 黑 / #FF" />
            </label>

            <section v-if="pendingReplace" class="editor-replace-confirm" aria-live="polite">
              <div>
                <span :style="{ backgroundColor: pendingReplace.source.hex }"></span>
                <strong>{{ pendingReplace.source.code }}</strong>
              </div>
              <em>→</em>
              <div>
                <span :style="{ backgroundColor: pendingReplace.target.hex }"></span>
                <strong>{{ pendingReplace.target.code }}</strong>
              </div>
              <p>将替换 {{ pendingReplace.count }} 格，撤销时会一次全部恢复。</p>
              <button type="button" @click="cancelReplaceConfirm">再选一个</button>
              <button type="button" class="editor-replace-confirm__primary" @click="confirmReplaceColor">确认替换</button>
            </section>
            <p v-else-if="replaceMessage" class="editor-replace-message">{{ replaceMessage }}</p>

            <section v-if="recentColors.length" class="editor-color-section" aria-label="最近使用">
              <h2>最近使用</h2>
              <div class="editor-color-grid editor-color-grid--recent">
                <button
                  v-for="color in recentColors"
                  :key="`recent-${color.code}`"
                  type="button"
                  class="editor-color-card"
                  @click="chooseFullColor(color)"
                >
                  <span :style="{ backgroundColor: color.hex }"></span>
                  <strong>{{ color.code }}</strong>
                </button>
              </div>
            </section>

            <nav class="editor-color-tabs" aria-label="色系">
              <button
                v-for="category in colorCategories"
                :key="category"
                type="button"
                :class="{ 'editor-color-tab--active': activeCategory === category }"
                @click="activeCategory = category"
              >
                {{ category }}
              </button>
            </nav>

            <div class="editor-color-grid" aria-label="MARD 色卡">
              <button
                v-for="color in filteredFullPalette"
                :key="color.code"
                type="button"
                class="editor-color-card"
                :class="{ 'editor-color-card--active': activeTool === 'paint' && selectedColor?.code === color.code }"
                @click="chooseFullColor(color)"
              >
                <span :style="{ backgroundColor: color.hex }"></span>
                <strong>{{ color.code }}</strong>
              </button>
            </div>
            <p v-if="!filteredFullPalette.length" class="editor-color-empty">没有找到这个颜色</p>
          </div>
        </div>
      </Teleport>
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
.editor-replace-trigger,
.editor-color,
.editor-color-card,
.editor-color-dialog button {
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
  flex-wrap: wrap;
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

.editor-tool-square {
  aspect-ratio: 1;
  border-radius: 14px !important;
  padding: 0 !important;
}

.editor-tool-square--active {
  border-color: transparent !important;
  background: var(--pd-gradient-warm) !important;
  box-shadow: var(--pd-shadow-cta);
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
.editor-color--active,
.editor-color--all {
  border-color: rgba(255, 142, 83, 0.56);
  background: #fff;
  box-shadow: 0 10px 22px rgba(255, 142, 83, 0.13);
  transform: translateY(-1px);
}

.editor-color span,
.editor-current__swatch span,
.editor-color-card span {
  display: block;
  border: 1px solid rgba(45, 45, 45, 0.1);
  border-radius: 999px;
  box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.65);
}

.editor-color span {
  width: 24px;
  height: 24px;
}

.editor-color__rainbow {
  background:
    conic-gradient(from 0deg, #ff6b6b, #ffd166, #79d98b, #69b7ff, #b58cff, #ff7ab6, #ff6b6b);
}

.editor-color strong {
  font-size: 11px;
  line-height: 1;
  white-space: nowrap;
}

.editor-current {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  min-width: 196px;
  min-height: 54px;
  border: 1px solid rgba(255, 142, 83, 0.18);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.86);
  padding: 7px 10px;
}

.editor-current__swatch {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 13px;
  background: #fff;
}

.editor-current__swatch span {
  width: 28px;
  height: 28px;
}

.editor-current__swatch--erase::before {
  width: 20px;
  height: 20px;
  display: block;
  border: 2px solid rgba(45, 45, 45, 0.66);
  border-radius: 6px;
  background:
    linear-gradient(135deg, transparent 44%, #ff6b9d 45%, #ff6b9d 55%, transparent 56%),
    #fffaf5;
  content: "";
}

.editor-current strong,
.editor-current span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-current strong {
  color: var(--pd-fg-1);
  font-size: 12px;
  line-height: 1.15;
}

.editor-current span {
  color: var(--pd-fg-2);
  font-size: 11px;
  font-weight: 900;
  line-height: 1.2;
}

.editor-replace-trigger {
  min-height: 34px;
  border: 1px solid rgba(255, 142, 83, 0.24);
  border-radius: 999px;
  background: rgba(255, 241, 232, 0.84);
  color: var(--pd-orange);
  font-size: 12px;
  padding: 0 11px;
  white-space: nowrap;
}

.editor-replace-trigger:hover:not(:disabled) {
  border-color: rgba(255, 142, 83, 0.52);
  box-shadow: 0 10px 22px rgba(255, 142, 83, 0.14);
  transform: translateY(-1px);
}

.editor-replace-trigger:disabled {
  cursor: not-allowed;
  opacity: 0.46;
}

.editor-modal {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  background: rgba(45, 45, 45, 0.24);
  padding: clamp(12px, 4vw, 28px);
  backdrop-filter: blur(10px);
}

.editor-color-dialog {
  width: min(920px, 100%);
  max-height: min(760px, calc(100dvh - 28px));
  display: grid;
  grid-template-rows: auto auto auto minmax(0, 1fr) auto;
  gap: 12px;
  border: 1px solid rgba(255, 142, 83, 0.22);
  border-radius: 28px;
  background:
    radial-gradient(circle at 12% 0%, rgba(255, 176, 136, 0.22), transparent 30%),
    rgba(255, 250, 247, 0.98);
  box-shadow: var(--pd-shadow-float);
  padding: clamp(14px, 3vw, 22px);
}

.editor-color-dialog__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.editor-color-dialog__header div {
  display: grid;
  gap: 2px;
}

.editor-color-dialog__header strong {
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(24px, 5vw, 34px);
  line-height: 1;
}

.editor-color-dialog__header span,
.editor-color-section h2,
.editor-color-empty {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
}

.editor-color-dialog__header button {
  width: 42px;
  height: 42px;
  border: 1px solid rgba(255, 142, 83, 0.24);
  border-radius: 999px;
  background: #fff;
  color: var(--pd-fg-1);
  font-size: 24px;
  line-height: 1;
}

.editor-color-search {
  display: grid;
  gap: 6px;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
}

.editor-color-search input {
  width: 100%;
  min-height: 46px;
  border: 1px solid var(--pd-stroke);
  border-radius: 16px;
  background: #fff;
  color: var(--pd-fg-1);
  font: inherit;
  font-weight: 900;
  outline: none;
  padding: 0 14px;
}

.editor-color-search input:focus {
  border-color: rgba(255, 142, 83, 0.58);
  box-shadow: 0 0 0 4px rgba(255, 142, 83, 0.12);
}

.editor-replace-confirm {
  display: grid;
  grid-template-columns: auto auto auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 10px;
  border: 1px solid rgba(255, 142, 83, 0.26);
  border-radius: 18px;
  background: rgba(255, 241, 232, 0.76);
  padding: 10px;
}

.editor-replace-confirm div {
  display: inline-grid;
  grid-template-columns: auto auto;
  align-items: center;
  gap: 6px;
  color: var(--pd-fg-1);
  font-size: 12px;
  font-weight: 900;
}

.editor-replace-confirm div span {
  width: 24px;
  height: 24px;
  border: 1px solid rgba(45, 45, 45, 0.1);
  border-radius: 999px;
}

.editor-replace-confirm em {
  color: var(--pd-orange);
  font-style: normal;
  font-weight: 900;
}

.editor-replace-confirm p,
.editor-replace-message {
  margin: 0;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
}

.editor-replace-confirm button {
  min-height: 34px;
  border: 1px solid rgba(255, 142, 83, 0.24);
  border-radius: 999px;
  background: #fff;
  color: var(--pd-orange);
  padding: 0 12px;
}

.editor-replace-confirm__primary {
  border-color: transparent !important;
  background: var(--pd-gradient-warm) !important;
  color: #fff !important;
  box-shadow: 0 10px 22px rgba(255, 142, 83, 0.14);
}

.editor-replace-message {
  border: 1px solid rgba(255, 142, 83, 0.2);
  border-radius: 14px;
  background: rgba(255, 241, 232, 0.68);
  padding: 9px 11px;
}

.editor-color-section {
  display: grid;
  gap: 8px;
}

.editor-color-section h2 {
  margin: 0;
}

.editor-color-tabs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.editor-color-tabs button {
  flex: 0 0 auto;
  min-height: 38px;
  border: 1px solid var(--pd-stroke);
  border-radius: 999px;
  background: #fff;
  color: var(--pd-fg-2);
  padding: 0 13px;
}

.editor-color-tab--active {
  border-color: transparent !important;
  background: var(--pd-gradient-warm) !important;
  color: #fff !important;
  box-shadow: 0 10px 22px rgba(255, 142, 83, 0.16);
}

.editor-color-grid {
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(70px, 1fr));
  gap: 8px;
  overflow-y: auto;
  padding: 2px 2px 4px;
}

.editor-color-grid--recent {
  grid-template-columns: repeat(auto-fill, minmax(64px, 82px));
  max-height: 90px;
  overflow-y: hidden;
}

.editor-color-card {
  min-width: 0;
  min-height: 68px;
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 6px;
  border: 1px solid var(--pd-stroke);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--pd-fg-1);
  padding: 8px;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.editor-color-card:hover,
.editor-color-card--active {
  border-color: rgba(255, 142, 83, 0.56);
  box-shadow: 0 10px 22px rgba(255, 142, 83, 0.14);
  transform: translateY(-1px);
}

.editor-color-card span {
  width: 30px;
  height: 30px;
}

.editor-color-card strong {
  max-width: 100%;
  overflow: hidden;
  color: var(--pd-fg-1);
  font-size: 12px;
  font-weight: 900;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-color-empty {
  margin: 0;
  text-align: center;
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
    grid-template-columns: minmax(0, 1fr);
  }

  .editor-tray__status,
  .editor-tools,
  .editor-palette,
  .editor-current {
    grid-column: 1 / -1;
  }

  .editor-tools {
    justify-content: flex-start;
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

  .editor-current {
    grid-template-columns: auto minmax(0, 1fr) auto;
    min-height: 48px;
    border-radius: 16px;
  }

  .editor-replace-trigger {
    min-height: 32px;
    padding: 0 9px;
  }

  .editor-color-dialog {
    max-height: calc(100dvh - 18px);
    border-radius: 22px;
  }

  .editor-replace-confirm {
    grid-template-columns: 1fr auto 1fr;
  }

  .editor-replace-confirm p,
  .editor-replace-confirm button {
    grid-column: 1 / -1;
  }

  .editor-color-grid {
    grid-template-columns: repeat(auto-fill, minmax(74px, 1fr));
    gap: 8px;
  }

  .editor-color-card {
    min-height: 76px;
  }
}
</style>
