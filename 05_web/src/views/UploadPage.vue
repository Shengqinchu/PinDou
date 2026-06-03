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
  useGenerationStore,
  type GenerationMode,
  type GenerationStylePreset,
  type ResultSizePreset
} from '../stores/generation';

const router = useRouter();
const generation = useGenerationStore();
const galleryInput = ref<HTMLInputElement | null>(null);
const cameraInput = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const previewUrl = ref('');
const isDragging = ref(false);
const message = ref('');

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

const generationVerb = computed(() => (generation.generationMode === 'ai' ? 'AI 生成' : '快速生成'));
const ctaLabel = computed(() => {
  const size = generation.selectedSize.split('x')[0];
  return selectedFile.value ? `${generationVerb.value} · ${size}格 ->` : '选择照片后开始生成';
});
const selectedModeDetail = computed(() => GENERATION_MODE_DETAILS[generation.generationMode]);

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

onUnmounted(revokePreview);
</script>

<template>
  <section class="upload-page">
    <header class="studio-hero">
      <p class="eyebrow">Create Pattern</p>
      <h1>把照片变成一张干净的 Q 版拼豆图纸</h1>
      <p>上传照片，选择生成方式、风格和目标格数，然后交给 PinDou 做图纸。</p>
    </header>

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
              <span></span>
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
        <div class="panel-head">
          <p class="eyebrow">Generate Setup</p>
          <strong>{{ selectedModeDetail.label }}</strong>
          <span>{{ selectedModeDetail.hint }}</span>
        </div>

        <section class="option-group" aria-label="生成方式">
          <div class="option-heading">
            <strong>生成方式</strong>
            <span>AI 默认推荐</span>
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
            <span>{{ generation.generationMode === 'ai' ? 'Q版风格化' : '切回 AI 时生效' }}</span>
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
              <span>{{ STYLE_OPTION_DETAILS[style].icon }}</span>
              <strong>{{ STYLE_OPTION_DETAILS[style].label }}</strong>
              <em>{{ STYLE_OPTION_DETAILS[style].hint }}</em>
            </button>
          </div>
        </section>

        <section class="option-group" aria-label="目标格数">
          <div class="option-heading">
            <strong>目标格数</strong>
            <span>按拼豆板规格</span>
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
              <span>{{ SIZE_OPTION_DETAILS[size].hint }}</span>
            </button>
          </div>
        </section>

        <p v-if="message" class="upload-message">{{ message }}</p>
        <button class="pd-btn generate-cta" type="button" :disabled="!selectedFile" @click="startGenerate">
          {{ ctaLabel }}
        </button>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.upload-page {
  display: grid;
  gap: clamp(22px, 4vw, 34px);
}

.studio-hero {
  width: min(100%, 860px);
}

.studio-hero h1 {
  max-width: 760px;
  margin: 0 0 12px;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(34px, 5.2vw, 60px);
  font-weight: 900;
  line-height: 1.04;
  letter-spacing: 0;
}

.studio-hero p:last-child {
  max-width: 640px;
  margin: 0;
  color: var(--pd-fg-2);
  font-size: 16px;
}

.eyebrow {
  margin: 0 0 10px;
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
  text-transform: uppercase;
}

.studio-shell {
  display: grid;
  grid-template-columns: minmax(0, 1.16fr) minmax(330px, 0.62fr);
  gap: 22px;
  align-items: stretch;
}

.upload-stage,
.control-panel {
  border: 1px solid rgba(237, 228, 218, 0.86);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--pd-shadow-float);
  padding: clamp(18px, 3.2vw, 30px);
}

.upload-stage {
  display: grid;
  grid-template-rows: minmax(320px, 1fr) auto auto;
  gap: 14px;
}

.drop-zone {
  position: relative;
  min-height: clamp(340px, 48vw, 560px);
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
    border-color 220ms var(--pd-ease-out),
    background 220ms var(--pd-ease-out),
    box-shadow 220ms var(--pd-ease-out),
    transform 220ms var(--pd-ease-out);
}

.drop-zone:hover {
  border-color: rgba(255, 142, 83, 0.62);
  box-shadow: inset 0 0 0 1px rgba(255, 176, 136, 0.18), 0 16px 34px rgba(255, 142, 83, 0.14);
  transform: translateY(-2px);
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

.upload-mark span {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background:
    linear-gradient(90deg, #fff 0 6px, transparent 6px 14px, #fff 14px 20px, transparent 20px),
    linear-gradient(#fff 0 6px, transparent 6px 14px, #fff 14px 20px, transparent 20px);
}

.preview-image {
  width: 100%;
  height: 100%;
  max-height: 560px;
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
  transition:
    filter 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.stage-actions .pd-btn:hover,
.generate-cta:hover:not(:disabled) {
  filter: brightness(1.03);
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
}

.control-panel {
  display: grid;
  align-content: start;
  gap: 18px;
}

.panel-head {
  border-radius: 22px;
  background:
    linear-gradient(135deg, rgba(255, 176, 136, 0.18), rgba(184, 164, 237, 0.12)),
    var(--pd-peach-50);
  padding: 18px;
}

.panel-head .eyebrow {
  margin-bottom: 8px;
}

.panel-head strong,
.panel-head span {
  display: block;
}

.panel-head strong {
  color: var(--pd-fg-1);
  font-size: 24px;
  font-weight: 900;
  line-height: 1.1;
}

.panel-head span {
  margin-top: 8px;
  color: var(--pd-fg-2);
  font-size: 13px;
  font-weight: 800;
  line-height: 1.5;
}

.option-group {
  display: grid;
  gap: 10px;
}

.option-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.option-heading strong {
  color: var(--pd-fg-1);
  font-size: 15px;
  font-weight: 900;
}

.option-heading span {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
}

.mode-grid,
.style-grid,
.size-grid {
  display: grid;
  gap: 10px;
}

.mode-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.style-grid {
  grid-template-columns: 1fr;
}

.size-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.mode-card,
.style-pill,
.size-card {
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
  min-height: 112px;
  border-radius: 20px;
  padding: 16px;
}

.mode-card:hover,
.style-pill:hover,
.size-card:hover {
  border-color: rgba(255, 142, 83, 0.42);
  background: #fff;
  box-shadow: 0 12px 26px rgba(255, 142, 83, 0.12);
  transform: translateY(-2px);
}

.mode-card strong,
.mode-card em,
.style-pill strong,
.style-pill em,
.size-card strong,
.size-card span {
  display: block;
  min-width: 0;
}

.mode-card strong {
  padding-right: 42px;
  font-size: 17px;
  font-weight: 900;
}

.mode-card em,
.style-pill em {
  margin-top: 8px;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
  line-height: 1.45;
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
.size-card--active {
  border-color: transparent;
  background: var(--pd-gradient-warm);
  color: #fff;
  box-shadow: var(--pd-shadow-cta);
}

.mode-card--active em,
.style-pill--active em,
.size-card--active span {
  color: rgba(255, 255, 255, 0.86);
}

.mode-card--active .option-badge {
  background: rgba(255, 255, 255, 0.22);
  color: #fff;
}

.style-pill {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 2px 10px;
  align-items: center;
  min-height: 68px;
  border-radius: 18px;
  padding: 12px;
}

.style-pill > span {
  width: 38px;
  height: 38px;
  display: grid;
  grid-row: 1 / span 2;
  place-items: center;
  border-radius: 14px;
  background: rgba(164, 212, 197, 0.2);
  color: var(--pd-fg-1);
  font-weight: 900;
}

.style-pill--active > span {
  background: rgba(255, 255, 255, 0.22);
  color: #fff;
}

.style-pill--muted:not(.style-pill--active) {
  opacity: 0.72;
}

.style-pill strong {
  font-size: 14px;
  font-weight: 900;
}

.size-card {
  min-height: 72px;
  border-radius: 18px;
  padding: 10px 8px;
  text-align: center;
}

.size-card strong {
  font-size: 22px;
  font-weight: 900;
  line-height: 1;
}

.size-card span {
  margin-top: 6px;
  color: var(--pd-fg-2);
  font-size: 11px;
  font-weight: 900;
  line-height: 1.2;
}

.upload-message {
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
  min-height: 56px;
  margin-top: 2px;
  font-size: 16px;
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
  }

  .upload-stage {
    grid-template-rows: auto auto auto;
  }

  .drop-zone {
    min-height: 360px;
  }

  .style-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .style-pill {
    grid-template-columns: 1fr;
    justify-items: start;
  }

  .style-pill > span {
    grid-row: auto;
  }
}

@media (max-width: 640px) {
  .upload-page {
    gap: 20px;
  }

  .studio-hero h1 {
    font-size: 32px;
  }

  .studio-hero p:last-child {
    font-size: 14px;
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

  .size-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .file-strip {
    align-items: start;
    flex-direction: column;
  }
}
</style>
