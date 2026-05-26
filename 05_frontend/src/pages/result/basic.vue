<template>
  <MiniProgramLayout title="你的拼豆图纸" backUrl="/pages/index/index" :scroll="true">
    <section class="result">

      <!-- ===== Pattern preview ===== -->
      <figure class="result__pattern">
        <div class="result__pattern-img-wrap" @click="previewFullScreen">
          <image
            v-if="patternImageUrl"
            class="result__pattern-image"
            :src="patternImageUrl"
            mode="widthFix"
          />
          <div
            v-else-if="hasPatternGrid"
            class="result__grid-preview"
            :style="gridPreviewStyle"
            aria-label="拼豆图纸预览"
          >
            <span
              v-for="cell in patternCells"
              :key="cell.key"
              class="result__grid-cell"
              :class="{ 'result__grid-cell--empty': !cell.color }"
              :style="{ backgroundColor: cell.color?.hex || 'transparent', color: cell.textColor }"
              aria-hidden="true"
            >{{ cell.showCode ? cell.color?.code : '' }}</span>
          </div>
          <div v-else class="result__empty-preview">
            <span class="result__empty-dot"></span>
            <span>暂无图纸预览</span>
          </div>
          <button
            v-if="patternImageUrl"
            type="button"
            class="result__zoom"
            @click.stop="previewFullScreen"
          >
            <span class="result__zoom-icon" aria-hidden="true"></span>
            点击放大
          </button>
          
          <!-- ===== AIGC 标识 (PRD §8.1 - FinishedPreview 可见) ===== -->
          <span v-if="tier === 'premium' && !isFallback" class="tag tag--ai result__pattern-badge">
            <span class="result__badge-star" aria-hidden="true">*</span>
            AI 智能生成
          </span>
        </div>
        
        <figcaption class="result__pattern-caption">
          <span class="result__pattern-name">{{ patternName }}</span>
          <span class="result__pattern-meta">{{ patternSizeLabel }} 网格</span>
        </figcaption>
      </figure>

      <!-- ===== Summary stats ===== -->
      <div class="card result__summary">
        <div class="result__summary-row">
          <div class="result__summary-cell">
            <span class="result__summary-num">{{ pattern.bead_total || 0 }}</span>
            <span class="result__summary-unit">总颗数</span>
          </div>
          <span class="result__summary-divider" aria-hidden="true"></span>
          <div class="result__summary-cell">
            <span class="result__summary-num">{{ colorsCount }}</span>
            <span class="result__summary-unit">色号数</span>
          </div>
          <span class="result__summary-divider" aria-hidden="true"></span>
          <div class="result__summary-cell">
            <span class="result__summary-num result__summary-num--cost">¥{{ estimatedCostLabel }}</span>
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
              {{ color.legend }}
            </span>
            <span class="result__color-bar">
              <!-- 延迟展开过渡动画 -->
              <span 
                class="result__color-bar-fill" 
                :style="{ width: isMounted ? color.percentage + '%' : '0%' }"
              ></span>
            </span>
          </li>
        </ul>
      </div>

      <!-- ===== CTAs ===== -->
      <div class="result__actions">
        <button class="btn btn--pink btn--block btn--lg result__download" @click="handleDownload">
          <span class="result__download-icon" aria-hidden="true"></span>
          保存图纸至相册
        </button>

        <button class="btn btn--primary btn--block btn--lg result__upsell" @click="showPaywall = true">
          <span class="result__upsell-text">解锁高级版（PDF / Excel）</span>
          <span class="result__upsell-badge">月卡</span>
        </button>

        <button class="btn btn--secondary btn--block btn--md result__partition" @click="openPartitions">
          分区查看
        </button>
      </div>

      <!-- ===== Regenerate footnote ===== -->
      <navigator class="result__regen" url="/pages/upload/upload" open-type="redirect">
        <span class="result__regen-icon" aria-hidden="true"></span>
        <span class="result__regen-label">再生成一次</span>
        <span class="result__regen-cost">消耗 1 次额度</span>
      </navigator>

    </section>

    <!-- ===== Paywall 遮罩 Modal 组件 ===== -->
    <Paywall 
      v-if="showPaywall" 
      :artworkId="artworkStore.currentArtwork?.artwork_id || ''"
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
import { PatternSheet, ColorRef } from '../../api';
import { BASE_URL } from '../../utils/request';

const artworkStore = useArtworkStore();
const CURRENT_PATTERN_KEY = 'pd_current_pattern';
const API_ORIGIN = BASE_URL.replace(/\/api\/v\d+$/, '');

const tier = ref<'quick' | 'premium'>('quick');
const isFallback = ref(false);
const isMounted = ref(false);
const showPaywall = ref(false);

type DisplayColor = {
  nameCn: string;
  code: string;
  count: number;
  percentage: number;
  hex: string;
  legend: string;
};

type DisplayCell = {
  key: string;
  color: ColorRef | null;
  showCode: boolean;
  textColor: string;
};

onLoad((options: any) => {
  if (options.tier) {
    tier.value = options.tier;
  }
  if (options.fallback === 'true') {
    isFallback.value = true;
  }
});

const readStoredPattern = (): PatternSheet | null => {
  const stored = uni.getStorageSync(CURRENT_PATTERN_KEY);
  if (!stored) return null;
  return stored as PatternSheet;
};

const emptyPattern: PatternSheet = {
  grid: [],
  color_counts: {},
  bead_total: 0,
  coords: [],
  no_bead_mask: [],
  palette_used: [],
  estimated_cost_cny: 0,
  suggested_buffer_pct: 10,
  brand: 'MARD',
  bead_diameter_mm: 5
};

// 从 Pinia 状态中获取当前图纸；热重载或跳转导致 Pinia 丢失时，读取最近一次真实 PatternSheet。
const pattern = computed(() => {
  return artworkStore.currentPattern || readStoredPattern() || emptyPattern;
});

const hasPatternGrid = computed(() => Array.isArray(pattern.value.grid) && pattern.value.grid.length > 0);
const gridRows = computed(() => pattern.value.grid.length);
const gridCols = computed(() => pattern.value.grid[0]?.length || 0);
const patternImageUrl = computed(() => {
  const url = (pattern.value as any).image_url || pattern.value.metadata?.labeled_image_url || '';
  return normalizeAssetUrl(url);
});
const artworkId = computed(() => {
  return String(pattern.value.metadata?.artwork_id || artworkStore.currentArtwork?.artwork_id || '');
});
const patternCells = computed<DisplayCell[]>(() => {
  const rows = pattern.value.grid || [];
  const maxDim = Math.max(gridCols.value, gridRows.value);
  const shouldShowAllCodes = maxDim <= 52;
  const cells: DisplayCell[] = [];
  rows.forEach((row, rowIndex) => {
    row.forEach((color, colIndex) => {
      const showCode = !!color && (shouldShowAllCodes || (rowIndex % 10 === 0 && colIndex % 10 === 0));
      cells.push({
        key: `${rowIndex}-${colIndex}`,
        color,
        showCode,
        textColor: color ? contrastText(color.rgb) : 'transparent'
      });
    });
  });
  return cells;
});

const resultCellSize = computed(() => {
  const maxDim = Math.max(gridCols.value, gridRows.value);
  if (maxDim <= 52) return 24;
  return 18;
});

const resultLabelSize = computed(() => {
  const maxDim = Math.max(gridCols.value, gridRows.value);
  if (maxDim <= 26) return 11;
  if (maxDim <= 52) return 8;
  return 7;
});
const gridPreviewStyle = computed(() => ({
  gridTemplateColumns: `repeat(${Math.max(gridCols.value, 1)}, ${resultCellSize.value}px)`,
  gridAutoRows: `${resultCellSize.value}px`,
  '--pd-result-cell-size': `${resultCellSize.value}px`,
  '--pd-result-label-size': `${resultLabelSize.value}px`
}));

const patternSizeLabel = computed(() => {
  if (!gridCols.value || !gridRows.value) return '0 × 0';
  return `${gridCols.value} × ${gridRows.value}`;
});

const patternColors = computed<DisplayColor[]>(() => {
  const counts = pattern.value.color_counts || {};
  const maxCount = Math.max(...Object.values(counts), 1);
  const paletteByCode = new Map(pattern.value.palette_used.map(color => [color.code, color]));

  return Object.entries(counts)
    .map(([code, count]) => {
      const color = paletteByCode.get(code);
      return {
        nameCn: color?.name_cn || '未命名色',
        code,
        count,
        percentage: Math.max(3, Math.round((count / maxCount) * 100)),
        hex: color?.hex || '#D9D9D9',
        legend: `${code} (${count} 颗 · ${color?.name_cn || '未命名色'})`
      };
    })
    .sort((a, b) => b.count - a.count);
});
const colorsCount = computed(() => patternColors.value.length);
const estimatedCostLabel = computed(() => Number(pattern.value.estimated_cost_cny || 0).toFixed(2));

const normalizeAssetUrl = (url: string) => {
  if (!url) return '';
  if (/^https?:\/\//.test(url)) return url;
  if (url.startsWith('/static/')) return `${API_ORIGIN}${url}`;
  return url;
};

const contrastText = (rgb: [number, number, number]) => {
  const luminance = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
  return luminance < 140 ? '#FFFFFF' : '#1F1F1F';
};

const patternName = computed(() => {
  if (tier.value === 'premium' && !isFallback.value) {
    return '萌宠拼豆 · AI 橘橘';
  }
  return '自拍拼豆 · 基础版';
});

const previewFullScreen = () => {
  if (!patternImageUrl.value) {
    uni.showToast({ title: '高清图生成后可放大查看', icon: 'none' });
    return;
  }
  uni.previewImage({
    current: patternImageUrl.value,
    urls: [patternImageUrl.value]
  });
};

const openPartitions = () => {
  if (!artworkId.value) {
    uni.showToast({ title: '重新生成后可查看分区图', icon: 'none' });
    return;
  }
  uni.navigateTo({
    url: `/pages/result/partitions?artwork_id=${encodeURIComponent(artworkId.value)}`
  });
};

// 一键保存拼豆图纸到系统相册
const handleDownload = () => {
  const imageUrl = patternImageUrl.value;
  if (!imageUrl) {
    uni.showToast({
      title: '图纸已生成，图片导出稍后开放',
      icon: 'none'
    });
    return;
  }
  uni.showLoading({ title: '正在保存图纸...' });
  
  // 小程序端长按保存或调用原生接口保存
  uni.downloadFile({
    url: imageUrl,
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
  max-width: 100%;
  position: relative;
  border-radius: var(--pd-r-img);
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
}

.result__pattern-image {
  width: 100%;
  max-width: 100%;
  display: block;
  border-radius: var(--pd-r-img);
  background: #fff;
}

.result__zoom {
  position: absolute;
  top: 10px;
  right: 10px;
  height: 30px;
  padding: 0 10px;
  border: 0;
  border-radius: 999px;
  background: rgba(255, 107, 157, 0.94);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  box-shadow: 0 4px 12px rgba(255, 107, 157, 0.32);
}

.result__zoom-icon {
  width: 12px;
  height: 12px;
  border: 2px solid currentColor;
  border-radius: 999px;
  position: relative;
}

.result__zoom-icon::after {
  content: "";
  position: absolute;
  right: -5px;
  bottom: -4px;
  width: 7px;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
  transform: rotate(45deg);
}

.result__grid-preview {
  width: max-content;
  max-width: none;
  display: grid;
  gap: 1px;
  padding: 6px;
  background: #fff;
  border: 1px solid var(--pd-divider);
  border-radius: var(--pd-r-img);
  overflow: hidden;
}

.result__grid-cell {
  width: var(--pd-result-cell-size);
  height: var(--pd-result-cell-size);
  border-radius: 2px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--pd-font-mono);
  font-size: var(--pd-result-label-size);
  font-weight: 800;
  line-height: 1;
  text-align: center;
  box-shadow: inset 0 0 0 0.7px rgba(45, 45, 45, 0.18);
  overflow: hidden;
}

.result__grid-cell--empty {
  background-image: radial-gradient(circle, rgba(150, 150, 150, 0.22) 0 18%, transparent 20%);
  box-shadow: none;
}

.result__empty-preview {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--pd-fg-2);
  background: #fff;
  border: 1px dashed var(--pd-divider);
  border-radius: var(--pd-r-img);
  font-size: 13px;
}

.result__empty-dot {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: var(--pd-gradient-warm);
  opacity: 0.72;
}

.result__pattern-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 2;
  box-shadow: 0 4px 10px rgba(255, 107, 157, 0.4);
}
.result__badge-star {
  margin-right: 2px;
  font-size: 11px;
  line-height: 1;
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
.result__download-icon {
  width: 14px;
  height: 14px;
  margin-right: 4px;
  border-bottom: 2px solid currentColor;
  position: relative;
}
.result__download-icon::before {
  content: "";
  position: absolute;
  left: 6px;
  top: 0;
  width: 2px;
  height: 10px;
  border-radius: 999px;
  background: currentColor;
}
.result__download-icon::after {
  content: "";
  position: absolute;
  left: 3px;
  top: 6px;
  width: 7px;
  height: 7px;
  border-left: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
  transform: rotate(-45deg);
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

.result__partition {
  cursor: pointer;
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
.result__regen-icon {
  width: 14px;
  height: 14px;
  margin-right: 4px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 999px;
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
