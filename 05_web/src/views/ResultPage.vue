<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { RESULT_SIZE_OPTIONS, useGenerationStore, type ResultSizePreset } from '../stores/generation';
import type { ColorRef } from '../api/types';

interface PaletteRow {
  color: ColorRef;
  count: number;
  percent: number;
}

interface GridCell {
  key: string;
  code: string;
  color: string;
  empty: boolean;
}

const route = useRoute();
const router = useRouter();
const generation = useGenerationStore();
const loading = ref(false);
const error = ref('');
const sizeNotice = ref('');

const pattern = computed(() => generation.currentPattern);
const patternImageUrl = computed(() => generation.patternImageUrl);
const hasSourceFile = computed(() => Boolean(generation.sourceFile));
const artworkId = computed(() => String(route.params.id || generation.currentArtworkId || ''));
const selectedSizeNumber = computed(() => generation.selectedSize.split('x')[0]);
const sizeLabel = computed(() => generation.selectedSize.replace('x', ' × '));
const colorTotal = computed(() => pattern.value?.palette_used.length || 0);
const beadTotal = computed(() => pattern.value?.bead_total || 0);
const estimatedCost = computed(() => {
  const value = pattern.value?.estimated_cost_cny;
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(1) : '';
});

const paletteRows = computed<PaletteRow[]>(() => {
  const sheet = pattern.value;
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
});

const gridColumnCount = computed(() => {
  const grid = pattern.value?.grid || [];
  return Math.max(...grid.map((row) => row.length), 0);
});

const gridCells = computed<GridCell[]>(() => {
  const grid = pattern.value?.grid || [];
  return grid.flatMap((row, rowIndex) =>
    row.map((cell, colIndex) => ({
      key: `${rowIndex}-${colIndex}`,
      code: cell?.code || '',
      color: cell?.hex || 'transparent',
      empty: !cell
    }))
  );
});

onMounted(() => {
  void loadArtworkIfNeeded();
});

watch(
  () => route.params.id,
  () => {
    void loadArtworkIfNeeded();
  }
);

async function loadArtworkIfNeeded(): Promise<void> {
  const id = String(route.params.id || '');
  if (!id || generation.currentArtworkId === id) {
    return;
  }

  loading.value = true;
  error.value = '';
  try {
    await generation.loadArtwork(id);
  } catch (loadError) {
    error.value = loadError instanceof Error ? loadError.message : '结果加载失败，请回到作品集重新打开。';
  } finally {
    loading.value = false;
  }
}

async function chooseSize(size: ResultSizePreset): Promise<void> {
  sizeNotice.value = '';
  if (size === generation.selectedSize) {
    return;
  }

  generation.setSize(size);
  if (!generation.sourceFile) {
    sizeNotice.value = '当前页面没有保留原图，请回到上传页重新选择后生成这个尺寸。';
    return;
  }
  await router.push({ name: 'loading', query: { size } });
}

async function regenerate(): Promise<void> {
  sizeNotice.value = '';
  if (!generation.sourceFile) {
    sizeNotice.value = '重新生成需要原图，请回到上传页重新选择照片。';
    return;
  }
  await router.push({ name: 'loading', query: { retry: '1', size: generation.selectedSize } });
}
</script>

<template>
  <section class="result-page">
    <template v-if="loading">
      <div class="result-state">
        <p class="eyebrow">正在读取</p>
        <h1>正在打开图纸</h1>
        <p>稍等一下，作品数据马上回来。</p>
      </div>
    </template>

    <template v-else-if="error">
      <div class="result-state">
        <p class="eyebrow">读取失败</p>
        <h1>暂时打不开这个结果</h1>
        <p>{{ error }}</p>
        <RouterLink class="pd-btn pd-btn--primary" to="/upload">重新上传</RouterLink>
      </div>
    </template>

    <template v-else-if="pattern">
      <header class="result-hero">
        <div>
          <p class="eyebrow">生成完成</p>
          <h1>拼豆图纸已准备好</h1>
          <p>{{ artworkId }} · {{ sizeLabel }}</p>
        </div>
        <div class="result-actions">
          <button class="pd-btn pd-btn--primary" type="button" @click="regenerate">重新生成</button>
          <RouterLink class="pd-btn result-secondary" to="/upload">换一张照片</RouterLink>
        </div>
      </header>

      <div class="result-layout">
        <section class="preview-panel" aria-label="拼豆图纸预览">
          <div class="pattern-frame">
            <img v-if="patternImageUrl" class="pattern-image" :src="patternImageUrl" alt="拼豆图纸预览" />
            <div
              v-else
              class="pattern-grid"
              :style="{ gridTemplateColumns: `repeat(${gridColumnCount}, minmax(0, 1fr))` }"
              aria-label="拼豆网格预览"
            >
              <span
                v-for="cell in gridCells"
                :key="cell.key"
                :class="{ 'pattern-grid__cell--empty': cell.empty }"
                :style="{ backgroundColor: cell.color }"
                :title="cell.code"
              ></span>
            </div>
          </div>

          <div class="size-switch" aria-label="尺寸切换">
            <button
              v-for="size in RESULT_SIZE_OPTIONS"
              :key="size"
              type="button"
              :class="{ 'size-switch__item--active': size === generation.selectedSize }"
              :aria-pressed="size === generation.selectedSize"
              @click="chooseSize(size)"
            >
              <strong>{{ size.split('x')[0] }}</strong>
              <span>格</span>
            </button>
          </div>
          <p v-if="sizeNotice" class="size-notice">{{ sizeNotice }}</p>
          <p v-else-if="hasSourceFile" class="size-hint">切换尺寸会用当前原图重新生成。</p>
        </section>

        <aside class="summary-panel" aria-label="图纸摘要">
          <dl class="result-stats">
            <div>
              <dt>尺寸</dt>
              <dd>{{ selectedSizeNumber }}</dd>
              <small>格宽</small>
            </div>
            <div>
              <dt>豆数</dt>
              <dd>{{ beadTotal }}</dd>
              <small>颗</small>
            </div>
            <div>
              <dt>色号</dt>
              <dd>{{ colorTotal }}</dd>
              <small>种</small>
            </div>
            <div>
              <dt>预估</dt>
              <dd>{{ estimatedCost || '-' }}</dd>
              <small>元</small>
            </div>
          </dl>

          <section class="palette-section" aria-label="色号清单">
            <div class="palette-heading">
              <p class="eyebrow">色号清单</p>
              <strong>{{ colorTotal }} 种颜色</strong>
            </div>
            <div class="palette-list">
              <div v-for="row in paletteRows" :key="row.color.code" class="palette-row">
                <span class="palette-swatch" :style="{ backgroundColor: row.color.hex }" aria-hidden="true"></span>
                <div>
                  <strong>{{ row.color.code }} · {{ row.color.name_cn }}</strong>
                  <em>{{ row.color.brand }} · {{ row.color.hex }}</em>
                </div>
                <span class="palette-count">{{ row.count }} 颗</span>
                <span class="palette-percent">{{ row.percent }}%</span>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </template>

    <template v-else>
      <div class="result-state">
        <p class="eyebrow">没有结果</p>
        <h1>先上传一张照片</h1>
        <p>生成完成后，会在这里看到图纸预览和色号清单。</p>
        <RouterLink class="pd-btn pd-btn--primary" to="/upload">去上传</RouterLink>
      </div>
    </template>
  </section>
</template>

<style scoped>
.result-page {
  display: grid;
  gap: 24px;
}

.result-hero {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 20px;
}

.eyebrow {
  margin: 0 0 10px;
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
  text-transform: uppercase;
}

.result-hero h1,
.result-state h1 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(30px, 5vw, 46px);
  line-height: 1.1;
  letter-spacing: 0;
}

.result-hero p:last-child,
.result-state p {
  margin: 10px 0 0;
  color: var(--pd-fg-2);
  word-break: break-word;
}

.result-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12px;
}

.result-secondary {
  border: 1px solid rgba(255, 142, 83, 0.28);
  background: var(--pd-peach-50);
  color: var(--pd-orange);
}

.result-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(320px, 0.56fr);
  gap: 24px;
  align-items: start;
}

.preview-panel,
.summary-panel,
.result-state {
  border: 1px solid rgba(237, 228, 218, 0.82);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--pd-shadow-float);
  padding: clamp(20px, 4vw, 32px);
}

.result-state {
  width: min(100%, 660px);
  margin: 0 auto;
  text-align: center;
}

.result-state .pd-btn {
  margin-top: 22px;
}

.pattern-frame {
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  overflow: hidden;
  border: 1px solid var(--pd-stroke);
  border-radius: 22px;
  background:
    linear-gradient(45deg, rgba(237, 228, 218, 0.38) 25%, transparent 25%),
    linear-gradient(-45deg, rgba(237, 228, 218, 0.38) 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, rgba(237, 228, 218, 0.38) 75%),
    linear-gradient(-45deg, transparent 75%, rgba(237, 228, 218, 0.38) 75%),
    #fff;
  background-position: 0 0, 0 10px, 10px -10px, -10px 0;
  background-size: 20px 20px;
}

.pattern-image {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  background: #fff;
}

.pattern-grid {
  width: 100%;
  height: 100%;
  display: grid;
  gap: 1px;
  background: rgba(45, 45, 45, 0.12);
}

.pattern-grid span {
  min-width: 0;
  min-height: 0;
}

.pattern-grid__cell--empty {
  background:
    linear-gradient(45deg, rgba(237, 228, 218, 0.55) 25%, transparent 25%),
    #fff !important;
}

.size-switch {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 16px;
}

.size-switch button {
  appearance: none;
  min-height: 68px;
  border: 1px solid var(--pd-stroke);
  border-radius: 18px;
  background: var(--pd-peach-50);
  color: var(--pd-fg-1);
  cursor: pointer;
  font: inherit;
  transition:
    border-color 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.size-switch button:hover {
  border-color: rgba(255, 142, 83, 0.44);
  background: #fff;
  box-shadow: 0 12px 26px rgba(255, 142, 83, 0.12);
  transform: translateY(-2px);
}

.size-switch strong,
.size-switch span {
  display: block;
}

.size-switch strong {
  font-size: 22px;
  font-weight: 900;
  line-height: 1;
}

.size-switch span {
  margin-top: 4px;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 800;
}

.size-switch__item--active {
  border-color: transparent !important;
  background: var(--pd-gradient-warm) !important;
  color: #fff !important;
  box-shadow: var(--pd-shadow-cta);
}

.size-switch__item--active span {
  color: rgba(255, 255, 255, 0.82);
}

.size-notice,
.size-hint {
  margin: 12px 0 0;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 800;
  padding: 12px 14px;
}

.size-notice {
  background: rgba(255, 176, 32, 0.16);
  color: #a56c00;
}

.size-hint {
  background: rgba(164, 212, 197, 0.18);
  color: var(--pd-fg-2);
}

.result-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0 0 22px;
}

.result-stats div {
  border: 1px solid var(--pd-stroke);
  border-radius: 18px;
  background: var(--pd-peach-50);
  padding: 14px;
}

.result-stats dt {
  margin: 0 0 6px;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
}

.result-stats dd {
  margin: 0;
  color: var(--pd-fg-1);
  font-size: 24px;
  font-weight: 900;
  line-height: 1;
}

.result-stats small {
  display: block;
  margin-top: 6px;
  color: var(--pd-fg-2);
  font-size: 12px;
}

.palette-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.palette-heading .eyebrow {
  margin: 0;
}

.palette-heading strong {
  color: var(--pd-fg-1);
}

.palette-list {
  max-height: 520px;
  overflow: auto;
  display: grid;
  gap: 10px;
  padding-right: 2px;
}

.palette-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--pd-stroke);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  padding: 10px;
}

.palette-swatch {
  width: 34px;
  height: 34px;
  border: 1px solid rgba(45, 45, 45, 0.1);
  border-radius: var(--pd-r-full);
  box-shadow: inset 0 0 0 3px rgba(255, 255, 255, 0.58);
}

.palette-row strong,
.palette-row em {
  display: block;
  min-width: 0;
}

.palette-row strong {
  overflow: hidden;
  color: var(--pd-fg-1);
  font-size: 13px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.palette-row em {
  color: var(--pd-fg-2);
  font-size: 11px;
  font-style: normal;
}

.palette-count,
.palette-percent {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

.palette-percent {
  min-width: 38px;
  text-align: right;
}

@media (max-width: 900px) {
  .result-hero {
    align-items: start;
    flex-direction: column;
  }

  .result-actions {
    justify-content: start;
  }

  .result-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .preview-panel,
  .summary-panel,
  .result-state {
    border-radius: 22px;
    padding: 20px;
  }

  .result-actions,
  .result-actions .pd-btn {
    width: 100%;
  }

  .size-switch {
    gap: 8px;
  }

  .size-switch button {
    min-height: 62px;
  }

  .palette-row {
    grid-template-columns: auto minmax(0, 1fr) auto;
  }

  .palette-percent {
    display: none;
  }
}
</style>
