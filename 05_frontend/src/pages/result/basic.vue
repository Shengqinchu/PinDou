<template>
  <MiniProgramLayout title="你的拼豆图纸" backUrl="/pages/index/index" :scroll="true">
    <section class="result">

      <!-- ===== Pattern preview ===== -->
      <figure class="result__pattern">
        <div class="result__pattern-img-wrap">
          <image class="result__pattern-image" :src="patternImage" mode="widthFix" />
          
          <!-- ===== AIGC 标识 (PRD §8.1 - FinishedPreview 可见) ===== -->
          <span v-if="tier === 'premium' && !isFallback" class="tag tag--ai result__pattern-badge">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="margin-right: 2px;">
              <path d="M9.94 14.06 2 12l7.94-2.06L12 2l2.06 7.94L22 12l-7.94 2.06L12 22z"/>
            </svg>
            AI 智能生成
          </span>
        </div>
        
        <figcaption class="result__pattern-caption">
          <span class="result__pattern-name">{{ patternName }}</span>
          <span class="result__pattern-meta">{{ pattern.size || '24 × 24' }} 网格</span>
        </figcaption>
      </figure>

      <!-- ===== Summary stats ===== -->
      <div class="card result__summary">
        <div class="result__summary-row">
          <div class="result__summary-cell">
            <span class="result__summary-num">{{ pattern.total_beads || 0 }}</span>
            <span class="result__summary-unit">总颗数</span>
          </div>
          <span class="result__summary-divider" aria-hidden="true"></span>
          <div class="result__summary-cell">
            <span class="result__summary-num">{{ colorsCount }}</span>
            <span class="result__summary-unit">色号数</span>
          </div>
          <span class="result__summary-divider" aria-hidden="true"></span>
          <div class="result__summary-cell">
            <span class="result__summary-num result__summary-num--cost">¥{{ pattern.estimated_cost || '0.00' }}</span>
            <span class="result__summary-unit">估算成本</span>
          </div>
        </div>
      </div>

      <!-- ===== Color list ===== -->
      <div class="card result__colors-card">
        <h2 class="result__section-title">
          色号清单
          <span class="result__section-sub">按数量排序</span>
        </h2>
        <ul class="result__colors" role="list">
          <li
            v-for="(color, index) in patternColors"
            :key="index"
            class="result__color"
            :class="{ 'result__color--last': index === patternColors.length - 1 }"
          >
            <!-- 动态绑定背景色 -->
            <span class="result__swatch" :style="{ backgroundColor: color.hex }" aria-hidden="true"></span>
            <span class="result__color-name">
              {{ color.name }} 
              <span class="result__color-code">{{ color.code }}</span>
            </span>
            <span class="result__color-bar">
              <!-- 延迟展开过渡动画 -->
              <span 
                class="result__color-bar-fill" 
                :style="{ width: isMounted ? color.percentage + '%' : '0%' }"
              ></span>
            </span>
            <span class="result__color-count">{{ color.count }}</span>
          </li>
        </ul>
      </div>

      <!-- ===== CTAs ===== -->
      <div class="result__actions">
        <button class="btn btn--pink btn--block btn--lg result__download" @click="handleDownload">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="margin-right: 4px; display: block;">
            <path d="M12 3v12"/>
            <path d="m7 10 5 5 5-5"/>
            <path d="M5 21h14"/>
          </svg>
          保存图纸至相册
        </button>

        <button class="btn btn--primary btn--block btn--lg result__upsell" @click="showPaywall = true">
          <span class="result__upsell-text">解锁高级版（PDF / Excel）</span>
          <span class="result__upsell-badge">月卡</span>
        </button>
      </div>

      <!-- ===== Regenerate footnote ===== -->
      <navigator class="result__regen" url="/pages/upload/upload" open-type="redirect">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="margin-right: 4px; display: block;">
          <path d="M3 12a9 9 0 0 1 15.5-6.3L21 8"/>
          <path d="M21 3v5h-5"/>
          <path d="M21 12a9 9 0 0 1-15.5 6.3L3 16"/>
          <path d="M3 21v-5h5"/>
        </svg>
        <span class="result__regen-label">再生成一次</span>
        <span class="result__regen-cost">消耗 1 次额度</span>
      </navigator>

    </section>

    <!-- ===== Paywall 遮罩 Modal 组件 ===== -->
    <Paywall 
      v-if="showPaywall" 
      :artworkId="pattern.pattern_id"
      @close="showPaywall = false" 
    />
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';
import Paywall from '../../components/Paywall.vue';
import { useArtworkStore } from '../../store/artwork';

const artworkStore = useArtworkStore();

const tier = ref<'quick' | 'premium'>('quick');
const isFallback = ref(false);
const isMounted = ref(false);
const showPaywall = ref(false);

onLoad((options: any) => {
  if (options.tier) {
    tier.value = options.tier;
  }
  if (options.fallback === 'true') {
    isFallback.value = true;
  }
});

// 从 Pinia 状态中获取当前的图纸，如果为空则使用 Mock 降级兜底展示
const pattern = computed(() => {
  return artworkStore.currentPattern || {
    pattern_id: 'pattern_mock_fallback',
    image_url: '/static/assets/bead-cat.svg',
    size: '24 × 24',
    total_beads: 487,
    colors_count: 7,
    estimated_cost: 6.5,
    colors: [
      { name: '蜜桃橙', code: 'O-22', count: 187, percentage: 38, hex: '#FFB088' },
      { name: '浅蜜桃', code: 'o-18', count: 156, percentage: 32, hex: '#FFCDA6' },
      { name: '奶油白', code: 'M-01', count: 65, percentage: 13, hex: '#FFF4E6' },
      { name: '樱花粉', code: 'p-08', count: 28, percentage: 6, hex: '#FFB6C1' },
      { name: '暖灰', code: 'k-50', count: 22, percentage: 5, hex: '#8C6A55' },
      { name: '墨色', code: 'K-99', count: 18, percentage: 4, hex: '#2D2D2D' },
      { name: '玫红', code: 'P-12', count: 11, percentage: 2, hex: '#FF6B9D' }
    ]
  };
});

const patternColors = computed(() => pattern.value.colors || []);
const colorsCount = computed(() => patternColors.value.length);

const patternImage = computed(() => {
  // 如果是 fallback 或 quick, 使用 bead-bunny; 如果是 premium 且成功, 使用 bead-cat
  if (isFallback.value || tier.value === 'quick') {
    return '/static/assets/bead-bunny.svg';
  }
  return pattern.value.image_url || '/static/assets/bead-cat.svg';
});

const patternName = computed(() => {
  if (tier.value === 'premium' && !isFallback.value) {
    return '萌宠拼豆 · AI 橘橘';
  }
  return '自拍拼豆 · 基础版';
});

// 一键保存拼豆图纸到系统相册
const handleDownload = () => {
  uni.showLoading({ title: '正在保存图纸...' });
  
  // 小程序端长按保存或调用原生接口保存
  uni.downloadFile({
    url: patternImage.value,
    success: (res) => {
      uni.saveImageToPhotosAlbum({
        filePath: res.tempFilePath,
        success: () => {
          uni.hideLoading();
          uni.showToast({
            title: '保存成功，去相册看看吧',
            icon: 'success'
          });
        },
        fail: (err) => {
          uni.hideLoading();
          uni.showToast({
            title: '保存相册失败，请授予相册写入权限',
            icon: 'none'
          });
          console.warn('授权失败或保存取消:', err);
        }
      });
    },
    fail: () => {
      uni.hideLoading();
      uni.showToast({
        title: '下载图纸资源失败',
        icon: 'none'
      });
    }
  });
};

onMounted(() => {
  // 延迟赋予 Mounted 状态，促使色条百分比伸长动画顺利在页面触发
  setTimeout(() => {
    isMounted.value = true;
  }, 100);
});
</script>

<style scoped lang="scss">
.result {
  padding: 16px 20px 28px;
}

/* ===== Big pattern preview ===== */
.result__pattern {
  margin: 0 0 16px;
  border-radius: var(--pd-r-card);
  background:
    radial-gradient(120% 100% at 50% 0%, #FFE4EE 0%, #FFF1E8 60%, transparent 100%),
    #fff;
  padding: 16px;
  box-shadow: var(--pd-shadow-card);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.result__pattern-img-wrap {
  width: 100%;
  max-width: 280px;
  position: relative;
  border-radius: var(--pd-r-img);
  overflow: hidden;
}

.result__pattern-image {
  width: 100%;
  display: block;
}

.result__pattern-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 2;
  box-shadow: 0 4px 10px rgba(255, 107, 157, 0.4);
}

.result__pattern-caption {
  margin: 0;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.result__pattern-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--pd-fg-1);
}
.result__pattern-meta {
  font-size: 11px;
  color: var(--pd-fg-2);
}

/* ===== Summary stats card ===== */
.result__summary {
  padding: 14px 4px;
  margin-bottom: 14px;
}
.result__summary-row {
  display: flex;
  align-items: center;
}
.result__summary-cell {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.result__summary-num {
  font-family: var(--pd-font-display);
  font-size: 22px;
  font-weight: 800;
  color: var(--pd-fg-1);
  line-height: 1;
  letter-spacing: -0.02em;
}
.result__summary-num--cost { 
  color: var(--pd-pink-deep); 
}
.result__summary-unit {
  font-size: 11px;
  color: var(--pd-fg-2);
}
.result__summary-divider {
  width: 1px;
  height: 28px;
  background: var(--pd-divider);
}

/* ===== Color list card ===== */
.result__colors-card { 
  padding: 16px 14px 8px; 
  margin-bottom: 18px; 
}

.result__section-title {
  margin: 0 0 8px;
  padding: 0 4px;
  font-size: 14px;
  font-weight: 700;
  color: var(--pd-fg-1);
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.result__section-sub {
  font-size: 11px;
  font-weight: 400;
  color: var(--pd-fg-3);
}

.result__colors {
  list-style: none;
  margin: 0;
  padding: 0;
}
.result__color {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 4px;
  border-bottom: 1px solid var(--pd-divider);
}
.result__color--last {
  border-bottom: 0;
}

.result__swatch {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  flex-shrink: 0;
  box-shadow: inset 0 0 0 1px rgba(45, 45, 45, 0.06);
}

.result__color-name {
  font-size: 13px;
  color: var(--pd-fg-1);
  font-weight: 500;
  white-space: nowrap;
}
.result__color-code {
  font-family: var(--pd-font-mono);
  font-size: 11px;
  color: var(--pd-fg-2);
  font-weight: 400;
  margin-left: 2px;
}

.result__color-bar {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: var(--pd-bg-warm);
  overflow: hidden;
  position: relative;
}
.result__color-bar-fill {
  display: block;
  height: 100%;
  background: var(--pd-gradient-warm);
  border-radius: inherit;
  width: 0;
  transition: width 800ms var(--pd-ease-out);
}

.result__color-count {
  font-size: 13px;
  font-weight: 700;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  min-width: 32px;
  text-align: right;
}

/* ===== CTAs ===== */
.result__actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.result__download {
  cursor: pointer;
}

.result__upsell {
  position: relative;
  justify-content: space-between;
  padding-left: 22px;
  padding-right: 22px;
  cursor: pointer;
}
.result__upsell-text {
  flex: 1;
  text-align: left;
}
.result__upsell-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.22);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.6px;
  color: #fff;
  border: 0.5px solid rgba(255, 255, 255, 0.4);
}

/* ===== Regen text link ===== */
.result__regen {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0 auto;
  padding: 6px 12px;
  font-size: 13px;
  color: var(--pd-fg-2);
  text-decoration: none;
  width: 100%;
  justify-content: center;
  cursor: pointer;
}
.result__regen-cost {
  font-size: 11px;
  color: var(--pd-fg-3);
  margin-left: 4px;
}
.result__regen-label {
  border-bottom: 0.5px solid var(--pd-fg-3);
  padding-bottom: 1px;
}
</style>
