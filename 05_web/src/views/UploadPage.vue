<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue';

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

function useFile(file: File): void {
  if (!file.type.startsWith('image/') && !/\.(heic|heif)$/i.test(file.name)) {
    message.value = '请上传 jpg、png、webp 或 HEIC 照片。';
    return;
  }

  revokePreview();
  selectedFile.value = file;
  previewUrl.value = URL.createObjectURL(file);
  message.value = isLargeFile(file) ? '这张图比较大，后续生成前会加入压缩与方向校正。' : '照片已选好，下一批会接入生成流程。';
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

onUnmounted(revokePreview);
</script>

<template>
  <section class="upload-page">
    <div class="upload-hero">
      <p class="eyebrow">开始生成</p>
      <h1>选一张清晰照片，做成你的拼豆图纸</h1>
      <p>推荐主体清楚、光线均匀、背景简单的近距离照片。宠物、自拍、情侣照都可以先试一张。</p>
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
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleDrop"
        >
          <template v-if="previewUrl">
            <img v-if="!isHeic" class="preview-image" :src="previewUrl" alt="已选择照片预览" />
            <div v-else class="preview-fallback">
              <strong>HEIC 照片已选择</strong>
              <span>部分浏览器不能直接预览 HEIC，后续生成前会做格式处理。</span>
            </div>
          </template>
          <template v-else>
            <div class="upload-icon" aria-hidden="true">图</div>
            <strong>拖拽照片到这里，或点击选择</strong>
            <span>支持 jpg、png、webp、HEIC。手机上也可以直接拍照。</span>
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

        <p v-if="message" class="upload-message">{{ message }}</p>
        <button class="pd-btn upload-next" type="button" disabled>生成图纸将在下一批接入</button>
      </section>

      <aside class="tips-card" aria-label="照片建议">
        <p class="eyebrow">怎样效果更好</p>
        <ul>
          <li><span>近</span><strong>主体占画面大一些</strong><em>脸部、宠物头部或主要物体越清楚越好。</em></li>
          <li><span>净</span><strong>背景尽量简单</strong><em>白墙、桌面、纯色背景更容易出干净轮廓。</em></li>
          <li><span>亮</span><strong>光线均匀</strong><em>少用强背光和糊图，颜色会更接近实际豆色。</em></li>
        </ul>
        <div class="format-note">
          <strong>关于 iPhone HEIC / 大图 / 旋转</strong>
          <p>本批先保证选图和预览稳定。压缩、转码和 EXIF 方向校正会在生成链路接入时一起处理。</p>
        </div>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.upload-page {
  display: grid;
  gap: 28px;
}

.upload-hero {
  width: min(100%, 760px);
  margin: 0 auto;
  text-align: center;
}

.upload-hero h1 {
  margin: 0 0 12px;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(34px, 5vw, 54px);
  line-height: 1.08;
  letter-spacing: 0;
}

.upload-hero p:last-child {
  margin: 0 auto;
  max-width: 600px;
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
  grid-template-columns: minmax(0, 1fr) minmax(300px, 0.42fr);
  align-items: start;
  gap: 22px;
}

.upload-card,
.tips-card {
  border: 1px solid rgba(237, 228, 218, 0.82);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--pd-shadow-float);
  padding: clamp(22px, 4vw, 36px);
}

.drop-zone {
  min-height: 380px;
  display: grid;
  place-items: center;
  gap: 12px;
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
  transition: border-color var(--pd-dur-base) var(--pd-ease-out), transform var(--pd-dur-base) var(--pd-ease-out);
}

.drop-zone--active {
  border-color: var(--pd-orange);
  transform: translateY(-2px);
}

.drop-zone--filled {
  padding: 12px;
  background: #fff;
}

.drop-zone strong {
  color: var(--pd-fg-1);
  font-size: 20px;
}

.drop-zone span {
  max-width: 360px;
}

.upload-icon {
  width: 76px;
  height: 76px;
  display: grid;
  place-items: center;
  border-radius: 30px;
  background: var(--pd-gradient-warm);
  color: #fff;
  font-size: 28px;
  font-weight: 900;
  box-shadow: var(--pd-shadow-cta);
}

.preview-image {
  width: 100%;
  height: 100%;
  max-height: 520px;
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

.upload-secondary {
  border: 1px solid rgba(255, 142, 83, 0.28);
  background: var(--pd-peach-50);
  color: var(--pd-orange);
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
}

.upload-message {
  margin: 14px 0 0;
  border-radius: 16px;
  background: rgba(164, 212, 197, 0.18);
  color: var(--pd-fg-2);
  font-size: 13px;
  font-weight: 800;
  padding: 12px 14px;
}

.upload-next {
  width: 100%;
  margin-top: 14px;
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
}

.format-note {
  border-radius: 18px;
  background: rgba(164, 212, 197, 0.16);
  padding: 16px;
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
    font-size: 32px;
  }

  .upload-card,
  .tips-card {
    border-radius: 22px;
    padding: 20px;
  }

  .drop-zone {
    min-height: 300px;
    border-radius: 20px;
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
