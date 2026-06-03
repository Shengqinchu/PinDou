<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { isResultSizePreset, useGenerationStore } from '../stores/generation';

const router = useRouter();
const route = useRoute();
const generation = useGenerationStore();
const activeStage = ref(0);
const progress = ref(8);
const error = ref('');
let progressTimer: number | undefined;

const stages = [
  { title: '整理照片', detail: '校正方向和尺寸' },
  { title: '匹配豆色', detail: '使用现有色卡量化' },
  { title: '生成图纸', detail: '保存预览和清单' }
];

const selectedSizeLabel = computed(() => generation.selectedSize.replace('x', ' × '));
const canRetry = computed(() => Boolean(generation.sourceFile));

onMounted(() => {
  const querySize = String(route.query.size || '');
  if (isResultSizePreset(querySize)) {
    generation.setSize(querySize);
  }
  void runGeneration();
});

onUnmounted(() => {
  stopProgress();
});

async function runGeneration(): Promise<void> {
  if (!generation.sourceFile) {
    error.value = '这次生成没有找到原图，请回到上传页重新选择。';
    progress.value = 0;
    return;
  }

  error.value = '';
  progress.value = 8;
  activeStage.value = 0;
  startProgress();

  try {
    const result = await generation.generateCurrent();
    progress.value = 100;
    activeStage.value = stages.length - 1;
    window.setTimeout(() => {
      void router.replace({ name: 'result', params: { id: result.artwork_id } });
    }, 320);
  } catch (generateError) {
    stopProgress();
    error.value = generateError instanceof Error ? generateError.message : '图纸生成失败，请重新试一次。';
  }
}

function startProgress(): void {
  stopProgress();
  progressTimer = window.setInterval(() => {
    progress.value = Math.min(progress.value + 5, 88);
    activeStage.value = Math.min(Math.floor(progress.value / 34), stages.length - 1);
  }, 520);
}

function stopProgress(): void {
  if (progressTimer !== undefined) {
    window.clearInterval(progressTimer);
    progressTimer = undefined;
  }
}
</script>

<template>
  <section class="loading-page">
    <div class="loading-panel">
      <p class="eyebrow">正在生成</p>
      <h1>{{ error ? '生成遇到问题' : '图纸正在准备中' }}</h1>
      <p class="loading-sub">
        {{ generation.sourceFile?.name || 'PinDou 拼豆图纸' }} · {{ selectedSizeLabel }}
      </p>

      <div
        class="progress-ring"
        :class="{ 'progress-ring--error': error }"
        :style="{ '--progress': progress }"
        aria-hidden="true"
      >
        <span>{{ error ? '!' : `${progress}%` }}</span>
      </div>

      <div class="progress-track" aria-hidden="true">
        <span :style="{ width: `${progress}%` }"></span>
      </div>

      <ol class="stage-list">
        <li
          v-for="(stage, index) in stages"
          :key="stage.title"
          :class="{ 'stage-list__item--active': index === activeStage && !error, 'stage-list__item--done': index < activeStage && !error }"
        >
          <span>{{ index + 1 }}</span>
          <div>
            <strong>{{ stage.title }}</strong>
            <em>{{ stage.detail }}</em>
          </div>
        </li>
      </ol>

      <p v-if="error" class="loading-error">{{ error }}</p>
      <div v-if="error" class="loading-actions">
        <button v-if="canRetry" class="pd-btn pd-btn--primary" type="button" @click="runGeneration">重新生成</button>
        <RouterLink class="pd-btn loading-secondary" to="/upload">回到上传</RouterLink>
      </div>
    </div>
  </section>
</template>

<style scoped>
.loading-page {
  display: grid;
  place-items: center;
  min-height: calc(100vh - var(--app-header-height) - 140px);
}

.loading-panel {
  width: min(100%, 620px);
  border: 1px solid rgba(237, 228, 218, 0.82);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--pd-shadow-float);
  padding: clamp(28px, 6vw, 48px);
  text-align: center;
}

.eyebrow {
  margin: 0 0 10px;
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
  text-transform: uppercase;
}

.loading-panel h1 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(30px, 5vw, 44px);
  line-height: 1.12;
  letter-spacing: 0;
}

.loading-sub {
  margin: 10px auto 24px;
  max-width: 420px;
  color: var(--pd-fg-2);
  word-break: break-word;
}

.progress-ring {
  width: 132px;
  height: 132px;
  display: grid;
  place-items: center;
  margin: 0 auto 22px;
  border-radius: var(--pd-r-full);
  background:
    conic-gradient(var(--pd-orange) calc(var(--progress, 0) * 1%), rgba(237, 228, 218, 0.9) 0),
    #fff;
  box-shadow: inset 0 0 0 12px #fff, var(--pd-shadow-cta);
  animation: breathe 1.4s var(--pd-ease-out) infinite alternate;
}

.progress-ring span {
  width: 92px;
  height: 92px;
  display: grid;
  place-items: center;
  border-radius: var(--pd-r-full);
  background: #fff;
  color: var(--pd-fg-1);
  font-size: 24px;
  font-weight: 900;
}

.progress-ring--error {
  animation: none;
  background: rgba(255, 90, 90, 0.16);
  box-shadow: inset 0 0 0 12px #fff, 0 14px 30px rgba(255, 90, 90, 0.12);
}

.progress-ring--error span {
  color: var(--pd-danger);
}

.progress-track {
  height: 10px;
  overflow: hidden;
  border-radius: var(--pd-r-full);
  background: var(--pd-divider);
}

.progress-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--pd-gradient);
  transition: width 240ms var(--pd-ease-out);
}

.stage-list {
  display: grid;
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
  border-radius: var(--pd-r-full);
  background: rgba(255, 142, 83, 0.16);
  color: var(--pd-orange);
  font-weight: 900;
}

.stage-list strong,
.stage-list em {
  display: block;
}

.stage-list strong {
  color: var(--pd-fg-1);
}

.stage-list em {
  color: var(--pd-fg-2);
  font-size: 13px;
  font-style: normal;
}

.stage-list__item--active {
  border-color: rgba(255, 142, 83, 0.44);
  background: #fff;
  box-shadow: 0 12px 26px rgba(255, 142, 83, 0.12);
}

.stage-list__item--active > span,
.stage-list__item--done > span {
  background: var(--pd-gradient-warm);
  color: #fff;
}

.loading-error {
  margin: 18px 0 0;
  border-radius: 16px;
  background: rgba(255, 90, 90, 0.12);
  color: #cc3d3d;
  font-size: 13px;
  font-weight: 800;
  padding: 12px 14px;
}

.loading-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 16px;
}

.loading-secondary {
  border: 1px solid rgba(255, 142, 83, 0.28);
  background: var(--pd-peach-50);
  color: var(--pd-orange);
}

@keyframes breathe {
  from {
    transform: scale(0.98);
  }

  to {
    transform: scale(1.02);
  }
}

@media (max-width: 640px) {
  .loading-page {
    min-height: auto;
  }

  .loading-panel {
    border-radius: 22px;
    padding: 28px 20px;
  }

  .loading-actions {
    grid-template-columns: 1fr;
  }
}
</style>
