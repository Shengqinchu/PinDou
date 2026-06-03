<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import {
  GENERATION_MODE_DETAILS,
  SIZE_OPTION_DETAILS,
  STYLE_OPTION_DETAILS,
  isResultSizePreset,
  useGenerationStore
} from '../stores/generation';

interface StageItem {
  title: string;
  detail: string;
}

const router = useRouter();
const route = useRoute();
const generation = useGenerationStore();
const activeStage = ref(0);
const progress = ref(8);
const error = ref('');
let progressTimer: number | undefined;

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
const selectedSizeLabel = computed(() => SIZE_OPTION_DETAILS[generation.selectedSize].label);
const modeLabel = computed(() => GENERATION_MODE_DETAILS[generation.generationMode].label);
const styleLabel = computed(() => STYLE_OPTION_DETAILS[generation.selectedStyle].label);
const canRetry = computed(() => Boolean(generation.sourceFile));
const progressHeadline = computed(() => {
  if (error.value) {
    return '生成遇到问题';
  }
  return generation.generationMode === 'ai' ? 'Q 版豆图正在制作' : '图纸正在快速生成';
});
const progressSub = computed(() => {
  const fileName = generation.sourceFile?.name || 'PinDou 拼豆图纸';
  const style = generation.generationMode === 'ai' ? ` · ${styleLabel.value}` : '';
  return `${fileName} · ${modeLabel.value}${style} · ${selectedSizeLabel.value}格`;
});

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
  progress.value = generation.generationMode === 'ai' ? 6 : 12;
  activeStage.value = 0;
  startProgress();

  try {
    const result = await generation.generateCurrent();
    stopProgress();
    progress.value = 100;
    activeStage.value = stages.value.length - 1;
    window.setTimeout(() => {
      void router.replace({ name: 'result', params: { id: result.artwork_id } });
    }, 380);
  } catch (generateError) {
    stopProgress();
    error.value = generateError instanceof Error ? generateError.message : '图纸生成失败，请重新试一次。';
  }
}

function startProgress(): void {
  stopProgress();
  progressTimer = window.setInterval(() => {
    const step = generation.generationMode === 'ai' ? 3 : 6;
    const ceiling = generation.generationMode === 'ai' ? 92 : 88;
    progress.value = Math.min(progress.value + step, ceiling);
    activeStage.value = Math.min(
      Math.floor((progress.value / 100) * stages.value.length),
      stages.value.length - 1
    );
  }, generation.generationMode === 'ai' ? 680 : 480);
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
      <div class="loading-copy">
        <p class="eyebrow">Generating</p>
        <h1>{{ progressHeadline }}</h1>
        <p class="loading-sub">{{ progressSub }}</p>
      </div>

      <div
        class="bead-loader"
        :class="{ 'bead-loader--error': error }"
        :style="{ '--progress': progress }"
        aria-hidden="true"
      >
        <span v-for="index in 16" :key="index"></span>
        <strong>{{ error ? '!' : `${progress}%` }}</strong>
      </div>

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
  width: min(100%, 680px);
  border: 1px solid rgba(237, 228, 218, 0.84);
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--pd-shadow-float);
  padding: clamp(28px, 6vw, 50px);
  text-align: center;
}

.loading-copy h1 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(30px, 5vw, 46px);
  font-weight: 900;
  line-height: 1.08;
  letter-spacing: 0;
}

.eyebrow {
  margin: 0 0 10px;
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
  text-transform: uppercase;
}

.loading-sub {
  margin: 12px auto 26px;
  max-width: 480px;
  color: var(--pd-fg-2);
  font-weight: 800;
  word-break: break-word;
}

.bead-loader {
  --loader-size: 154px;
  position: relative;
  width: var(--loader-size);
  height: var(--loader-size);
  display: grid;
  place-items: center;
  margin: 0 auto 22px;
  border-radius: 999px;
  background:
    radial-gradient(circle at 50% 50%, #fff 0 45%, transparent 46%),
    conic-gradient(var(--pd-orange) calc(var(--progress, 0) * 1%), rgba(237, 228, 218, 0.9) 0);
  box-shadow: inset 0 0 0 12px #fff, var(--pd-shadow-cta);
  animation: breathe 1.5s var(--pd-ease-out) infinite alternate;
}

.bead-loader span {
  position: absolute;
  left: calc(50% - 8px);
  top: calc(50% - 8px);
  width: 16px;
  height: 16px;
  border-radius: 999px;
  background: var(--pd-peach);
  box-shadow: inset 0 0 0 4px rgba(255, 255, 255, 0.55);
  transform:
    rotate(calc((var(--i, 1) - 1) * 22.5deg))
    translateY(-66px);
}

.bead-loader span:nth-child(1) { --i: 1; background: #ffb088; }
.bead-loader span:nth-child(2) { --i: 2; background: #ff8e53; }
.bead-loader span:nth-child(3) { --i: 3; background: #ff6b9d; }
.bead-loader span:nth-child(4) { --i: 4; background: #b8a4ed; }
.bead-loader span:nth-child(5) { --i: 5; background: #a4d4c5; }
.bead-loader span:nth-child(6) { --i: 6; background: #e8b94a; }
.bead-loader span:nth-child(7) { --i: 7; background: #ffb088; }
.bead-loader span:nth-child(8) { --i: 8; background: #ff8e53; }
.bead-loader span:nth-child(9) { --i: 9; background: #ff6b9d; }
.bead-loader span:nth-child(10) { --i: 10; background: #b8a4ed; }
.bead-loader span:nth-child(11) { --i: 11; background: #a4d4c5; }
.bead-loader span:nth-child(12) { --i: 12; background: #e8b94a; }
.bead-loader span:nth-child(13) { --i: 13; background: #ffb088; }
.bead-loader span:nth-child(14) { --i: 14; background: #ff8e53; }
.bead-loader span:nth-child(15) { --i: 15; background: #ff6b9d; }
.bead-loader span:nth-child(16) { --i: 16; background: #b8a4ed; }

.bead-loader strong {
  width: 92px;
  height: 92px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: #fff;
  color: var(--pd-fg-1);
  font-size: 24px;
  font-weight: 900;
}

.bead-loader--error {
  animation: none;
  background: rgba(255, 90, 90, 0.16);
  box-shadow: inset 0 0 0 12px #fff, 0 14px 30px rgba(255, 90, 90, 0.12);
}

.bead-loader--error strong {
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
  font-size: 14px;
}

.stage-list em {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
  line-height: 1.45;
}

.stage-list__item--active {
  border-color: rgba(255, 142, 83, 0.48);
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
    transform: scale(0.985) rotate(-1deg);
  }

  to {
    transform: scale(1.02) rotate(1deg);
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
