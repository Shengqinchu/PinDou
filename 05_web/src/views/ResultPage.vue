<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import {
  GENERATION_MODE_DETAILS,
  GENERATION_MODE_OPTIONS,
  RESULT_SIZE_OPTIONS,
  STYLE_OPTION_DETAILS,
  STYLE_OPTIONS,
  useGenerationStore,
  type GenerationMode,
  type GenerationStylePreset,
  type ResultSizePreset
} from '../stores/generation';
import { useSWRCacheStore } from '../stores/swrCache';
import { paletteRowsForPattern } from '../utils/patternEditing';

const route = useRoute();
const router = useRouter();
const generation = useGenerationStore();
const swrCache = useSWRCacheStore();
const loading = ref(false);
const error = ref('');
const sizeNotice = ref('');
const isRegenerateModalOpen = ref(false);
const isDownloading = ref(false);
const draftMode = ref<GenerationMode>(generation.generationMode);
const draftStyle = ref<GenerationStylePreset>(generation.selectedStyle);
const draftSize = ref<ResultSizePreset>(generation.selectedSize);

const pattern = computed(() => generation.currentPattern);
const hasSourceFile = computed(() => Boolean(generation.sourceFile));
const artworkId = computed(() => String(route.params.id || generation.currentArtworkId || ''));
const selectedSizeNumber = computed(() => generation.selectedSize.split('x')[0]);
const colorTotal = computed(() => pattern.value?.palette_used.length || 0);
const beadTotal = computed(() => pattern.value?.bead_total || 0);
const patternImageUrl = computed(() => generation.patternImageUrl);
const paletteRows = computed(() => paletteRowsForPattern(pattern.value));
const downloadFileName = computed(() => {
  const title = generation.currentArtwork?.title?.trim();
  const rawName = title || `拼豆图纸_${artworkId.value || 'pindou'}`;
  const safeName = rawName.replace(/[\\/:*?"<>|]/g, '').trim() || '拼豆图纸';
  return `${safeName}.png`;
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

  const snapshot = swrCache.getArtworkSnapshot(id);
  if (snapshot) {
    error.value = '';
    loading.value = false;
    generation.applyArtwork(snapshot.data);
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

function openRegenerateModal(): void {
  sizeNotice.value = '';
  if (!generation.sourceFile) {
    sizeNotice.value = '重新生成需要原图，请回到上传页重新选择照片。';
    return;
  }
  draftMode.value = generation.generationMode;
  draftStyle.value = generation.selectedStyle;
  draftSize.value = generation.selectedSize;
  isRegenerateModalOpen.value = true;
}

function closeRegenerateModal(): void {
  isRegenerateModalOpen.value = false;
}

function chooseDraftMode(mode: GenerationMode): void {
  draftMode.value = mode;
}

function chooseDraftStyle(style: GenerationStylePreset): void {
  draftStyle.value = style;
  draftMode.value = 'ai';
}

function chooseDraftSize(size: ResultSizePreset): void {
  draftSize.value = size;
}

async function confirmRegenerate(): Promise<void> {
  if (!generation.sourceFile) {
    closeRegenerateModal();
    sizeNotice.value = '重新生成需要原图，请回到上传页重新选择照片。';
    return;
  }
  generation.setGenerationMode(draftMode.value);
  generation.setStyle(draftStyle.value);
  generation.setSize(draftSize.value);
  swrCache.invalidateGallery();
  closeRegenerateModal();
  await router.push({ name: 'loading', query: { retry: '1', size: generation.selectedSize } });
}

async function downloadPattern(): Promise<void> {
  const url = patternImageUrl.value;
  if (!url || isDownloading.value) {
    return;
  }
  sizeNotice.value = '';
  isDownloading.value = true;
  let objectUrl = '';
  try {
    const response = await fetch(url, { mode: 'cors' });
    if (!response.ok) {
      throw new Error('download failed');
    }
    const blob = await response.blob();
    objectUrl = URL.createObjectURL(blob);
    triggerDownload(objectUrl, downloadFileName.value);
  } catch (_error) {
    window.open(url, '_blank', 'noopener,noreferrer');
    sizeNotice.value = '图片已在新窗口打开，手机端可长按保存。';
  } finally {
    if (objectUrl) {
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
    }
    isDownloading.value = false;
  }
}

function triggerDownload(url: string, filename: string): void {
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.rel = 'noopener';
  document.body.appendChild(link);
  link.click();
  link.remove();
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
          <h1>点击编辑图纸按钮，可以<span class="hl-edit">修改配色</span>哦~</h1>
        </div>
        <div class="result-actions">
          <div class="result-actions__row">
            <RouterLink class="pd-btn pd-btn--primary result-action-primary" :to="{ name: 'editor', params: { id: artworkId } }">
              <span class="result-action-icon result-action-icon--edit" aria-hidden="true"></span>
              <span>编辑图纸</span>
            </RouterLink>
            <RouterLink class="pd-btn result-secondary" to="/">
              <span>返回主页</span>
            </RouterLink>
            <button class="pd-btn result-secondary result-action-download" type="button" :disabled="!patternImageUrl || isDownloading" @click="downloadPattern">
              <span class="result-action-icon result-action-icon--download" aria-hidden="true"></span>
              <span>{{ isDownloading ? '下载中' : '下载图纸' }}</span>
            </button>
          </div>
          <button class="result-regenerate-link" type="button" @click="openRegenerateModal">重新生成 ›</button>
        </div>
      </header>

      <div class="result-layout">
        <section class="preview-panel" aria-label="拼豆图纸预览">
          <div class="pattern-frame pattern-frame--viewer">
            <img v-if="patternImageUrl" class="pattern-image" :src="patternImageUrl" alt="拼豆图纸预览" />
            <div v-else class="pattern-image-empty">图纸预览生成中</div>
          </div>
          <p v-if="sizeNotice" class="size-notice">{{ sizeNotice }}</p>
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

    <div v-if="isRegenerateModalOpen" class="regen-modal-backdrop" @click.self="closeRegenerateModal">
      <section class="regen-modal" role="dialog" aria-modal="true" aria-labelledby="regen-title">
        <header class="regen-modal__header">
          <div>
            <p class="eyebrow">重新生成</p>
            <h2 id="regen-title">调整参数后再试一次</h2>
          </div>
          <button class="regen-modal__close" type="button" aria-label="关闭" @click="closeRegenerateModal">×</button>
        </header>

        <div class="regen-modal__section">
          <div class="regen-modal__section-title">
            <strong>生成方式</strong>
          </div>
          <div class="regen-choice-grid regen-choice-grid--mode">
            <button
              v-for="mode in GENERATION_MODE_OPTIONS"
              :key="mode"
              type="button"
              class="regen-choice"
              :class="{ 'regen-choice--active': mode === draftMode }"
              :aria-pressed="mode === draftMode"
              @click="chooseDraftMode(mode)"
            >
              <strong>{{ GENERATION_MODE_DETAILS[mode].label }}</strong>
              <span>{{ GENERATION_MODE_DETAILS[mode].hint }}</span>
            </button>
          </div>
        </div>

        <div class="regen-modal__section">
          <div class="regen-modal__section-title">
            <strong>风格</strong>
          </div>
          <div class="regen-choice-grid regen-choice-grid--style">
            <button
              v-for="style in STYLE_OPTIONS"
              :key="style"
              type="button"
              class="regen-choice regen-choice--style"
              :class="{ 'regen-choice--active': style === draftStyle && draftMode === 'ai' }"
              :aria-pressed="style === draftStyle && draftMode === 'ai'"
              @click="chooseDraftStyle(style)"
            >
              <img :src="STYLE_OPTION_DETAILS[style].iconSrc" alt="" aria-hidden="true" />
              <span>{{ STYLE_OPTION_DETAILS[style].label }}</span>
            </button>
          </div>
        </div>

        <div class="regen-modal__section">
          <div class="regen-modal__section-title">
            <strong>目标格数</strong>
          </div>
          <div class="size-switch size-switch--modal" aria-label="重新生成尺寸">
            <button
              v-for="size in RESULT_SIZE_OPTIONS"
              :key="size"
              type="button"
              :class="{ 'size-switch__item--active': size === draftSize }"
              :aria-pressed="size === draftSize"
              @click="chooseDraftSize(size)"
            >
              <strong>{{ size.split('x')[0] }}</strong>
              <span>格</span>
            </button>
          </div>
        </div>

        <div class="regen-modal__actions">
          <button class="pd-btn result-secondary" type="button" @click="closeRegenerateModal">取消</button>
          <button class="pd-btn pd-btn--primary" type="button" @click="confirmRegenerate">确认重新生成</button>
        </div>
      </section>
    </div>
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

.result-hero h1 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(30px, 5vw, 46px);
  line-height: 1.1;
  letter-spacing: 0;
}

.hl-edit {
  -webkit-box-decoration-break: clone;
  box-decoration-break: clone;
  border-radius: 6px;
  background: color-mix(in srgb, var(--pd-orange) 15%, transparent);
  color: var(--pd-fg-1);
  padding: 0 4px;
}

.result-state h1 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(30px, 5vw, 46px);
  line-height: 1.1;
  letter-spacing: 0;
}

.result-state p {
  margin: 10px 0 0;
  color: var(--pd-fg-2);
  word-break: break-word;
}

.result-actions {
  min-width: min(100%, 430px);
  display: grid;
  justify-items: end;
  gap: 8px;
}

.result-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.56;
  box-shadow: none;
}

.result-actions__row {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(116px, 1.22fr) minmax(96px, 1fr) minmax(96px, 1fr);
  gap: 10px;
}

.result-actions__row .pd-btn {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding-inline: 13px;
  white-space: nowrap;
}

.result-action-icon {
  position: relative;
  flex: 0 0 auto;
  width: 15px;
  height: 15px;
  display: inline-block;
}

.result-action-icon--edit::before {
  position: absolute;
  left: 3px;
  top: 2px;
  width: 9px;
  height: 3px;
  border-radius: 999px;
  background: currentColor;
  content: "";
  transform: rotate(-38deg);
  transform-origin: center;
}

.result-action-icon--edit::after {
  position: absolute;
  left: 2px;
  bottom: 1px;
  width: 10px;
  height: 8px;
  border: 2px solid currentColor;
  border-top: 0;
  border-radius: 2px;
  content: "";
}

.result-action-icon--download::before {
  position: absolute;
  left: 6px;
  top: 1px;
  width: 3px;
  height: 9px;
  border-radius: 999px;
  background: currentColor;
  content: "";
}

.result-action-icon--download::after {
  position: absolute;
  left: 2px;
  bottom: 1px;
  width: 11px;
  height: 8px;
  border-right: 3px solid currentColor;
  border-bottom: 3px solid currentColor;
  content: "";
  transform: rotate(45deg);
}

.result-regenerate-link {
  border: 0;
  background: transparent;
  color: var(--pd-fg-2);
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 900;
  padding: 2px 4px;
  transition:
    color 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.result-regenerate-link:hover {
  color: var(--pd-orange);
  transform: translateY(-1px);
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

.pattern-frame--viewer {
  padding: 12px;
}

.pattern-image {
  width: 100%;
  height: 100%;
  display: block;
  border-radius: 14px;
  object-fit: contain;
  background: #fff;
}

.pattern-image-empty {
  width: 100%;
  min-height: 220px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--pd-fg-2);
  font-weight: 900;
}

.edit-status {
  margin: 12px 0 0;
  border-radius: 16px;
  background: rgba(164, 212, 197, 0.18);
  color: var(--pd-fg-2);
  font-size: 13px;
  font-weight: 800;
  padding: 12px 14px;
}

.edit-status--error {
  background: rgba(255, 91, 110, 0.14);
  color: #c42535;
}

.size-switch {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 0;
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

.regen-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  background: rgba(48, 38, 30, 0.28);
  padding: 18px;
  backdrop-filter: blur(10px);
}

.regen-modal {
  width: min(100%, 560px);
  max-height: min(760px, calc(100vh - 36px));
  overflow: auto;
  border: 1px solid rgba(237, 228, 218, 0.88);
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(255, 248, 244, 0.98), rgba(255, 255, 255, 0.96)),
    #fff;
  box-shadow: 0 28px 80px rgba(88, 55, 34, 0.2);
  padding: 24px;
  animation: modal-in 180ms var(--pd-ease-out);
}

.regen-modal__header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 22px;
}

.regen-modal__header .eyebrow {
  margin-bottom: 6px;
}

.regen-modal__header h2 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: 26px;
  line-height: 1.14;
}

.regen-modal__close {
  appearance: none;
  width: 40px;
  height: 40px;
  border: 1px solid rgba(255, 142, 83, 0.22);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  color: var(--pd-fg-2);
  cursor: pointer;
  font: inherit;
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.regen-modal__close:hover {
  border-color: rgba(255, 142, 83, 0.48);
  box-shadow: 0 12px 28px rgba(255, 142, 83, 0.14);
  transform: translateY(-1px);
}

.regen-modal__section {
  display: grid;
  gap: 10px;
}

.regen-modal__section + .regen-modal__section {
  margin-top: 18px;
}

.regen-modal__section-title strong {
  color: var(--pd-fg-1);
  font-size: 14px;
  font-weight: 900;
}

.regen-choice-grid {
  display: grid;
  gap: 10px;
}

.regen-choice-grid--mode {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.regen-choice-grid--style {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.regen-choice {
  appearance: none;
  min-height: 84px;
  border: 1px solid var(--pd-stroke);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.84);
  color: var(--pd-fg-1);
  cursor: pointer;
  font: inherit;
  padding: 14px;
  text-align: left;
  transition:
    border-color 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    color 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.regen-choice:hover {
  border-color: rgba(255, 142, 83, 0.46);
  background: #fff;
  box-shadow: 0 14px 30px rgba(255, 142, 83, 0.12);
  transform: translateY(-2px);
}

.regen-choice strong,
.regen-choice span {
  display: block;
}

.regen-choice strong {
  font-size: 16px;
  font-weight: 900;
}

.regen-choice span {
  margin-top: 6px;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 800;
  line-height: 1.45;
}

.regen-choice--active {
  border-color: transparent;
  background: var(--pd-gradient-warm);
  color: #fff;
  box-shadow: var(--pd-shadow-cta);
}

.regen-choice--active span {
  color: rgba(255, 255, 255, 0.84);
}

.regen-choice--style {
  min-height: 86px;
  display: grid;
  place-items: center;
  text-align: center;
}

.regen-choice--style img {
  width: 38px;
  height: 38px;
  object-fit: contain;
}

.regen-choice--style span {
  margin-top: 8px;
  color: inherit;
  font-size: 14px;
}

.size-switch--modal {
  margin: 0;
}

.regen-modal__actions {
  display: grid;
  grid-template-columns: 0.8fr 1.2fr;
  gap: 12px;
  margin-top: 24px;
}

@keyframes modal-in {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.985);
  }

  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.result-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 0 0 22px;
}

.result-stats div {
  display: grid;
  min-width: 0;
  min-height: 96px;
  align-content: center;
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
  font-size: clamp(20px, 2.45vw, 24px);
  font-variant-numeric: tabular-nums;
  font-weight: 900;
  line-height: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  grid-template-columns: 34px minmax(0, 1fr) minmax(52px, auto) 38px;
  align-items: center;
  gap: 10px;
  min-width: 0;
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
  overflow: hidden;
  color: var(--pd-fg-2);
  font-size: 11px;
  font-style: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.palette-count,
.palette-percent {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

.palette-count {
  justify-self: end;
  text-align: right;
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
    justify-items: stretch;
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

  .result-actions {
    width: 100%;
  }

  .result-actions__row {
    grid-template-columns: minmax(104px, 1.24fr) minmax(82px, 0.88fr) minmax(82px, 0.88fr);
    gap: 8px;
  }

  .result-actions__row .pd-btn {
    min-height: 46px;
    font-size: clamp(12px, 3.25vw, 14px);
    padding-inline: 8px;
  }

  .result-action-icon {
    width: 13px;
    height: 13px;
  }

  .result-regenerate-link {
    justify-self: center;
    font-size: 12px;
  }

  .size-switch {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .size-switch button {
    min-height: 62px;
  }

  .result-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    margin-bottom: 18px;
  }

  .result-stats div {
    min-height: 86px;
    border-radius: 16px;
    padding: 12px 8px;
    text-align: center;
  }

  .result-stats dt,
  .result-stats small {
    font-size: 11px;
    line-height: 1.2;
  }

  .result-stats dd {
    font-size: clamp(16px, 5.4vw, 23px);
  }

  .palette-heading {
    align-items: start;
    flex-direction: column;
    gap: 6px;
  }

  .regen-modal {
    border-radius: 22px;
    padding: 18px;
  }

  .regen-modal__header {
    margin-bottom: 16px;
  }

  .regen-modal__header h2 {
    font-size: 24px;
  }

  .regen-modal__section + .regen-modal__section {
    margin-top: 14px;
  }

  .regen-choice-grid--mode {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .regen-choice-grid--style {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .regen-choice {
    min-height: 74px;
    padding: 12px;
  }

  .regen-choice strong {
    font-size: 14px;
  }

  .regen-choice span {
    font-size: 11px;
  }

  .regen-choice--style {
    min-height: 76px;
    text-align: center;
  }

  .regen-choice--style img {
    width: 34px;
    height: 34px;
  }

  .regen-choice--style span {
    margin: 6px 0 0;
  }

  .regen-modal__actions {
    grid-template-columns: 0.8fr 1.2fr;
    margin-top: 18px;
  }

  .palette-row {
    grid-template-columns: 32px minmax(0, 1fr) minmax(50px, auto);
    gap: 8px;
    padding: 9px;
  }

  .palette-percent {
    display: none;
  }

  .palette-swatch {
    width: 32px;
    height: 32px;
  }

  .palette-row strong {
    overflow: hidden;
    line-height: 1.25;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .palette-row em {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .palette-count {
    align-self: center;
    min-width: 50px;
  }
}

@media (max-width: 380px) {
  .preview-panel,
  .summary-panel,
  .result-state {
    padding: 16px;
  }

  .result-stats {
    gap: 6px;
  }

  .result-stats div {
    padding: 10px 6px;
  }
}
</style>
