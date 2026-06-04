<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import {
  GENERATION_MODE_DETAILS,
  GENERATION_MODE_OPTIONS,
  RESULT_SIZE_OPTIONS,
  SIZE_OPTION_DETAILS,
  STYLE_OPTION_DETAILS,
  STYLE_OPTIONS,
  resultSizeLabel,
  useGenerationStore,
  type GenerationMode,
  type GenerationStylePreset,
  type ResultSizePreset
} from '../stores/generation';

type TooltipKey = 'mode' | 'size';

const router = useRouter();
const generation = useGenerationStore();
const galleryInput = ref<HTMLInputElement | null>(null);
const cameraInput = ref<HTMLInputElement | null>(null);
const customSizeField = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const previewUrl = ref('');
const isDragging = ref(false);
const message = ref('');
const customSizeInput = ref('120');
const activeTooltip = ref<TooltipKey | null>(null);

const modeTooltip = 'AI 模式：先把照片变成 Q 版再转图纸，更精细，真人、实物照片强烈推荐（有 AI 参与，稍慢一点）。普通模式：直接量化原图，秒出，适合本来就是卡通的图。';
const sizeTooltip = '格子越多，细节越清楚、越还原；格子越少越好拼，但细节会糊。建议从 52 格起步。格数越高，生成时间也越久哦。';

const fileSizeMb = computed(() => {
  if (!selectedFile.value) {
    return '';
  }
  return `${(selectedFile.value.size / 1024 / 1024).toFixed(1)} MB`;
});

const isHeic = computed(() => {
  const file = selectedFile.value;
  if (!file) {
    return false;
  }
  const name = file.name.toLowerCase();
  return file.type.includes('heic') || file.type.includes('heif') || name.endsWith('.heic') || name.endsWith('.heif');
});

const isCustomSizeActive = computed(() => !RESULT_SIZE_OPTIONS.includes(generation.selectedSize as (typeof RESULT_SIZE_OPTIONS)[number]));
const generationVerb = computed(() => GENERATION_MODE_DETAILS[generation.generationMode].label);
const ctaLabel = computed(() => {
  const size = resultSizeLabel(generation.selectedSize);
  return selectedFile.value ? `${generationVerb.value} · ${size}格 ->` : '选择照片后开始生成';
});

function openGallery(): void {
  galleryInput.value?.click();
}

function openCamera(): void {
  cameraInput.value?.click();
}

function handleInput(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file) {
    useFile(file);
  }
  input.value = '';
}

function handleDrop(event: DragEvent): void {
  isDragging.value = false;
  const file = event.dataTransfer?.files?.[0];
  if (file) {
    useFile(file);
  }
}

function handleDragLeave(event: DragEvent): void {
  const nextTarget = event.relatedTarget as Node | null;
  if (nextTarget && event.currentTarget instanceof Node && event.currentTarget.contains(nextTarget)) {
    return;
  }
  isDragging.value = false;
}

function useFile(file: File): void {
  if (!file.type.startsWith('image/') && !/\.(heic|heif)$/i.test(file.name)) {
    message.value = '请上传 jpg、png、webp 或 HEIC 照片。';
    return;
  }

  revokePreview();
  selectedFile.value = file;
  previewUrl.value = URL.createObjectURL(file);
  message.value = isLargeFile(file) ? '照片较大，会在生成前自动整理。' : '照片已就位，可以开始生成。';
}

function clearFile(): void {
  revokePreview();
  selectedFile.value = null;
  message.value = '';
}

function revokePreview(): void {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value);
    previewUrl.value = '';
  }
}

function isLargeFile(file: File): boolean {
  return file.size > 8 * 1024 * 1024;
}

async function startGenerate(): Promise<void> {
  if (!selectedFile.value) {
    message.value = '请先选择一张照片。';
    return;
  }
  generation.setSourceFile(selectedFile.value);
  await router.push({ name: 'loading', query: { from: 'upload' } });
}

function chooseMode(mode: GenerationMode): void {
  generation.setGenerationMode(mode);
}

function chooseStyle(style: GenerationStylePreset): void {
  generation.setStyle(style);
  generation.setGenerationMode('ai');
}

function chooseSize(size: ResultSizePreset): void {
  generation.setSize(size);
}

function chooseCustomSize(): void {
  const size = normalizeCustomSize(customSizeInput.value);
  customSizeInput.value = String(size);
  generation.setSize(`${size}x${size}` as ResultSizePreset);
}

function focusCustomSize(): void {
  chooseCustomSize();
  window.setTimeout(() => customSizeField.value?.focus(), 0);
}

function handleCustomSizeInput(): void {
  customSizeInput.value = customSizeInput.value.replace(/\D/g, '').slice(0, 3);
  if (isCustomSizeActive.value && customSizeInput.value) {
    chooseCustomSize();
  }
}

function commitCustomSize(): void {
  chooseCustomSize();
}

function normalizeCustomSize(rawValue: string): number {
  const parsed = Number.parseInt(rawValue, 10);
  if (!Number.isFinite(parsed)) {
    return 52;
  }
  return Math.max(10, Math.min(200, parsed));
}

function showTooltip(key: TooltipKey): void {
  activeTooltip.value = key;
}

function hideTooltip(key: TooltipKey): void {
  if (activeTooltip.value === key) {
    activeTooltip.value = null;
  }
}

onUnmounted(revokePreview);
</script>

<template>
  <section class="upload-page">
    <div class="studio-shell">
      <section class="upload-stage" aria-label="上传照片">
        <input
          ref="galleryInput"
          class="sr-only"
          type="file"
          accept="image/*,.heic,.heif"
          @change="handleInput"
        />
        <input
          ref="cameraInput"
          class="sr-only"
          type="file"
          accept="image/*,.heic,.heif"
          capture="environment"
          @change="handleInput"
        />

        <div
          class="drop-zone"
          :class="{ 'drop-zone--active': isDragging, 'drop-zone--filled': selectedFile }"
          role="button"
          tabindex="0"
          @click="openGallery"
          @keydown.enter.prevent="openGallery"
          @keydown.space.prevent="openGallery"
          @dragenter.prevent="isDragging = true"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="handleDragLeave"
          @drop.prevent="handleDrop"
        >
          <template v-if="previewUrl">
            <img v-if="!isHeic" class="preview-image" :src="previewUrl" alt="已选择照片预览" />
            <div v-else class="preview-fallback">
              <strong>HEIC 照片已选择</strong>
              <span>可以继续生成。</span>
            </div>
            <div class="preview-sheen" aria-hidden="true"></div>
          </template>
          <template v-else>
            <div class="upload-mark" aria-hidden="true">
              <svg viewBox="0 0 48 48" focusable="false">
                <path d="M14 33.5v2.25A4.25 4.25 0 0 0 18.25 40h11.5A4.25 4.25 0 0 0 34 35.75V33.5" />
                <path d="M24 31V10" />
                <path d="m16.5 17.5 7.5-7.5 7.5 7.5" />
                <path d="M14 27.5h20" />
              </svg>
            </div>
            <strong>拖拽照片到这里</strong>
            <span>或点击选择图片</span>
          </template>
        </div>

        <div class="stage-actions">
          <button class="pd-btn pd-btn--primary" type="button" @click="openGallery">从相册选择</button>
          <button class="pd-btn stage-secondary" type="button" @click="openCamera">拍一张</button>
        </div>

        <div v-if="selectedFile" class="file-strip">
          <div>
            <strong>{{ selectedFile.name }}</strong>
            <span>{{ selectedFile.type || 'image/*' }} · {{ fileSizeMb }}</span>
          </div>
          <button type="button" @click="clearFile">重新选择</button>
        </div>
      </section>

      <aside class="control-panel" aria-label="生成选项">
        <section class="option-group" aria-label="生成方式">
          <div class="option-heading">
            <div class="heading-title">
              <strong>生成方式</strong>
              <span
                class="info-wrap"
                @mouseenter="showTooltip('mode')"
                @mouseleave="hideTooltip('mode')"
              >
                <button
                  class="info-trigger"
                  type="button"
                  aria-label="生成方式说明"
                  :aria-expanded="activeTooltip === 'mode'"
                  @click.stop="showTooltip('mode')"
                  @focus="showTooltip('mode')"
                  @blur="hideTooltip('mode')"
                >
                  i
                </button>
                <span v-if="activeTooltip === 'mode'" class="info-tip" role="tooltip">
                  {{ modeTooltip }}
                </span>
              </span>
            </div>
            <span class="heading-note">AI 默认推荐</span>
          </div>
          <div class="mode-grid">
            <button
              v-for="mode in GENERATION_MODE_OPTIONS"
              :key="mode"
              type="button"
              class="mode-card"
              :class="{ 'mode-card--active': generation.generationMode === mode }"
              :aria-pressed="generation.generationMode === mode"
              @click="chooseMode(mode)"
            >
              <span v-if="GENERATION_MODE_DETAILS[mode].badge" class="option-badge">
                {{ GENERATION_MODE_DETAILS[mode].badge }}
              </span>
              <strong>{{ GENERATION_MODE_DETAILS[mode].label }}</strong>
              <em>{{ GENERATION_MODE_DETAILS[mode].hint }}</em>
            </button>
          </div>
        </section>

        <section class="option-group" aria-label="风格">
          <div class="option-heading">
            <strong>风格</strong>
            <span class="heading-note">{{ generation.generationMode === 'ai' ? 'Q版风格化' : '切回 AI 时生效' }}</span>
          </div>
          <div class="style-grid">
            <button
              v-for="style in STYLE_OPTIONS"
              :key="style"
              type="button"
              class="style-pill"
              :class="{ 'style-pill--active': generation.selectedStyle === style, 'style-pill--muted': generation.generationMode !== 'ai' }"
              :aria-pressed="generation.selectedStyle === style"
              @click="chooseStyle(style)"
            >
              <span class="style-icon" aria-hidden="true">
                <img :src="STYLE_OPTION_DETAILS[style].iconSrc" :alt="`${STYLE_OPTION_DETAILS[style].label}图标`" />
              </span>
              <span class="style-copy">
                <strong>{{ STYLE_OPTION_DETAILS[style].label }}</strong>
                <em>{{ STYLE_OPTION_DETAILS[style].hint }}</em>
              </span>
            </button>
          </div>
        </section>

        <section class="option-group" aria-label="目标格数">
          <div class="option-heading">
            <div class="heading-title">
              <strong>目标格数</strong>
              <span
                class="info-wrap"
                @mouseenter="showTooltip('size')"
                @mouseleave="hideTooltip('size')"
              >
                <button
                  class="info-trigger"
                  type="button"
                  aria-label="目标格数说明"
                  :aria-expanded="activeTooltip === 'size'"
                  @click.stop="showTooltip('size')"
                  @focus="showTooltip('size')"
                  @blur="hideTooltip('size')"
                >
                  i
                </button>
                <span v-if="activeTooltip === 'size'" class="info-tip" role="tooltip">
                  {{ sizeTooltip }}
                </span>
              </span>
            </div>
            <span class="heading-note">按拼豆板规格</span>
          </div>
          <div class="size-grid">
            <button
              v-for="size in RESULT_SIZE_OPTIONS"
              :key="size"
              type="button"
              class="size-card"
              :class="{ 'size-card--active': generation.selectedSize === size }"
              :aria-pressed="generation.selectedSize === size"
              @click="chooseSize(size)"
            >
              <strong>{{ SIZE_OPTION_DETAILS[size].label }}</strong>
            </button>
          </div>
          <label
            class="custom-size-field"
            :class="{ 'custom-size-field--active': isCustomSizeActive }"
            @click="focusCustomSize"
          >
            <strong>自定义</strong>
            <input
              ref="customSizeField"
              v-model="customSizeInput"
              type="text"
              inputmode="numeric"
              pattern="[0-9]*"
              aria-label="自定义目标格数"
              @click.stop
              @focus="chooseCustomSize"
              @input="handleCustomSizeInput"
              @blur="commitCustomSize"
            />
            <span>按拼豆板规格更好拼</span>
          </label>
        </section>
      </aside>

      <div class="generate-bar">
        <p v-if="message" class="upload-message">{{ message }}</p>
        <button class="pd-btn generate-cta" type="button" :disabled="!selectedFile" @click="startGenerate">
          {{ ctaLabel }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.upload-page {
  padding: clamp(8px, 3vh, 26px) 0 24px;
}

.studio-shell {
  width: min(100%, 1080px);
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(348px, 392px) minmax(500px, 1fr);
  grid-template-rows: minmax(0, 1fr) auto;
  grid-template-areas:
    "controls upload"
    "controls action";
  gap: clamp(14px, 2vw, 22px) clamp(18px, 2.4vw, 28px);
  align-items: stretch;
  justify-content: center;
}

.upload-stage,
.control-panel {
  border: 1px solid rgba(237, 228, 218, 0.86);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--pd-shadow-float);
  padding: clamp(18px, 3.2vw, 30px);
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.upload-stage:hover,
.control-panel:hover {
  border-color: rgba(255, 142, 83, 0.36);
  box-shadow: 0 22px 54px rgba(255, 142, 83, 0.15), 0 16px 36px rgba(45, 45, 45, 0.08);
  transform: translateY(-3px);
}

.upload-stage {
  grid-area: upload;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.drop-zone {
  position: relative;
  min-height: clamp(240px, 30vw, 360px);
  flex: 1 1 auto;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  overflow: hidden;
  border: 2px dashed rgba(255, 142, 83, 0.3);
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(255, 176, 136, 0.1), rgba(164, 212, 197, 0.12)),
    repeating-linear-gradient(45deg, rgba(237, 228, 218, 0.24) 0 1px, transparent 1px 14px),
    #fffaf5;
  color: var(--pd-fg-2);
  cursor: pointer;
  padding: 24px;
  text-align: center;
  transition:
    border-color 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.drop-zone:hover {
  border-color: rgba(255, 142, 83, 0.7);
  box-shadow: inset 0 0 0 1px rgba(255, 176, 136, 0.22), 0 18px 34px rgba(255, 142, 83, 0.18);
  transform: translateY(-3px);
}

.drop-zone--active {
  border-style: solid;
  border-color: var(--pd-orange);
  background:
    linear-gradient(135deg, rgba(255, 176, 136, 0.2), rgba(184, 164, 237, 0.16)),
    #fff7ef;
  box-shadow: 0 20px 42px rgba(255, 142, 83, 0.22), 0 0 0 4px rgba(255, 142, 83, 0.12);
  transform: translateY(-4px) scale(1.008);
}

.drop-zone--filled {
  border-style: solid;
  border-color: rgba(237, 228, 218, 0.92);
  background: #fff;
  padding: 12px;
}

.drop-zone strong {
  color: var(--pd-fg-1);
  font-size: 22px;
  font-weight: 900;
}

.drop-zone > span {
  color: var(--pd-fg-2);
  font-weight: 800;
}

.upload-mark {
  width: 86px;
  height: 86px;
  display: grid;
  place-items: center;
  border-radius: 28px;
  background: var(--pd-gradient-warm);
  box-shadow: var(--pd-shadow-cta);
  transition: transform 260ms var(--pd-ease-soft);
}

.drop-zone:hover .upload-mark,
.drop-zone--active .upload-mark {
  transform: rotate(-4deg) scale(1.05);
}

.upload-mark svg {
  width: 43px;
  height: 43px;
  fill: none;
  stroke: #fff;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 4.2;
}

.preview-image {
  width: 100%;
  height: 100%;
  max-height: 360px;
  display: block;
  border-radius: 18px;
  object-fit: contain;
  animation: previewIn 360ms var(--pd-ease-out);
}

.preview-sheen {
  position: absolute;
  inset: 12px;
  pointer-events: none;
  border-radius: 18px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.58), inset 0 -40px 80px rgba(255, 176, 136, 0.06);
}

.preview-fallback {
  display: grid;
  gap: 8px;
  place-items: center;
  border-radius: 20px;
  background: rgba(255, 176, 136, 0.14);
  padding: 32px;
}

.stage-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.stage-secondary {
  border: 1px solid rgba(255, 142, 83, 0.28);
  background: var(--pd-peach-50);
  color: var(--pd-orange);
}

.stage-actions .pd-btn,
.generate-cta {
  cursor: pointer;
  transition:
    border-color 180ms var(--pd-ease-out),
    filter 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.stage-actions .pd-btn:hover,
.generate-cta:hover:not(:disabled) {
  filter: brightness(1.03);
  border-color: rgba(255, 142, 83, 0.58);
  box-shadow: 0 16px 28px rgba(255, 142, 83, 0.2);
  transform: translateY(-2px);
}

.file-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  border: 1px solid var(--pd-stroke);
  border-radius: 18px;
  background: rgba(255, 241, 232, 0.58);
  padding: 13px 15px;
}

.file-strip strong,
.file-strip span {
  display: block;
}

.file-strip strong {
  color: var(--pd-fg-1);
  word-break: break-all;
}

.file-strip span {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 800;
}

.file-strip button {
  flex: 0 0 auto;
  border: 0;
  background: transparent;
  color: var(--pd-orange);
  cursor: pointer;
  font: inherit;
  font-weight: 900;
  transition:
    color 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.file-strip button:hover {
  color: var(--pd-pink);
  transform: translateY(-1px);
}

.control-panel {
  grid-area: controls;
  display: grid;
  align-content: start;
  gap: 18px;
}

.option-group {
  display: grid;
  gap: 12px;
}

.option-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.heading-title {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.option-heading strong,
.heading-title strong {
  color: var(--pd-fg-1);
  font-size: 15px;
  font-weight: 900;
  white-space: nowrap;
}

.heading-note {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

.info-wrap {
  position: relative;
  display: inline-grid;
  place-items: center;
}

.info-trigger {
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 142, 83, 0.34);
  border-radius: 999px;
  background: rgba(255, 241, 232, 0.88);
  color: var(--pd-orange);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  font-weight: 900;
  line-height: 1;
  transition:
    border-color 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.info-trigger:hover,
.info-trigger:focus-visible {
  border-color: rgba(255, 142, 83, 0.72);
  background: #fff;
  box-shadow: 0 8px 18px rgba(255, 142, 83, 0.16);
  outline: none;
  transform: translateY(-1px);
}

.info-tip {
  position: absolute;
  top: calc(100% + 10px);
  left: 0;
  z-index: 6;
  width: min(312px, 76vw);
  border: 1px solid rgba(255, 142, 83, 0.3);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 18px 42px rgba(45, 45, 45, 0.12), 0 10px 24px rgba(255, 142, 83, 0.12);
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 800;
  line-height: 1.62;
  padding: 12px 13px;
  text-align: left;
  white-space: normal;
}

.mode-grid,
.style-grid,
.size-grid {
  display: grid;
  width: 100%;
  gap: 10px;
}

.mode-grid {
  grid-template-columns: repeat(2, minmax(150px, 1fr));
}

.style-grid {
  grid-template-columns: 1fr;
}

.size-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.mode-card,
.style-pill,
.size-card,
.custom-size-field {
  appearance: none;
  position: relative;
  min-width: 0;
  border: 1px solid var(--pd-stroke);
  background: rgba(255, 255, 255, 0.82);
  color: var(--pd-fg-1);
  cursor: pointer;
  font: inherit;
  text-align: left;
  transition:
    border-color 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.mode-card {
  display: grid;
  align-content: center;
  gap: 7px;
  min-height: 104px;
  border-radius: 20px;
  padding: 16px 14px;
}

.mode-card:hover,
.style-pill:hover,
.size-card:hover,
.custom-size-field:hover {
  border-color: rgba(255, 142, 83, 0.62);
  background: #fff;
  box-shadow: 0 14px 28px rgba(255, 142, 83, 0.16);
  transform: translateY(-2px);
}

.mode-card strong,
.mode-card em,
.style-copy,
.style-pill strong,
.style-pill em,
.size-card strong,
.size-card span {
  display: block;
  min-width: 0;
  word-break: keep-all;
  overflow-wrap: normal;
}

.mode-card strong {
  padding-right: 42px;
  font-size: 17px;
  font-weight: 900;
  white-space: nowrap;
}

.mode-card em,
.style-pill em {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
  line-height: 1.45;
  white-space: nowrap;
}

.option-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  border-radius: 999px;
  background: rgba(255, 107, 157, 0.12);
  color: var(--pd-pink-deep);
  font-size: 11px;
  font-weight: 900;
  padding: 4px 8px;
}

.mode-card--active,
.style-pill--active,
.size-card--active,
.custom-size-field--active {
  border-color: transparent;
  background: var(--pd-gradient-warm);
  color: #fff;
  box-shadow: var(--pd-shadow-cta);
}

.mode-card--active:hover,
.style-pill--active:hover,
.size-card--active:hover,
.custom-size-field--active:hover {
  border-color: rgba(255, 142, 83, 0.7);
  background: var(--pd-gradient-warm);
  color: #fff;
  box-shadow: 0 18px 34px rgba(255, 142, 83, 0.26), 0 9px 18px rgba(255, 107, 90, 0.18);
}

.mode-card--active em,
.style-pill--active em,
.size-card--active span {
  color: rgba(255, 255, 255, 0.86);
}

.mode-card--active:hover em,
.style-pill--active:hover em,
.size-card--active:hover span {
  color: rgba(255, 255, 255, 0.86);
}

.mode-card--active .option-badge {
  background: rgba(255, 255, 255, 0.22);
  color: #fff;
}

.style-pill {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  justify-items: start;
  min-height: 72px;
  border-radius: 18px;
  padding: 12px 16px;
}

.style-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  justify-self: start;
  align-self: center;
  border-radius: 16px;
  background: rgba(255, 249, 245, 0.72);
  box-shadow: inset 0 0 0 1px rgba(237, 228, 218, 0.62);
  overflow: hidden;
}

.style-icon img {
  width: 42px;
  height: 42px;
  display: block;
  object-fit: contain;
}

.style-pill--active .style-icon {
  background: rgba(255, 255, 255, 0.22);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.36);
}

.style-pill--active:hover .style-icon {
  background: rgba(255, 255, 255, 0.22);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.36);
}

.style-pill--muted:not(.style-pill--active) {
  opacity: 0.72;
}

.style-copy {
  display: grid;
  gap: 4px;
  align-content: center;
  justify-items: start;
  line-height: 1.2;
}

.style-pill strong {
  font-size: 16px;
  font-weight: 900;
  line-height: 1.15;
  white-space: nowrap;
}

.style-pill em {
  margin-top: 0;
  line-height: 1.3;
}

.size-card {
  min-height: 64px;
  border-radius: 18px;
  padding: 10px 7px;
  text-align: center;
}

.size-card strong {
  font-size: 22px;
  font-weight: 900;
  line-height: 1;
}

.custom-size-field {
  display: grid;
  grid-template-columns: auto minmax(72px, 108px) minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  min-height: 64px;
  border-radius: 18px;
  margin-top: 10px;
  padding: 12px 14px;
  text-align: left;
}

.custom-size-field strong {
  font-size: 16px;
  font-weight: 900;
  white-space: nowrap;
}

.custom-size-field input {
  width: 100%;
  min-width: 0;
  height: 38px;
  border: 1px solid rgba(255, 142, 83, 0.34);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.82);
  color: var(--pd-fg-1);
  cursor: text;
  font: inherit;
  font-size: 18px;
  font-weight: 900;
  outline: none;
  padding: 0 10px;
  text-align: center;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out);
}

.custom-size-field input:focus {
  border-color: rgba(255, 142, 83, 0.72);
  box-shadow: 0 0 0 4px rgba(255, 142, 83, 0.12);
}

.custom-size-field span {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
  line-height: 1.25;
  white-space: nowrap;
}

.custom-size-field--active input {
  border-color: rgba(255, 255, 255, 0.48);
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.custom-size-field--active input::placeholder,
.custom-size-field--active span {
  color: rgba(255, 255, 255, 0.86);
}

.generate-bar {
  grid-area: action;
  display: grid;
  align-content: end;
  gap: 10px;
  min-width: 0;
}

.upload-message {
  width: 100%;
  margin: 0;
  border-radius: 16px;
  background: rgba(164, 212, 197, 0.18);
  color: var(--pd-fg-2);
  font-size: 13px;
  font-weight: 800;
  padding: 12px 14px;
}

.generate-cta {
  width: 100%;
  min-height: 60px;
  border: 1px solid transparent;
  font-size: 17px;
}

.generate-cta:not(:disabled) {
  background: var(--pd-gradient);
  color: #fff;
  box-shadow: var(--pd-shadow-cta);
}

.generate-cta:disabled {
  background: #ede5dd;
  color: #9b8e84;
  box-shadow: none;
  cursor: not-allowed;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}

@keyframes previewIn {
  from {
    opacity: 0;
    transform: scale(0.985);
  }

  to {
    opacity: 1;
    transform: scale(1);
  }
}

@media (max-width: 980px) {
  .studio-shell {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
    grid-template-areas:
      "upload"
      "controls"
      "action";
  }

  .upload-stage {
    min-height: auto;
  }

  .drop-zone {
    min-height: 360px;
  }

  .style-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .upload-page {
    padding-top: 8px;
  }

  .upload-stage,
  .control-panel {
    border-radius: 22px;
    padding: 16px;
  }

  .drop-zone {
    min-height: 300px;
    border-radius: 20px;
  }

  .stage-actions,
  .mode-grid,
  .style-grid {
    grid-template-columns: 1fr;
  }

  .mode-card {
    min-height: 88px;
  }

  .mode-card em,
  .style-pill em,
  .custom-size-field span {
    white-space: normal;
  }

  .style-pill {
    grid-template-columns: 48px minmax(0, 1fr);
    min-height: 70px;
    padding: 11px 14px;
  }

  .size-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .custom-size-field {
    grid-template-columns: minmax(0, 1fr) minmax(84px, 108px);
    gap: 8px 10px;
  }

  .custom-size-field span {
    grid-column: 1 / -1;
    line-height: 1.35;
  }

  .file-strip {
    align-items: start;
    flex-direction: column;
  }
}
</style>
