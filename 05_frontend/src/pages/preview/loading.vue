<template>
  <MiniProgramLayout title="正在生成..." backUrl="/pages/generate/choice" :scroll="false">
    <section class="loading">
      <div class="loading__wash" aria-hidden="true"></div>

      <div class="loading__spacer-top"></div>

      <!-- ===== Progress ring + center label ===== -->
      <div class="loading__ring-wrap">
        <div class="loading__confetti" aria-hidden="true">
          <span class="loading__dot loading__dot--1"></span>
          <span class="loading__dot loading__dot--2"></span>
          <span class="loading__dot loading__dot--3"></span>
          <span class="loading__dot loading__dot--4"></span>
          <span class="loading__dot loading__dot--5"></span>
        </div>

        <div class="loading__ring" :style="ringStyle" aria-hidden="true">
          <div class="loading__ring-hole"></div>
        </div>

        <div class="loading__center">
          <div class="loading__percent text-grad">{{ displayPercent }}%</div>
          <div class="loading__eta">{{ etaText }}</div>
        </div>
      </div>

      <!-- ===== Status copy (rotates) ===== -->
      <div class="loading__status">
        <p class="loading__status-line" :class="{ 'loading__status-line--reassure': isOverTime }">
          {{ statusText }}
        </p>
      </div>
      <p class="loading__desc">生成期间可以离开页面，做好了我们会消息提醒你</p>

      <div class="loading__spacer-bottom"></div>

      <navigator class="loading__examples" url="/pages/index/index" open-type="reLaunch">
        去看示例作品
        <span class="loading__examples-arrow" aria-hidden="true">›</span>
      </navigator>
    </section>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';
import { useArtworkStore } from '../../store/artwork';
import { StylePreset, SizePreset } from '../../api';

const artworkStore = useArtworkStore();

const STATUS_LINES = [
  'AI 正在画你的拼豆…',
  '正在挑选最美色号…',
  '马上就好啦~'
];
const REASSURE = '还有 30 秒哦，你的作品 99% 完成';

const TOTAL = 30; // 模拟跑满 100% 预计时间 (秒)
const ROTATE_MS = 8000; // 文案轮播间隔

// 路由参数
const tier = ref<'quick' | 'premium'>('quick');
const stylePreset = ref<StylePreset>('cartoon_fallback');
const sizePreset = ref<SizePreset>('26x26');
const rawImage = ref('');

onLoad((options: any) => {
  if (options.tier) tier.value = options.tier;
  if (options.style) stylePreset.value = options.style as StylePreset;
  if (options.size) sizePreset.value = options.size as SizePreset;
  if (options.image) rawImage.value = decodeURIComponent(options.image);
});

const activeIndex = ref(0);
const startTime = ref(0);
const percent = ref(0);
const isOverTime = ref(false);
const isApiDone = ref(false);

let tickTimer: any = null;
let rotateTimer: any = null;

const displayPercent = computed(() => Math.floor(percent.value));

const ringStyle = computed(() => ({
  background: `conic-gradient(#FF8E53 0%, #FF6B9D ${displayPercent.value}%, #FFE4EE ${displayPercent.value}% 100%)`
}));

const statusText = computed(() => {
  if (isOverTime.value) return REASSURE;
  return STATUS_LINES[activeIndex.value];
});

const etaText = computed(() => {
  if (isOverTime.value) return '稍等一下下';
  const elapsed = (Date.now() - startTime.value) / 1000;
  const remaining = Math.max(1, Math.ceil(TOTAL - elapsed));
  return `约 ${remaining} 秒`;
});

// 状态文案循环
const startStatusRotation = () => {
  rotateTimer = setInterval(() => {
    if (isOverTime.value) return;
    activeIndex.value = (activeIndex.value + 1) % STATUS_LINES.length;
  }, ROTATE_MS);
};

// 进度环时钟
const startProgressTick = () => {
  startTime.value = Date.now();
  tickTimer = setInterval(() => {
    if (isApiDone.value) {
      // 接口完成了，快速充填到 100% 并清除
      if (percent.value < 100) {
        percent.value = Math.min(100, percent.value + 15);
      } else {
        clearInterval(tickTimer);
      }
      return;
    }
    
    const elapsed = (Date.now() - startTime.value) / 1000;
    if (elapsed > TOTAL) {
      isOverTime.value = true;
      percent.value = 99; // 停留安抚
    } else {
      percent.value = (elapsed / TOTAL) * 100;
    }
  }, 100);
};

// 发起核心接口业务请求并管理 Fallback 降级链
const handleGeneration = async () => {
  const selectedSize = sizePreset.value || '26x26'; // 默认单板尺寸，对齐国产 26 格拼豆板
  
  if (tier.value === 'quick') {
    // 快速生成：直接调 PatternBuilder 本地量化
    try {
      await artworkStore.buildPatternSheet({
        size: selectedSize,
        rawImageFilePath: rawImage.value,
        mode: 'script'
      });
      completeAndNavigate('quick');
    } catch (err) {
      console.error('快速路径生成失败:', err);
      // 快速路径本就是最底层，再失败跳转错误页
      redirectToError(err);
    }
  } else {
    // AI精品生成：先 AI 风格重塑，再本地图纸量化
    try {
      // 1. 调用 PreviewProvider
      const preview = await artworkStore.generateAIPreview(
        rawImage.value,
        stylePreset.value,
        selectedSize
      );
      
      // 2. 拿到 preview_id 后调用 PatternBuilder
      await artworkStore.buildPatternSheet({
        size: selectedSize,
        preview_id: preview.preview_id,
        mode: 'ai'
      });
      
      completeAndNavigate('premium');
    } catch (err) {
      // ===== ADR-005: 关键 Fallback Chain 优雅降级 =====
      console.warn('AI 路径超时或不可用，触发普通量化兜底降级...', err);
      
      try {
        // 静默重新调用 script 量化
        await artworkStore.buildPatternSheet({
          size: selectedSize,
          rawImageFilePath: rawImage.value,
          mode: 'script'
        });
        
        // 成功后导向基础结果页，带上 fallback 参数，不暴露英文细节
        completeAndNavigate('quick', true);
      } catch (fallbackErr) {
        console.error('兜底量化链亦失败:', fallbackErr);
        redirectToError(fallbackErr);
      }
    }
  }
};

const redirectToError = (err: unknown) => {
  const anyErr = err as any;
  const code = String(anyErr?.code || '');
  const message = String(anyErr?.message || '再试一次吧～');
  const isQuota = code === 'QUOTA_EXCEEDED' || message.includes('额度') || message.includes('次数已用完');
  const isConsent = code === 'CONSENT_REQUIRED' || message.includes('同意');
  const variant = isQuota ? 'quota' : 'network';
  const title = isQuota ? '今天的额度用完啦' : isConsent ? '需要先完成授权' : '生成失败';

  uni.redirectTo({
    url: `/pages/error/error?variant=${variant}&title=${encodeURIComponent(title)}&message=${encodeURIComponent(message)}`
  });
};

const completeAndNavigate = (finalTier: 'quick' | 'premium', isFallback = false) => {
  isApiDone.value = true;
  
  // 等待百分比飙升至 100%
  const checkEnd = setInterval(() => {
    if (percent.value >= 100) {
      clearInterval(checkEnd);
      uni.redirectTo({
        url: `/pages/result/basic?tier=${finalTier}${isFallback ? '&fallback=true' : ''}`
      });
    }
  }, 100);
};

onMounted(() => {
  startProgressTick();
  startStatusRotation();
  handleGeneration();
});

onUnmounted(() => {
  if (tickTimer) clearInterval(tickTimer);
  if (rotateTimer) clearInterval(rotateTimer);
});
</script>

<style scoped lang="scss">
.loading {
  width: 100%;
  height: 100%;
  padding: 0 24px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.loading__wash {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 280px;
  background: radial-gradient(120% 100% at 50% 0%,
              #FFF1E8 0%, rgba(255, 241, 232, 0) 75%);
  pointer-events: none;
}

.loading__spacer-top    { flex: 1; }
.loading__spacer-bottom { flex: 1; }

/* ===== Ring container ===== */
.loading__ring-wrap {
  width: 220px;
  height: 220px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading__confetti {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.loading__dot {
  position: absolute;
  border-radius: 999px;
  opacity: 0.75;
}
.loading__dot--1 { left: 14%; top: 18%; width: 6px; height: 6px; background: #FFB6C1; }
.loading__dot--2 { left: 86%; top: 10%; width: 4px; height: 4px; background: #FFB088; }
.loading__dot--3 { left: 92%; top: 92%; width: 5px; height: 5px; background: #FFE5A0; }
.loading__dot--4 { left:  8%; top: 86%; width: 4px; height: 4px; background: #B8E6C9; }
.loading__dot--5 { left: 48%; top:  4%; width: 3px; height: 3px; background: #FF6B9D; }

/* CSS ring: keep mp-weixin away from inline svg/path parsing */
.loading__ring {
  position: absolute;
  width: 200px;
  height: 200px;
  border-radius: 999px;
  box-shadow: 0 0 18px rgba(255, 107, 157, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading__ring-hole {
  width: 176px;
  height: 176px;
  border-radius: 999px;
  background: var(--pd-bg);
}

/* Centred percent + ETA */
.loading__center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.loading__percent {
  font-family: var(--pd-font-display);
  font-size: 44px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.02em;
}
.loading__eta {
  font-size: 12px;
  color: var(--pd-fg-2);
  margin-top: 6px;
}

/* ===== Status line (rotates) ===== */
.loading__status {
  margin-top: 28px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.loading__status-line {
  font-size: 15px;
  font-weight: 500;
  color: var(--pd-fg-1);
  margin: 0;
  animation: pd-fade-in 360ms var(--pd-ease-out);
}
.loading__status-line--reassure {
  color: var(--pd-pink-deep);
}

.loading__desc {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--pd-fg-2);
  text-align: center;
  line-height: 1.55;
  max-width: 260px;
}

/* ===== Examples link ===== */
.loading__examples {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  color: var(--pd-pink-deep);
  text-decoration: none;
  cursor: pointer;
  
  &:active { 
    opacity: 0.7; 
  }
}

.loading__examples-arrow {
  margin-left: 2px;
  font-size: 18px;
  font-weight: 800;
  line-height: 1;
}

@keyframes pd-fade-in {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}
</style>
