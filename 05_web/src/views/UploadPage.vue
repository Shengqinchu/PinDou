<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import {
  DEFAULT_GENERATION_SIZE,
  RESULT_SIZE_OPTIONS,
  SIZE_OPTION_DETAILS,
  useGenerationStore,
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
const sizeOptions = RESULT_SIZE_OPTIONS;

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
  generation.setSize(DEFAULT_GENERATION_SIZE);
  previewUrl.value = URL.createObjectURL(file);
  message.value = isLargeFile(file) ? '照片较大也没关系，我们会在生成前自动整理。' : '照片已选好，可以开始生成了。';
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

function chooseSize(size: ResultSizePreset): void {
  generation.setSize(size);
}

onUnmounted(revokePreview);
</script>

<template>
  <section class="upload-page">
    <div class="upload-hero">
      <p class="eyebrow">开始生成</p>
      <h1>选一张清晰照片，做成你的<span>专属拼豆图纸</span></h1>
      <p>主体清楚、光线柔和、背景简单的近距离照片效果最好。宠物、自拍、情侣照都可以先试一张。</p>
    </div>

    <div class="upload-layout">
      <section class="upload-card" aria-label="上传照片">
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
              <span>部分浏览器不能直接预览 HEIC，也可以继续生成。</span>
            </div>
          </template>
          <template v-else>
            <div class="upload-icon" aria-hidden="true">图</div>
            <strong>拖拽照片到这里，或点击选择</strong>
            <span>支持 jpg、png、webp、HEIC；手机上也可以直接拍照。</span>
          </template>
        </div>

        <div class="upload-actions">
          <button class="pd-btn pd-btn--primary" type="button" @click="openGallery">从相册选择</button>
          <button class="pd-btn upload-secondary" type="button" @click="openCamera">拍一张</button>
        </div>

        <div v-if="selectedFile" class="file-summary">
          <div>
            <strong>{{ selectedFile.name }}</strong>
            <span>{{ selectedFile.type || 'image/*' }} · {{ fileSizeMb }}</span>
          </div>
          <button type="button" @click="clearFile">重新选择</button>
        </div>

        <section v-if="selectedFile" class="size-picker" aria-label="选择目标格数">
          <div class="size-picker__head">
            <strong>目标格数</strong>
            <span>按拼豆板规格生成</span>
          </div>
          <div class="size-picker__options">
            <button
              v-for="size in sizeOptions"
              :key="size"
              class="size-picker__option"
              type="button"
              :class="{ 'size-picker__option--active': size === generation.selectedSize }"
              :aria-pressed="size === generation.selectedSize"
              @click="chooseSize(size)"
            >
              <strong>{{ SIZE_OPTION_DETAILS[size].label }}</strong>
              <span>{{ SIZE_OPTION_DETAILS[size].hint }}</span>
            </button>
          </div>
        </section>

        <p v-if="message" class="upload-message">{{ message }}</p>
        <button class="pd-btn upload-next" type="button" :disabled="!selectedFile" @click="startGenerate">
          {{ selectedFile ? `开始生成 ${generation.selectedSize.split('x')[0]} 格 →` : '选择照片后开始生成' }}
        </button>
      </section>

      <aside class="tips-card" aria-label="照片建议">
        <p class="eyebrow">怎样效果更好</p>
        <ul>
          <li><span>近</span><strong>主体占大一些</strong><em>脸部、宠物头部或主要物体越清楚，图纸越好认。</em></li>
          <li><span>净</span><strong>背景简单干净</strong><em>白墙、桌面、纯色背景更容易保留清爽轮廓。</em></li>
          <li><span>亮</span><strong>光线柔和均匀</strong><em>避开强背光和糊图，颜色会更接近真实豆色。</em></li>
        </ul>
        <div class="format-note">
          <strong>iPhone 照片也放心</strong>
          <p>HEIC、大图和照片方向问题，我们会尽量自动处理；如果预览不显示，也可以继续试试。</p>
        </div>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.upload-page {
  display: grid;
  gap: 24px;
}

.upload-hero {
  width: min(100%, 820px);
  margin: 0 auto;
  text-align: center;
}

.upload-hero h1 {
  margin: 0 0 12px;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(34px, 4.7vw, 54px);
  line-height: 1.12;
  letter-spacing: 0;
}

.upload-hero h1 span {
  white-space: nowrap;
}

.upload-hero p:last-child {
  margin: 0 auto;
  max-width: 650px;
  color: var(--pd-fg-2);
}

.eyebrow {
  margin: 0 0 10px;
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
  text-transform: uppercase;
}

.upload-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(316px, 0.46fr);
  align-items: stretch;
  gap: 24px;
}

.upload-card,
.tips-card {
  border: 1px solid rgba(237, 228, 218, 0.82);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--pd-shadow-float);
  padding: clamp(22px, 4vw, 36px);
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out);
}

.upload-card:hover,
.tips-card:hover {
  border-color: rgba(255, 142, 83, 0.34);
  box-shadow: 0 18px 44px rgba(255, 107, 90, 0.15), 0 8px 20px rgba(45, 45, 45, 0.07);
  transform: translateY(-3px);
}

.drop-zone {
  min-height: clamp(260px, 32vw, 340px);
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  border: 2px dashed rgba(255, 142, 83, 0.28);
  border-radius: 26px;
  background:
    radial-gradient(circle at 18% 16%, rgba(255, 176, 136, 0.14), transparent 28%),
    var(--pd-peach-50);
  color: var(--pd-fg-2);
  cursor: pointer;
  overflow: hidden;
  padding: 22px;
  text-align: center;
  transition:
    border-color 180ms var(--pd-ease-out),
    border-style 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.drop-zone:hover {
  border-color: rgba(255, 142, 83, 0.58);
  box-shadow: inset 0 0 0 1px rgba(255, 176, 136, 0.16), 0 12px 28px rgba(255, 142, 83, 0.12);
  transform: translateY(-3px);
}

.drop-zone--active {
  border-style: solid;
  border-color: var(--pd-orange);
  background:
    radial-gradient(circle at 18% 16%, rgba(255, 176, 136, 0.24), transparent 30%),
    rgba(255, 241, 232, 0.96);
  box-shadow: 0 18px 38px rgba(255, 142, 83, 0.2), 0 0 0 4px rgba(255, 142, 83, 0.12);
  transform: translateY(-4px) scale(1.01);
}

.drop-zone--filled {
  padding: 12px;
  background: #fff;
}

.drop-zone strong {
  color: var(--pd-fg-1);
  font-size: 19px;
  line-height: 1.35;
}

.drop-zone span {
  max-width: 360px;
  line-height: 1.55;
}

.upload-icon {
  width: 68px;
  height: 68px;
  display: grid;
  place-items: center;
  border-radius: 26px;
  background: var(--pd-gradient-warm);
  color: #fff;
  font-size: 28px;
  font-weight: 900;
  box-shadow: var(--pd-shadow-cta);
}

.preview-image {
  width: 100%;
  height: 100%;
  max-height: 360px;
  display: block;
  border-radius: 20px;
  object-fit: contain;
}

.preview-fallback {
  display: grid;
  gap: 10px;
  place-items: center;
  border-radius: 22px;
  background: rgba(255, 176, 136, 0.15);
  padding: 36px;
}

.upload-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 16px;
}

.upload-actions .pd-btn,
.upload-next {
  transition:
    border-color 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    filter 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.upload-actions .pd-btn:hover,
.upload-next:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.01);
}

.upload-actions .pd-btn--primary:hover,
.upload-next:hover:not(:disabled) {
  filter: brightness(1.035);
  box-shadow: 0 18px 38px rgba(255, 142, 83, 0.34), 0 8px 20px rgba(255, 107, 90, 0.2);
}

.upload-secondary {
  border: 1px solid rgba(255, 142, 83, 0.28);
  background: var(--pd-peach-50);
  color: var(--pd-orange);
}

.upload-secondary:hover {
  border-color: rgba(255, 142, 83, 0.58);
  background: #fff;
  box-shadow: 0 12px 26px rgba(255, 142, 83, 0.12);
}

.file-summary {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  margin-top: 16px;
  border: 1px solid var(--pd-stroke);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.76);
  padding: 14px 16px;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.file-summary:hover {
  border-color: rgba(255, 142, 83, 0.34);
  box-shadow: var(--pd-shadow-card);
  transform: translateY(-2px);
}

.file-summary strong,
.file-summary span {
  display: block;
}

.file-summary strong {
  color: var(--pd-fg-1);
  word-break: break-all;
}

.file-summary span {
  color: var(--pd-fg-2);
  font-size: 12px;
}

.file-summary button {
  flex: 0 0 auto;
  border: 0;
  background: transparent;
  color: var(--pd-orange);
  cursor: pointer;
  font: inherit;
  font-weight: 900;
  transition: color 160ms var(--pd-ease-out), transform 160ms var(--pd-ease-out);
}

.file-summary button:hover {
  color: var(--pd-pink-deep);
  transform: translateY(-1px);
}

.size-picker {
  margin-top: 16px;
  border: 1px solid rgba(237, 228, 218, 0.82);
  border-radius: 20px;
  background: rgba(255, 241, 232, 0.54);
  padding: 16px;
}

.size-picker__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.size-picker__head strong {
  color: var(--pd-fg-1);
  font-size: 15px;
  font-weight: 900;
}

.size-picker__head span {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 800;
}

.size-picker__options {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.size-picker__option {
  appearance: none;
  min-width: 0;
  min-height: 74px;
  border: 1px solid rgba(255, 142, 83, 0.18);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
  color: var(--pd-fg-1);
  cursor: pointer;
  font: inherit;
  padding: 10px 8px;
  transition:
    border-color 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    color 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.size-picker__option:hover {
  border-color: rgba(255, 142, 83, 0.44);
  background: #fff;
  box-shadow: 0 12px 26px rgba(255, 142, 83, 0.12);
  transform: translateY(-2px);
}

.size-picker__option strong,
.size-picker__option span {
  display: block;
  min-width: 0;
}

.size-picker__option strong {
  font-size: 22px;
  font-weight: 900;
  line-height: 1;
}

.size-picker__option span {
  margin-top: 6px;
  color: var(--pd-fg-2);
  font-size: 11px;
  font-weight: 900;
  line-height: 1.2;
}

.size-picker__option--active {
  border-color: transparent;
  background: var(--pd-gradient-warm);
  color: #fff;
  box-shadow: var(--pd-shadow-cta);
}

.size-picker__option--active span {
  color: rgba(255, 255, 255, 0.88);
}

.upload-message {
  margin: 14px 0 0;
  border-radius: 16px;
  background: rgba(164, 212, 197, 0.18);
  color: var(--pd-fg-2);
  font-size: 13px;
  font-weight: 800;
  padding: 12px 14px;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.upload-message:hover {
  box-shadow: var(--pd-shadow-card);
  transform: translateY(-2px);
}

.upload-next {
  width: 100%;
  margin-top: 14px;
}

.upload-next:not(:disabled) {
  background: var(--pd-gradient);
  color: #fff;
  box-shadow: var(--pd-shadow-cta);
}

.upload-next:disabled {
  background: #ede5dd;
  color: #9b8e84;
  box-shadow: none;
  cursor: not-allowed;
}

.tips-card ul {
  display: grid;
  gap: 12px;
  margin: 0 0 18px;
  padding: 0;
  list-style: none;
}

.tips-card li {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 12px;
  border-radius: 18px;
  background: var(--pd-peach-50);
  padding: 14px;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out);
}

.tips-card li:hover {
  background: #fff;
  box-shadow: 0 12px 26px rgba(255, 142, 83, 0.12);
  transform: translateY(-3px);
}

.tips-card li span {
  width: 34px;
  height: 34px;
  display: grid;
  grid-row: 1 / span 2;
  place-items: center;
  border-radius: var(--pd-r-full);
  background: var(--pd-gradient-warm);
  color: #fff;
  font-weight: 900;
}

.tips-card strong {
  color: var(--pd-fg-1);
}

.tips-card em {
  color: var(--pd-fg-2);
  font-size: 13px;
  font-style: normal;
  line-height: 1.5;
}

.format-note {
  border-radius: 18px;
  background: rgba(164, 212, 197, 0.16);
  padding: 16px;
  transition:
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out);
}

.format-note:hover {
  background: rgba(164, 212, 197, 0.22);
  box-shadow: 0 12px 26px rgba(164, 212, 197, 0.16);
  transform: translateY(-3px);
}

.format-note p {
  margin: 8px 0 0;
  color: var(--pd-fg-2);
  font-size: 13px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}

@media (max-width: 900px) {
  .upload-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .upload-page {
    gap: 20px;
  }

  .upload-hero {
    text-align: left;
  }

  .upload-hero h1 {
    max-width: 420px;
    font-size: 32px;
  }

  .upload-card,
  .tips-card {
    border-radius: 22px;
    padding: 20px;
  }

  .drop-zone {
    min-height: 260px;
    border-radius: 20px;
  }

  .size-picker__head {
    align-items: start;
    flex-direction: column;
    gap: 2px;
  }

  .size-picker__options {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .upload-actions,
  .file-summary {
    grid-template-columns: 1fr;
  }

  .file-summary {
    display: grid;
  }
}
</style>
