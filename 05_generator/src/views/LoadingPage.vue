<script setup lang="ts">
import { gt } from '../i18n';
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { ApiError } from '../api';
import type { PaymentSkuCategory } from '../api/types';
import { requestGeneratorLogin } from '../host';
import PricingModal from '../components/PricingModal.vue';
import QuotaGuideModal from '../components/QuotaGuideModal.vue';
import {
  GENERATION_MODE_DETAILS,
  STYLE_OPTION_DETAILS,
  isResultSizePreset,
  resultSizeLabel,
  useGenerationStore
} from '../stores/generation';
import type { GenerationJobResponse } from '../api/types';

interface StageItem {
  title: string;
  detail: string;
}

const router = useRouter();
const route = useRoute();
const generation = useGenerationStore();
const activeStage = ref(0);
const progress = ref(8);
const progressCeiling = ref(92);
const serverMessage = ref('');
const error = ref('');
const quotaGuideOpen = ref(false);
const quotaKind = ref<'ai' | 'script'>('ai');
const quotaMessage = ref('');
const authModalOpen = ref(false);
const pricingOpen = ref(false);
const pricingPanel = ref<PaymentSkuCategory>('points');
const pricingReason = ref<'manual' | 'ai-low' | 'script-low'>('manual');
const pricingFocusCdk = ref(false);
let progressTimer: number | undefined;
let mounted=true,finishTimer:ReturnType<typeof setTimeout>|undefined;

const aiStages: StageItem[] = [
  { title: 'AI 风格化中', detail: '先把照片整理成 Q 版卡通' },
  { title: '提炼拼豆轮廓', detail: '保留主体、边线和大色块' },
  { title: '匹配豆色', detail: '把画面压进 MARD 色号体系' },
  { title: '导出图纸', detail: '生成网格、清单和作品记录' }
];

const scriptStages: StageItem[] = [
  { title: '整理照片', detail: '校正方向和尺寸' },
  { title: '匹配豆色', detail: '直接使用色卡量化' },
  { title: '生成图纸', detail: '保存预览和清单' }
];

const stages = computed(() => (generation.generationMode === 'ai' ? aiStages : scriptStages));
const selectedSizeLabel = computed(() => resultSizeLabel(generation.selectedSize));
const modeLabel = computed(() => GENERATION_MODE_DETAILS[generation.generationMode].label);
const styleLabel = computed(() => STYLE_OPTION_DETAILS[generation.selectedStyle].label);
const canRetry = computed(() => Boolean(generation.sourceFile)&&(!generation.submitted||!!generation.jobId));
const progressHeadline = computed(() => {
  if (error.value) {
    return '生成遇到问题';
  }
  return generation.generationMode === 'ai' ? 'Q 版豆图正在制作' : '图纸正在快速生成';
});
const progressSub = computed(() => {
  const fileName = generation.sourceFile?.name || 'PinDou 拼豆图纸';
  const style = generation.generationMode === 'ai' ? ` · ${gt(styleLabel.value)}` : '';
  return `${fileName} · ${gt(modeLabel.value)}${style} · ${gt(`${selectedSizeLabel.value} 格`)}`;
});
const liveMessage = computed(() => serverMessage.value || stages.value[activeStage.value]?.detail || '');

onMounted(() => {
  const querySize = String(route.query.size || '');
  if (isResultSizePreset(querySize)) {
    generation.setSize(querySize);
  }
  void runGeneration();
});

onUnmounted(() => {
  mounted=false;clearTimeout(finishTimer);
  stopProgress();
});

async function runGeneration(): Promise<void> {
  if (!generation.sourceFile) {
    error.value = '这次生成没有找到原图，请回到上传页重新选择。';
    progress.value = 0;
    return;
  }

  quotaGuideOpen.value = false;
  error.value = '';
  progress.value = generation.generationMode === 'ai' ? 6 : 12;
  progressCeiling.value = generation.generationMode === 'ai' ? 22 : 88;
  serverMessage.value = generation.generationMode === 'ai' ? '正在提交 AI 生成任务。' : '';
  activeStage.value = 0;
  startProgress();

  try {
    const result = await generation.generateCurrent(applyJobUpdate);
    stopProgress();
    progress.value = 100;
    activeStage.value = stages.value.length - 1;
    if(!mounted||route.name!=='tools-loading')return;
    finishTimer=setTimeout(() => {
      if(!mounted||route.name!=='tools-loading')return;
      void router.replace({ name: 'tools-result', params: { id: result.artwork_id } });
    }, 380);
  } catch (generateError) {
    if(!mounted)return;
    stopProgress();
    if (isQuotaExceeded(generateError)) {
      quotaKind.value = quotaKindFromError(generateError);
      quotaMessage.value = generateError instanceof Error ? generateError.message : '';
      serverMessage.value = '';
      progress.value = 0;
      quotaGuideOpen.value = true;
      return;
    }
    error.value = generateError instanceof Error ? generateError.message : '图纸生成失败，请重新试一次。';
  }
}

function applyJobUpdate(job: GenerationJobResponse): void {
  if(!mounted)return;
  const messages:Record<string,string>={queued:'正在提交 AI 生成任务。',ai_style:'先把照片整理成 Q 版卡通',quantize:'把画面压进 MARD 色号体系',export:'生成网格、清单和作品记录',done:'图纸已生成',completed:'图纸已生成'};
  serverMessage.value = messages[job.stage]||'';
  progress.value = Math.max(progress.value, job.progress || 0);
  progressCeiling.value = progressCeilingForStage(job.stage, job.progress);
  activeStage.value = stageIndexForJob(job.stage, job.progress);
}

function startProgress(): void {
  stopProgress();
  progressTimer = window.setInterval(() => {
    const step = generation.generationMode === 'ai' ? 3 : 6;
    const ceiling = generation.generationMode === 'ai' ? progressCeiling.value : 88;
    progress.value = Math.min(progress.value + step, ceiling);
    activeStage.value = Math.min(
      Math.floor((progress.value / 100) * stages.value.length),
      stages.value.length - 1
    );
  }, generation.generationMode === 'ai' ? 680 : 480);
}

function progressCeilingForStage(stage: string, progressValue: number): number {
  if (stage === 'queued') {
    return Math.max(progressValue, 18);
  }
  if (stage === 'ai_style') {
    return Math.max(progressValue, 54);
  }
  if (stage === 'quantize') {
    return Math.max(progressValue, 78);
  }
  if (stage === 'export') {
    return Math.max(progressValue, 94);
  }
  if (stage === 'done') {
    return 100;
  }
  return Math.max(progressValue, progressCeiling.value);
}

function stageIndexForJob(stage: string, progressValue: number): number {
  if (stage === 'export' || stage === 'done') {
    return stages.value.length - 1;
  }
  if (stage === 'quantize') {
    return Math.min(2, stages.value.length - 1);
  }
  if (progressValue >= 70) {
    return Math.min(2, stages.value.length - 1);
  }
  if (progressValue >= 38) {
    return Math.min(1, stages.value.length - 1);
  }
  return 0;
}

function stopProgress(): void {
  if (progressTimer !== undefined) {
    window.clearInterval(progressTimer);
    progressTimer = undefined;
  }
}

function isQuotaExceeded(errorValue: unknown): boolean {
  return errorValue instanceof ApiError && (errorValue.status === 402 || errorValue.code === 'QUOTA_EXCEEDED');
}

function quotaKindFromError(errorValue: unknown): 'ai' | 'script' {
  const detail = errorValue instanceof ApiError ? errorValue.detail : null;
  if (isRecord(detail) && detail.kind === 'script') {
    return 'script';
  }
  return generation.generationMode === 'script' ? 'script' : 'ai';
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function openQuotaRedeem(): void {
  quotaGuideOpen.value = false;
  pricingPanel.value = quotaKind.value === 'script' ? 'membership' : 'points';
  pricingReason.value = quotaKind.value === 'script' ? 'script-low' : 'ai-low';
  pricingFocusCdk.value = true;
  pricingOpen.value = true;
}

async function openQuotaRegister(): Promise<void> {
  quotaGuideOpen.value = false;
  if(await requestGeneratorLogin())await runGeneration();
}

function openQuotaRecharge(): void {
  quotaGuideOpen.value = false;
  pricingPanel.value = quotaKind.value === 'script' ? 'membership' : 'points';
  pricingReason.value = quotaKind.value === 'script' ? 'script-low' : 'ai-low';
  pricingFocusCdk.value = false;
  pricingOpen.value = true;
}

function closePricing(): void {
  pricingOpen.value = false;
  pricingFocusCdk.value = false;
}

async function handlePricingSuccess(): Promise<void> {
  closePricing();
  await runGeneration();
}

async function handleAuthSuccess(): Promise<void> {
  authModalOpen.value = false;
  await runGeneration();
}

function closeAuthModal(): void {
  authModalOpen.value = false;
}

</script>

<template>
  <section class="loading-page">
    <div class="loading-panel">
      <div class="loading-copy">
        <h1>{{ gt(progressHeadline) }}</h1>
        <p class="loading-sub">{{ progressSub }}</p>
        <p v-if="liveMessage" class="loading-live">{{ gt(liveMessage) }}</p>
      </div>

      <div class="loading-anim" :class="{ 'loading-anim--error': error }" aria-hidden="true">
        <!-- TODO: 散步循环动图，待用户提供 gif/lottie/webp 素材替换。 -->
        <img src="/studio-brand/puppy-icon-192-v6.png" alt="" />
      </div>

      <div class="progress-readout" :class="{ 'progress-readout--error': error }">{{ gt(error ? '!' : `${progress}%`) }}</div>
      <div class="progress-track" aria-hidden="true">
        <span :style="{ width: `${progress}%` }"></span>
      </div>

      <ol class="stage-list">
        <li
          v-for="(stage, index) in stages"
          :key="stage.title"
          :class="{
            'stage-list__item--active': index === activeStage && !error,
            'stage-list__item--done': index < activeStage && !error
          }"
        >
          <span>{{ gt(index + 1) }}</span>
          <div>
            <strong>{{ gt(stage.title) }}</strong>
            <em>{{ gt(stage.detail) }}</em>
          </div>
        </li>
      </ol>

      <p v-if="error" class="loading-error">{{ gt(error) }}</p>
      <div v-if="error" class="loading-actions">
        <button v-if="canRetry" class="pd-btn pd-btn--primary" type="button" @click="runGeneration">{{ gt("重新生成") }}</button>
        <RouterLink class="pd-btn loading-secondary" to="/tools">{{ gt("回到上传") }}</RouterLink>
      </div>
    </div>
  </section>

  <QuotaGuideModal
    :open="quotaGuideOpen"
    :kind="quotaKind"
    :message="quotaMessage"
    @close="quotaGuideOpen = false"
    @redeem="openQuotaRedeem"
    @register="openQuotaRegister"
    @recharge="openQuotaRecharge"
  />

  <PricingModal
    :open="pricingOpen"
    :initial-panel="pricingPanel"
    :focus-cdk="pricingFocusCdk"
    :reason="pricingReason"
    @close="closePricing"
    @success="handlePricingSuccess"
  />
</template>

<style scoped>
.loading-page {
  display: grid;
  place-items: center;
  min-height: calc(100vh - var(--app-header-height) - 140px);
}

.loading-panel {
  width: min(100%, 680px);
  border: 1px solid rgba(242, 247, 250, 0.84);
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--pd-shadow-float);
  padding: clamp(28px, 6vw, 50px);
  text-align: center;
}

.loading-copy h1 {
  margin: 0;
  color: var(--pd-orange);
  font-family: var(--pd-font-body);
  font-size: clamp(30px, 5vw, 46px);
  font-weight: 600;
  line-height: 1.08;
  letter-spacing: 0;
}

.loading-sub {
  margin: 12px auto 10px;
  max-width: 480px;
  color: var(--pd-fg-2);
  font-weight: 500;
  word-break: break-word;
}

.loading-live {
  width: fit-content;
  max-width: min(100%, 480px);
  margin: 0 auto 24px;
  border: 1px solid rgba(134, 162, 184, 0.18);
  border-radius: 999px;
  background: rgba(235, 243, 249, 0.72);
  color: var(--pd-orange);
  font-size: 13px;
  font-weight: 600;
  padding: 8px 14px;
}

.loading-anim {
  width: min(44vw, 190px);
  height: min(44vw, 190px);
  display: grid;
  place-items: center;
  margin: 2px auto 18px;
  border: 1px solid rgba(134, 162, 184, 0.18);
  border-radius: 34px;
  background:
    radial-gradient(circle at 48% 38%, rgba(235, 243, 249, 0.2), transparent 42%),
    rgba(255, 255, 255, 0.82);
  box-shadow:
    inset 0 0 0 8px rgba(134, 162, 184, 0.64),
    0 20px 46px rgba(134, 162, 184, 0.12);
}

.loading-anim img {
  width: 76%;
  max-width: 138px;
  height: auto;
  filter: drop-shadow(0 12px 18px rgba(45, 45, 45, 0.1));
  animation: loading-logo-breathe 2.2s var(--pd-ease-out) infinite;
}

.loading-anim--error {
  background: rgba(255, 90, 90, 0.08);
  box-shadow: 0 14px 30px rgba(255, 90, 90, 0.1);
}

.progress-readout {
  width: fit-content;
  min-width: 76px;
  min-height: 34px;
  display: grid;
  place-items: center;
  margin: 0 auto 10px;
  border: 1px solid rgba(134, 162, 184, 0.22);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  color: var(--pd-fg-1);
  font-size: 17px;
  font-weight: 600;
  padding: 0 16px;
  box-shadow: 0 12px 26px rgba(134, 162, 184, 0.08);
}

.progress-readout--error {
  color: var(--pd-danger);
}

.progress-track {
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--pd-divider);
}

.progress-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--pd-gradient);
  transition: width 260ms var(--pd-ease-out);
}

.stage-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 24px 0 0;
  padding: 0;
  list-style: none;
  text-align: left;
}

.stage-list li {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
  align-items: center;
  min-height: 78px;
  border: 1px solid var(--pd-stroke);
  border-radius: 18px;
  background: var(--pd-peach-50);
  padding: 14px;
}

.stage-list li > span {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: rgba(235, 243, 249, 0.16);
  color: var(--pd-orange);
  font-weight: 600;
}

.stage-list strong,
.stage-list em {
  display: block;
}

.stage-list strong {
  color: var(--pd-fg-1);
  font-size: 14px;
}

.stage-list em {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-style: normal;
  font-weight: 500;
  line-height: 1.45;
}

.stage-list__item--active {
  border-color: rgba(134, 162, 184, 0.48);
  background: #fff;
  box-shadow: 0 12px 26px rgba(134, 162, 184, 0.12);
}

.stage-list__item--active > span,
.stage-list__item--done > span {
  background: var(--pd-gradient-warm);
  color: var(--pd-fg-1);
}

.loading-error {
  margin: 18px 0 0;
  border-radius: 16px;
  background: rgba(255, 90, 90, 0.12);
  color: #cc3d3d;
  font-size: 13px;
  font-weight: 500;
  padding: 12px 14px;
}

.loading-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 16px;
}

.loading-auth-backdrop {
  position: fixed;
  inset: 0;
  z-index: 88;
  display: grid;
  place-items: center;
  background: rgba(45, 36, 30, 0.34);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  padding: 16px;
}

.loading-auth-modal {
  position: relative;
  width: min(100%, 520px);
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  padding: 0;
}

.loading-auth-modal__close {
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
  background: rgba(255, 255, 255, 0.86);
  color: var(--pd-fg-2);
  cursor: pointer;
  font: inherit;
  font-size: 21px;
  font-weight: 600;
  line-height: 1;
}

.loading-auth-modal__close:hover {
  color: var(--pd-orange);
  box-shadow: 0 12px 24px rgba(134, 162, 184, 0.16);
}

.loading-secondary {
  border: 1px solid rgba(134, 162, 184, 0.28);
  background: var(--pd-peach-50);
  color: var(--pd-orange);
}

@keyframes loading-logo-breathe {
  0%,
  100% {
    opacity: 0.9;
    transform: translateY(2px) scale(0.985);
  }

  50% {
    opacity: 1;
    transform: translateY(-4px) scale(1.015);
  }
}

@media (max-width: 640px) {
  .loading-page {
    min-height: auto;
  }

  .loading-panel {
    border-radius: 22px;
    padding: 28px 18px;
  }

  .stage-list,
  .loading-actions {
    grid-template-columns: 1fr;
  }
}
</style>
