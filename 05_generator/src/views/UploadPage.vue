<script setup lang="ts">
import LiftTitle from "../../../05_studio/src/components/LiftTitle.vue";
import { gt } from '../i18n';
import { vToolDialog } from '../dialog';
import InfoTip from '../../../05_studio/src/components/InfoTip.vue';
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { getSkus, getWalletProfile } from '../api';
import type { User } from '../api/types';
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
import { useAuthStore } from '../stores/auth';

type TooltipKey = 'mode' | 'size';

const router = useRouter();
const generation = useGenerationStore();
const auth = useAuthStore();
const galleryInput = ref<HTMLInputElement | null>(null);
const cameraInput = ref<HTMLInputElement | null>(null);
const customWidthField = ref<HTMLInputElement | null>(null);
const customHeightField = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const previewUrl = ref('');
const isDragging = ref(false);
const message = ref('');
const customWidthInput = ref('120');
const customHeightInput = ref('120');
const activeTooltip = ref<TooltipKey | null>(null);
const isConfirmOpen = ref(false);
const isCustomSizeSelected = ref(false);
const walletProfile = ref<User | null>(null);
const skuAiCost = ref(0);
const CUSTOM_MIN_SIZE = 20;
const CUSTOM_MAX_SIZE = 200;

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

const isCustomPresetSize = computed(() => RESULT_SIZE_OPTIONS.includes(generation.selectedSize as (typeof RESULT_SIZE_OPTIONS)[number]));
const isCustomSizeActive = computed(() => isCustomSizeSelected.value || !isCustomPresetSize.value);
const generationVerb = computed(() => GENERATION_MODE_DETAILS[generation.generationMode].label);
const selectedSizeLabel = computed(() => resultSizeLabel(generation.selectedSize));
const selectedStyleLabel = computed(() => STYLE_OPTION_DETAILS[generation.selectedStyle].label);
const isAiMode = computed(() => generation.generationMode === 'ai');
const walletUser = computed(() => auth.user || walletProfile.value);
const isUnlimitedAccount = computed(() => Boolean(walletUser.value?.is_unlimited_account));
const aiCost = computed(() => Number(walletUser.value?.ai_generation_cost_points || skuAiCost.value || 0));
const membershipExpiresAt = computed(() => walletUser.value?.membership_expires_at || walletUser.value?.monthly_card_expires_at || null);
const membershipActive = computed(() => {
  if (isUnlimitedAccount.value) {
    return true;
  }
  if (!membershipExpiresAt.value) {
    return false;
  }
  const expiresAt = Date.parse(membershipExpiresAt.value);
  return Number.isFinite(expiresAt) && expiresAt > Date.now();
});
const aiModeCostText = computed(() => aiCost.value ? `${formatInteger(aiCost.value)} 积分/张` : '积分同步中');
const normalModeCostText = computed(() => '消耗 1 次 · 会员期内无限');
const aiCtaCostText = computed(() => aiCost.value ? `消耗 ${formatInteger(aiCost.value)} 积分` : '积分同步中');
const normalCtaCostText = computed(() => '免费');
const customSizeDraft = computed(() => ({
  width: parseCustomDimension(customWidthInput.value),
  height: parseCustomDimension(customHeightInput.value)
}));
const isCustomSizeValid = computed(() => (
  isValidCustomDimension(customSizeDraft.value.width) &&
  isValidCustomDimension(customSizeDraft.value.height) &&
  customSizeDraft.value.width/customSizeDraft.value.height>=0.5 && customSizeDraft.value.width/customSizeDraft.value.height<=2
));
const hasInvalidCustomSize = computed(() => isCustomSizeActive.value && !isCustomSizeValid.value);
const canStartGenerate = computed(() => Boolean(selectedFile.value) && !hasInvalidCustomSize.value);
const creditSummary = computed(() => {
  if (isAiMode.value) {
    return aiCost.value ? `本次消耗 ${formatInteger(aiCost.value)} 积分，生成成功才扣` : 'AI 积分同步中，生成成功才扣';
  }
  return '普通模式免费不限次';
});
const ctaLabel = computed(() => {
  if (hasInvalidCustomSize.value) {
    return '请检查格数与长宽比例';
  }
  if (!selectedFile.value) {
    return '选择照片后开始生成';
  }
  return `开始生成 · ${isAiMode.value ? aiCtaCostText.value : normalCtaCostText.value}`;
});

function modeCostLabel(mode: GenerationMode): string {
  return mode === 'ai' ? aiModeCostText.value : normalModeCostText.value;
}

async function refreshWalletContext(): Promise<void> {
  try {
    if (auth.isLoggedIn) {
      await auth.refreshProfile();
      walletProfile.value = null;
    } else {
      walletProfile.value = await getWalletProfile();
    }
  } catch {
    if (!auth.isLoggedIn) {
      walletProfile.value = null;
    }
  }
  if (!aiCost.value) {
    await refreshSkuCost();
  }
}

async function refreshSkuCost(): Promise<void> {
  try {
    const catalog = await getSkus();
    skuAiCost.value = Number(catalog.ai_generation_cost_points || 0);
  } catch {
    skuAiCost.value = 0;
  }
}

function formatInteger(value: number): string {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 }).format(Math.max(0, Math.floor(value)));
}

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
  if (/\.(heic|heif)$/i.test(file.name)||/heic|heif/i.test(file.type)) {
    message.value='请先将 HEIC 照片转换为 JPG 或 PNG。';return;
  }
  if (!/^(image\/(jpeg|png|webp))$/i.test(file.type)&&!(/\.(jpe?g|png|webp)$/i.test(file.name)&&!file.type)) {
    message.value='请上传 JPG、PNG 或 WebP 照片。';return;
  }
  if(file.size>12*1024*1024-65536){message.value='照片过大，请选择小于 12 MB 的图片。';return;}

  revokePreview();
  selectedFile.value = file;
  generation.setSourceFile(file);
  previewUrl.value = URL.createObjectURL(file);
  message.value = isLargeFile(file) ? '照片较大，上传可能需要一些时间。' : '照片已就位，可以开始生成。';
}

function clearFile(): void {
  revokePreview();
  selectedFile.value = null;
  generation.clearSourceFile();
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
  if (!ensureCustomSizeReady()) {
    return;
  }
  isConfirmOpen.value = true;
}

async function confirmGenerate(): Promise<void> {
  if (!selectedFile.value) {
    isConfirmOpen.value = false;
    message.value = '请先选择一张照片。';
    return;
  }
  if (!ensureCustomSizeReady()) {
    isConfirmOpen.value = false;
    return;
  }
  isConfirmOpen.value = false;
  await continueGenerate();
}

async function continueGenerate(): Promise<void> {
  if (!selectedFile.value) {
    message.value = '请先选择一张照片。';
    return;
  }
  if (!ensureCustomSizeReady()) {
    return;
  }
  generation.setSourceFile(selectedFile.value);
  await router.push({ name: 'tools-loading', query: { from: 'upload' } });
}

function closeConfirm(): void {
  isConfirmOpen.value = false;
}

function chooseMode(mode: GenerationMode): void {
  generation.setGenerationMode(mode);
}

function chooseStyle(style: GenerationStylePreset): void {
  if (!isAiMode.value) {
    return;
  }
  generation.setStyle(style);
}

function chooseSize(size: ResultSizePreset): void {
  isCustomSizeSelected.value = false;
  generation.setSize(size);
  message.value = '';
}

function chooseCustomSize(): boolean {
  isCustomSizeSelected.value = true;
  const { width, height } = customSizeDraft.value;
  if (!isValidCustomDimension(width) || !isValidCustomDimension(height) || width/height<0.5 || width/height>2) {
    return false;
  }
  generation.setSize(`${width}x${height}` as ResultSizePreset);
  message.value = '';
  return true;
}

function focusCustomSize(): void {
  chooseCustomSize();
  window.setTimeout(() => customWidthField.value?.focus(), 0);
}

function handleCustomSizeInput(axis: 'width' | 'height'): void {
  if (axis === 'width') {
    customWidthInput.value = sanitizeDimensionInput(customWidthInput.value);
  } else {
    customHeightInput.value = sanitizeDimensionInput(customHeightInput.value);
  }
  chooseCustomSize();
}

function commitCustomSize(): void {
  if (!chooseCustomSize() && isCustomSizeActive.value) {
    message.value = '自定义格数每边需为 20–200，宽高比在 1:2 到 2:1 之间。';
  }
}

function sanitizeDimensionInput(rawValue: string): string {
  return rawValue.replace(/\D/g, '').slice(0, 3);
}

function parseCustomDimension(rawValue: string): number {
  const parsed = Number.parseInt(rawValue, 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function isValidCustomDimension(value: number): boolean {
  return value >= CUSTOM_MIN_SIZE && value <= CUSTOM_MAX_SIZE;
}

function ensureCustomSizeReady(): boolean {
  if (!isCustomSizeActive.value) {
    return true;
  }
  if (chooseCustomSize()) {
    return true;
  }
  message.value = '自定义格数每边需为 20–200，宽高比在 1:2 到 2:1 之间。';
  return false;
}

function showTooltip(key: TooltipKey): void {
  activeTooltip.value = key;
}

function hideTooltip(key: TooltipKey): void {
  if (activeTooltip.value === key) {
    activeTooltip.value = null;
  }
}

onMounted(() => {
  void refreshWalletContext();
  if(!RESULT_SIZE_OPTIONS.includes(generation.selectedSize as any)){const [w,h]=generation.selectedSize.split('x');customWidthInput.value=w;customHeightInput.value=h;isCustomSizeSelected.value=true;}
  if(generation.sourceFile){selectedFile.value=generation.sourceFile;previewUrl.value=URL.createObjectURL(generation.sourceFile);}
});

onUnmounted(revokePreview);
</script>

<template>
  <section class="upload-page">
    <div class="studio-shell">
      <section class="upload-stage" :aria-label='gt("上传照片")'>
        <input
          ref="galleryInput"
          class="sr-only"
          type="file"
          :aria-label="gt('从相册选择')"
          tabindex="-1"
          accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
          @change="handleInput"
        />
        <input
          ref="cameraInput"
          class="sr-only"
          type="file"
          :aria-label="gt('拍一张')"
          tabindex="-1"
          accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
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
            <img v-if="!isHeic" class="preview-image" :src="previewUrl" :alt='gt("已选择照片预览")' />
            <div v-else class="preview-fallback">
              <strong>{{ gt("HEIC 照片已选择") }}</strong>
              <span>{{ gt("可以继续生成。") }}</span>
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
            <strong>{{ gt("拖拽照片到这里") }}</strong>
            <span>{{ gt("或点击选择图片") }}</span>
          </template>
        </div>

        <div class="stage-actions">
          <button class="pd-btn pd-btn--primary" type="button" @click="openGallery">{{ gt("从相册选择") }}</button>
          <button class="pd-btn stage-secondary" type="button" @click="openCamera">{{ gt("拍一张") }}</button>
        </div>

        <div v-if="selectedFile" class="file-strip">
          <div>
            <strong>{{ selectedFile.name }}</strong>
            <span>{{ gt(selectedFile.type || 'image/*') }} · {{ gt(fileSizeMb) }}</span>
          </div>
          <button type="button" @click="clearFile">{{ gt("重新选择") }}</button>
        </div>
      </section>

      <aside class="control-panel" :aria-label='gt("生成选项")'>
        <section class="option-group" :aria-label='gt("生成方式")'>
          <div class="option-heading">
            <div class="heading-title">
              <strong>{{ gt("生成方式") }}</strong>
              <InfoTip :label="gt('生成方式说明')"><p>{{ gt(modeTooltip) }}</p></InfoTip>
            </div>
            <span class="heading-note">{{ gt("AI 默认推荐") }}</span>
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
                {{ gt(GENERATION_MODE_DETAILS[mode].badge) }}
              </span>
              <strong>{{ gt(GENERATION_MODE_DETAILS[mode].label) }}</strong>
              <span class="mode-cost">{{ gt(modeCostLabel(mode)) }}</span>
            </button>
          </div>
        </section>

        <section class="option-group style-option-group" :class="{ 'style-option-group--locked': !isAiMode }" :aria-label='gt("风格")'>
          <div class="option-heading">
            <strong>{{ gt("风格") }}</strong>
            <span class="heading-note">{{ gt(isAiMode ? 'Q版风格化' : '仅 AI 模式可用') }}</span>
          </div>
          <div class="style-grid">
            <button
              v-for="style in STYLE_OPTIONS"
              :key="style"
              type="button"
              class="style-pill"
              :class="{ 'style-pill--active': generation.selectedStyle === style }"
              :aria-pressed="generation.selectedStyle === style"
              :disabled="!isAiMode"
              @click="chooseStyle(style)"
            >
              <span class="style-icon" aria-hidden="true">
                <img :src="STYLE_OPTION_DETAILS[style].iconSrc" :alt="gt(`${STYLE_OPTION_DETAILS[style].label}图标`)" />
              </span>
              <span class="style-copy">
                <strong>{{ gt(STYLE_OPTION_DETAILS[style].label) }}</strong>
                <em>{{ gt(STYLE_OPTION_DETAILS[style].hint) }}</em>
              </span>
            </button>
          </div>
          <div v-if="!isAiMode" class="style-lock" aria-hidden="true">
            <span>{{ gt("仅 AI 模式可用") }}</span>
          </div>
        </section>

        <section class="option-group" :aria-label='gt("目标格数")'>
          <div class="option-heading">
            <div class="heading-title">
              <strong>{{ gt("目标格数") }}</strong>
              <InfoTip :label="gt('目标格数说明')"><p>{{ gt(sizeTooltip) }}</p></InfoTip>
            </div>
            <span class="heading-note">{{ gt("按拼豆板规格") }}</span>
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
              <strong>{{ gt(SIZE_OPTION_DETAILS[size].label) }}</strong>
            </button>
          </div>
          <label
            class="custom-size-field"
            :class="{ 'custom-size-field--active': isCustomSizeActive }"
            @click="focusCustomSize"
          >
            <strong>{{ gt("自定义") }}</strong>
            <span class="dimension-inputs">
              <input
                ref="customWidthField"
                v-model="customWidthInput"
                type="text"
                inputmode="numeric"
                pattern="[0-9]*"
                :aria-label='gt("自定义宽度")'
                @click.stop
                @focus="chooseCustomSize"
                @input="handleCustomSizeInput('width')"
                @blur="commitCustomSize"
              />
              <i aria-hidden="true">×</i>
              <input
                ref="customHeightField"
                v-model="customHeightInput"
                type="text"
                inputmode="numeric"
                pattern="[0-9]*"
                :aria-label='gt("自定义高度")'
                @click.stop
                @focus="chooseCustomSize"
                @input="handleCustomSizeInput('height')"
                @blur="commitCustomSize"
              />
            </span>
            <span>{{ gt("按拼豆板规格更好拼") }}</span>
          </label>
        </section>
      </aside>

      <div class="generate-bar">
        <p v-if="message" class="upload-message">{{ gt(message) }}</p>
        <button class="pd-btn generate-cta" type="button" :disabled="!canStartGenerate" @click="startGenerate">
          {{ gt(ctaLabel) }}
        </button>
      </div>
    </div>

    <div v-if="isConfirmOpen" class="confirm-backdrop" role="presentation" @click.self="closeConfirm">
      <dialog class="confirm-dialog" v-tool-dialog="closeConfirm" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <button class="confirm-close" type="button" :aria-label='gt("关闭确认弹窗")' @click="closeConfirm">×</button>
        <LiftTitle id="confirm-title" as="h2" :text="gt('确认这次生成设置')"/>
        <dl class="confirm-summary">
          <div>
            <dt>{{ gt("生成方式") }}</dt>
            <dd>{{ gt(generationVerb) }}</dd>
          </div>
          <div>
            <dt>{{ gt("风格") }}</dt>
            <dd>{{ gt(isAiMode ? selectedStyleLabel : '普通模式不使用风格') }}</dd>
          </div>
          <div>
            <dt>{{ gt("格数") }}</dt>
            <dd>{{ gt(selectedSizeLabel) }}</dd>
          </div>
          <div>
            <dt>{{ gt("本次消耗") }}</dt>
            <dd>{{ gt(creditSummary) }}</dd>
          </div>
        </dl>
        <div class="confirm-actions">
          <button class="pd-btn confirm-cancel" type="button" @click="closeConfirm">{{ gt("取消") }}</button>
          <button class="pd-btn pd-btn--primary confirm-submit" type="button" @click="confirmGenerate">{{ gt("确认生成") }}</button>
        </div>
      </dialog>
    </div>

  </section>
</template>

<style scoped>
.upload-page {
  padding: 0 0 clamp(18px, 3vh, 24px);
  overflow-x: clip;
}

.studio-shell {
  width: min(100%, 1100px);
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(280px, 0.82fr) minmax(0, 1.18fr);
  grid-template-rows: minmax(0, 1fr) auto;
  grid-template-areas:
    "controls upload"
    "controls action";
  gap: clamp(12px, 1.8vw, 20px) clamp(16px, 2.2vw, 26px);
  align-items: stretch;
  justify-content: center;
  min-width: 0;
}

.upload-stage,
.control-panel {
  border: 1px solid rgba(242, 247, 250, 0.86);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--pd-shadow-float);
  min-width: 0;
  padding: clamp(14px, 2.3vw, 26px);
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.upload-stage:hover,
.control-panel:hover {
  border-color: rgba(134, 162, 184, 0.36);
  box-shadow: 0 22px 54px rgba(134, 162, 184, 0.15), 0 16px 36px rgba(45, 45, 45, 0.08);
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
  min-height: clamp(220px, 30vw, 340px);
  flex: 1 1 auto;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  overflow: hidden;
  border: 2px dashed rgba(134, 162, 184, 0.3);
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(235, 243, 249, 0.1), rgba(164, 212, 197, 0.12)),
    repeating-linear-gradient(45deg, rgba(242, 247, 250, 0.24) 0 1px, transparent 1px 14px),
    #f7f9fb;
  color: var(--pd-fg-2);
  cursor: pointer;
  padding: clamp(16px, 2.5vw, 24px);
  text-align: center;
  transition:
    border-color 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.drop-zone:hover {
  border-color: rgba(134, 162, 184, 0.7);
  box-shadow: inset 0 0 0 1px rgba(134, 162, 184, 0.22), 0 18px 34px rgba(134, 162, 184, 0.18);
  transform: translateY(-3px);
}

.drop-zone--active {
  border-style: solid;
  border-color: var(--pd-orange);
  background:
    linear-gradient(135deg, rgba(235, 243, 249, 0.2), rgba(184, 164, 237, 0.16)),
    #f7f9fb;
  box-shadow: 0 20px 42px rgba(134, 162, 184, 0.22), 0 0 0 4px rgba(134, 162, 184, 0.12);
  transform: translateY(-4px) scale(1.008);
}

.drop-zone--filled {
  border-style: solid;
  border-color: rgba(242, 247, 250, 0.92);
  background: #fff;
  padding: 12px;
}

.drop-zone strong {
  color: var(--pd-fg-1);
  font-family: var(--pd-font-body);
  font-size: clamp(19px, 2.6vw, 22px);
  font-weight: 600;
}

.drop-zone > span {
  color: var(--pd-fg-2);
  font-weight: 500;
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
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.58), inset 0 -40px 80px rgba(134, 162, 184, 0.06);
}

.preview-fallback {
  display: grid;
  gap: 8px;
  place-items: center;
  border-radius: 20px;
  background: rgba(235, 243, 249, 0.14);
  padding: 32px;
}

.stage-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: clamp(8px, 1.6vw, 12px);
}

.stage-secondary {
  border: 1px solid rgba(134, 162, 184, 0.28);
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
  border-color: rgba(134, 162, 184, 0.58);
  box-shadow: 0 16px 28px rgba(134, 162, 184, 0.2);
  transform: translateY(-2px);
}

.file-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  border: 1px solid var(--pd-stroke);
  border-radius: 18px;
  background: rgba(235, 243, 249, 0.58);
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
  font-weight: 500;
}

.file-strip button {
  flex: 0 0 auto;
  border: 0;
  background: transparent;
  color: var(--pd-orange);
  cursor: pointer;
  font: inherit;
  font-weight: 600;
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

.style-option-group {
  position: relative;
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
  font-family: var(--pd-font-body);
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
}

.heading-note {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 600;
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
  border: 1px solid rgba(134, 162, 184, 0.34);
  border-radius: 999px;
  background: rgba(235, 243, 249, 0.88);
  color: var(--pd-orange);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  transition:
    border-color 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.info-trigger:hover,
.info-trigger:focus-visible {
  border-color: rgba(134, 162, 184, 0.72);
  background: #fff;
  box-shadow: 0 8px 18px rgba(134, 162, 184, 0.16);
  outline: none;
  transform: translateY(-1px);
}

.legacy-info-tip {
  position: absolute;
  top: calc(100% + 10px);
  left: 0;
  z-index: 6;
  width: min(312px, 76vw);
  border: 1px solid rgba(134, 162, 184, 0.3);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 18px 42px rgba(45, 45, 45, 0.12), 0 10px 24px rgba(134, 162, 184, 0.12);
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 500;
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
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: clamp(86px, 8vw, 98px);
  border-radius: 20px;
  padding: 13px clamp(8px, 1.6vw, 14px) 12px;
}

.mode-card:hover,
.style-pill:hover,
.size-card:hover,
.custom-size-field:hover {
  border-color: rgba(134, 162, 184, 0.62);
  background: #fff;
  box-shadow: 0 14px 28px rgba(134, 162, 184, 0.16);
  transform: translateY(-2px);
}

.mode-card strong,
.mode-cost,
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
  display: flex;
  align-items: center;
  justify-content: center;
  padding-right: 0;
  font-family: var(--pd-font-body);
  font-size: clamp(22px, 2.4vw, 26px);
  font-weight: 600;
  line-height: 1;
  text-align: center;
  transform: translateY(3px);
  white-space: nowrap;
}

.mode-cost {
  color: var(--pd-fg-2);
  font-size: clamp(10px, 1.35vw, 12px);
  font-weight: 600;
  line-height: 1.25;
  text-align: center;
  transform: translateY(3px);
  white-space: nowrap;
}

.style-pill em {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-style: normal;
  font-weight: 500;
  line-height: 1.45;
  white-space: nowrap;
}

.option-badge {
  position: absolute;
  top: 7px;
  right: 7px;
  border-radius: 999px;
  background: rgba(235, 243, 249, 0.12);
  color: var(--pd-pink-deep);
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
  padding: 3px 7px;
}

.mode-card--active,
.style-pill--active,
.size-card--active,
.custom-size-field--active {
  border-color: transparent;
  background: var(--pd-gradient-warm);
  color: var(--pd-fg-1);
  box-shadow: var(--pd-shadow-cta);
}

.mode-card--active:hover,
.style-pill--active:hover,
.size-card--active:hover,
.custom-size-field--active:hover {
  border-color: rgba(134, 162, 184, 0.7);
  background: var(--pd-gradient-warm);
  color: var(--pd-fg-1);
  box-shadow: 0 18px 34px rgba(134, 162, 184, 0.26), 0 9px 18px rgba(134, 162, 184, 0.18);
}

.style-pill--active em,
.mode-card--active .mode-cost,
.size-card--active span {
  color: var(--pd-fg-2);
}

.style-pill--active:hover em,
.mode-card--active:hover .mode-cost,
.size-card--active:hover span {
  color: var(--pd-fg-2);
}

.mode-card--active .option-badge {
  background: rgba(255, 255, 255, 0.22);
  color: var(--pd-fg-1);
}

.style-pill {
  display: grid;
  grid-template-columns: clamp(40px, 5vw, 48px) minmax(0, 1fr);
  gap: clamp(9px, 1.5vw, 12px);
  align-items: center;
  justify-items: start;
  min-height: 72px;
  border-radius: 18px;
  padding: 11px clamp(12px, 1.8vw, 16px);
}

.style-pill:disabled {
  cursor: not-allowed;
}

.style-icon {
  width: clamp(40px, 5vw, 48px);
  height: clamp(40px, 5vw, 48px);
  display: grid;
  place-items: center;
  justify-self: start;
  align-self: center;
  border-radius: 16px;
  background: rgba(235, 243, 249, 0.72);
  box-shadow: inset 0 0 0 1px rgba(242, 247, 250, 0.62);
  overflow: hidden;
}

.style-icon img {
  width: clamp(35px, 4.4vw, 42px);
  height: clamp(35px, 4.4vw, 42px);
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

.style-copy {
  display: grid;
  gap: 4px;
  align-content: center;
  justify-items: start;
  line-height: 1.2;
}

.style-pill strong {
  font-family: var(--pd-font-body);
  font-size: clamp(14px, 1.65vw, 16px);
  font-weight: 600;
  line-height: 1.15;
  white-space: nowrap;
}

.style-pill em {
  margin-top: 0;
  font-size: clamp(11px, 1.3vw, 12px);
  line-height: 1.3;
}

.size-card {
  min-height: clamp(56px, 7vw, 64px);
  border-radius: 18px;
  padding: 9px 5px;
  text-align: center;
}

.size-card strong {
  font-family: var(--pd-font-body);
  font-size: clamp(19px, 2.1vw, 22px);
  font-weight: 600;
  line-height: 1;
}

.custom-size-field {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: clamp(8px, 1.5vw, 10px);
  align-items: center;
  min-height: 64px;
  border-radius: 18px;
  margin-top: 10px;
  padding: clamp(10px, 1.7vw, 12px) clamp(12px, 1.8vw, 14px);
  text-align: left;
}

.custom-size-field strong {
  font-family: var(--pd-font-body);
  font-size: clamp(14px, 1.65vw, 16px);
  font-weight: 600;
  white-space: nowrap;
}

.dimension-inputs {
  display: grid;
  grid-template-columns: minmax(44px, 1fr) auto minmax(44px, 1fr);
  align-items: center;
  gap: 7px;
}

.dimension-inputs i {
  color: var(--pd-fg-2);
  font-style: normal;
  font-weight: 600;
}

.custom-size-field input {
  width: 100%;
  min-width: 0;
  height: 38px;
  border: 1px solid rgba(134, 162, 184, 0.34);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.82);
  color: var(--pd-fg-1);
  cursor: text;
  font: inherit;
  font-size: clamp(16px, 1.8vw, 18px);
  font-weight: 600;
  outline: none;
  padding: 0 10px;
  text-align: center;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out);
}

.custom-size-field input:focus {
  border-color: rgba(134, 162, 184, 0.72);
  box-shadow: 0 0 0 4px rgba(134, 162, 184, 0.12);
}

.custom-size-field span {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 600;
  line-height: 1.25;
  white-space: nowrap;
}

.custom-size-field--active input {
  border-color: var(--pd-fg-2);
  background: rgba(255, 255, 255, 0.2);
  color: var(--pd-fg-1);
}

.custom-size-field--active .dimension-inputs i {
  color: var(--pd-fg-2);
}

.custom-size-field--active input::placeholder,
.custom-size-field--active span {
  color: var(--pd-fg-2);
}

.style-lock {
  position: absolute;
  inset: 36px 0 0;
  z-index: 2;
  display: grid;
  place-items: center;
  border: 1px solid rgba(134, 162, 184, 0.24);
  border-radius: 20px;
  background: rgba(235, 243, 249, 0.62);
  backdrop-filter: blur(9px) saturate(1.08);
  color: var(--pd-fg-1);
  pointer-events: auto;
}

.style-lock span {
  border: 1px solid rgba(134, 162, 184, 0.32);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 12px 24px rgba(134, 162, 184, 0.14);
  color: var(--pd-orange);
  font-family: var(--pd-font-body);
  font-size: 15px;
  font-weight: 600;
  padding: 9px 15px;
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
  font-weight: 500;
  padding: 12px 14px;
}

.generate-cta {
  width: 100%;
  min-height: clamp(54px, 6vw, 60px);
  border: 1px solid transparent;
  font-size: clamp(15px, 1.8vw, 17px);
}

.generate-cta:not(:disabled) {
  background: var(--pd-gradient);
  color: var(--pd-fg-1);
  box-shadow: var(--pd-shadow-cta);
}

.generate-cta:disabled {
  background: #f7f9fb;
  color: #9b8e84;
  box-shadow: none;
  cursor: not-allowed;
}

.confirm-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  background: rgba(45, 36, 30, 0.26);
  backdrop-filter: blur(8px);
  padding: 18px;
  animation: fadeIn 160ms var(--pd-ease-out);
}

.auth-backdrop {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  place-items: center;
  overflow-y: auto;
  background: rgba(45, 36, 30, 0.26);
  backdrop-filter: blur(12px);
  padding: clamp(14px, 4vw, 28px);
  animation: fadeIn 160ms var(--pd-ease-out);
}

.auth-modal {
  position: relative;
  width: min(100%, 520px);
}

.auth-modal__close {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 30;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(134, 162, 184, 0.22);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 10px 24px rgba(45, 36, 30, 0.08);
  color: var(--pd-fg-2);
  cursor: pointer;
  font: inherit;
  font-size: 20px;
  font-weight: 600;
  line-height: 1;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    color 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.auth-modal__close:hover {
  border-color: rgba(134, 162, 184, 0.5);
  box-shadow: 0 10px 20px rgba(134, 162, 184, 0.14);
  color: var(--pd-orange);
  transform: translateY(-1px);
}

.confirm-dialog {
  position: relative;
  width: min(100%, 440px);
  max-height: min(680px, calc(100dvh - 36px));
  overflow-y: auto;
  overscroll-behavior: contain;
  border: 1px solid rgba(242, 247, 250, 0.9);
  border-radius: 28px;
  background:
    linear-gradient(145deg, #fff, #f7f9fb),
    #f7f9fb;
  box-shadow: var(--pd-shadow-modal), 0 18px 44px rgba(134, 162, 184, 0.18);
  padding: 24px;
  animation: modalPop 190ms var(--pd-ease-soft);
}

.confirm-close {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(134, 162, 184, 0.22);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--pd-fg-2);
  cursor: pointer;
  font: inherit;
  font-size: 20px;
  font-weight: 600;
  line-height: 1;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    color 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.confirm-close:hover {
  border-color: rgba(134, 162, 184, 0.5);
  box-shadow: 0 10px 20px rgba(134, 162, 184, 0.14);
  color: var(--pd-orange);
  transform: translateY(-1px);
}

.confirm-dialog h2 {
  margin: 0 42px 18px 0;
  color: var(--pd-orange);
  font-family: var(--pd-font-body);
  font-size: 25px;
  line-height: 1.2;
}

.confirm-summary {
  display: grid;
  gap: 10px;
  margin: 0;
}

.confirm-summary div {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  border: 1px solid rgba(242, 247, 250, 0.76);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.94);
  padding: 12px 13px;
}

.confirm-summary dt,
.confirm-summary dd {
  margin: 0;
}

.confirm-summary dt {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 600;
}

.confirm-summary dd {
  color: var(--pd-fg-1);
  font-weight: 600;
}

.confirm-actions {
  display: grid;
  grid-template-columns: 0.8fr 1.2fr;
  gap: 12px;
  margin-top: 18px;
}

.confirm-cancel,
.confirm-submit {
  cursor: pointer;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    filter 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.confirm-cancel {
  border: 1px solid rgba(134, 162, 184, 0.28);
  background: rgba(235, 243, 249, 0.72);
  color: var(--pd-orange);
}

.confirm-cancel:hover,
.confirm-submit:hover {
  filter: brightness(1.03);
  border-color: rgba(134, 162, 184, 0.58);
  box-shadow: 0 14px 28px rgba(134, 162, 184, 0.18);
  transform: translateY(-2px);
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

@keyframes fadeIn {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}

@keyframes modalPop {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.98);
  }

  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (max-width: 860px) {
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
    min-height: clamp(260px, 54vw, 360px);
  }

  .style-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .upload-page {
    padding-top: 0;
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
  .style-grid {
    grid-template-columns: 1fr;
  }

  .mode-card {
    min-height: 82px;
  }

  .style-pill em,
  .custom-size-field span {
    white-space: normal;
  }

  .style-pill {
    grid-template-columns: clamp(40px, 12vw, 48px) minmax(0, 1fr);
    min-height: 70px;
    padding: 11px 14px;
  }

  .size-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .custom-size-field {
    grid-template-columns: minmax(0, 1fr);
    gap: 8px 10px;
  }

  .dimension-inputs {
    width: 100%;
  }

  .custom-size-field span {
    line-height: 1.35;
  }

  .file-strip {
    align-items: start;
    flex-direction: column;
  }

  .confirm-dialog {
    border-radius: 24px;
    padding: 20px;
  }

  .confirm-summary div,
  .confirm-actions {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 420px) {
  .studio-shell {
    gap: 14px;
  }

  .mode-grid,
  .size-grid {
    gap: 8px;
  }

  .mode-card {
    min-height: 80px;
    padding-inline: 6px;
  }

  .style-pill {
    padding-inline: 12px;
  }

  .custom-size-field {
    padding: 10px 12px;
  }
}
</style>
