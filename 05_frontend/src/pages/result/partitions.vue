<template>
  <MiniProgramLayout title="分区图" backUrl="/pages/result/basic" :scroll="true">
    <section class="partitions">
      <div class="partitions__overview">
        <image
          v-if="patternImageUrl"
          class="partitions__overview-image"
          :src="patternImageUrl"
          mode="aspectFit"
          @click="previewFullPattern"
        />
        <div v-else class="partitions__overview-placeholder">
          <span></span>
        </div>

        <div class="partitions__overview-info">
          <span class="partitions__overview-title">全图位置</span>
          <span class="partitions__overview-sub">{{ sheetSizeLabel }} · {{ totalLabel }}</span>
          <div class="partitions__map" aria-label="四区位置">
            <button
              v-for="cell in overviewCells"
              :key="cell.index"
              type="button"
              class="partitions__map-cell"
              :class="{ 'partitions__map-cell--active': cell.index === activeIndex }"
              @click="previewPartition(cell.index)"
            >
              {{ cell.shortLabel }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="isLoading" class="partitions__loading">
        <span class="partitions__loading-dot"></span>
        <span>正在生成分区图...</span>
      </div>

      <div v-else-if="errorMsg" class="partitions__error">
        <h2>分区图暂时打不开</h2>
        <p>{{ errorMsg }}</p>
        <button type="button" class="btn btn--primary btn--md" @click="loadPartitions">重试</button>
      </div>

      <div v-else class="partitions__grid">
        <button
          v-for="item in quadrantItems"
          :key="item.index"
          type="button"
          class="partitions__card"
          :class="{ 'partitions__card--active': item.index - 1 === activeIndex }"
          @click="previewPartition(item.index - 1)"
        >
          <span class="partitions__card-title">{{ item.title }}</span>
          <image
            v-if="!item.imageFailed"
            class="partitions__thumb"
            :src="item.imageUrl"
            mode="aspectFit"
            @load="handlePartitionImageLoad(item.imageUrl)"
            @error="handlePartitionImageError(item.imageUrl, $event)"
          />
          <div
            v-else-if="item.cells.length"
            class="partitions__thumb-grid"
            :style="item.gridStyle"
          >
            <span
              v-for="cell in item.cells"
              :key="cell.key"
              class="partitions__thumb-cell"
              :style="{ backgroundColor: cell.hex }"
            ></span>
          </div>
          <div v-else class="partitions__thumb-placeholder">
            <span>预览加载失败</span>
          </div>
          <span class="partitions__card-meta">{{ item.cols }}×{{ item.rows }} · 轻点放大</span>
        </button>
      </div>
    </section>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';
import { api, PartitionItem, PatternSheet } from '../../api';
import { BASE_URL } from '../../utils/request';

const CURRENT_PATTERN_KEY = 'pd_current_pattern';
const API_ORIGIN = BASE_URL.replace(/\/api\/v\d+$/, '');
const QUADRANT_TITLES = ['左上区', '右上区', '左下区', '右下区'];
const QUADRANT_SHORT_TITLES = ['左上', '右上', '左下', '右下'];

const artworkId = ref('');
const isLoading = ref(false);
const errorMsg = ref('');
const activeIndex = ref(0);
const partitions = ref<PartitionItem[]>([]);
const failedImageUrls = ref<string[]>([]);
const rows = ref(0);
const cols = ref(0);
const storedPattern = ref<PatternSheet | null>(null);

type FallbackCell = {
  key: string;
  hex: string;
};

onLoad((options: any) => {
  artworkId.value = String(options?.artwork_id || '');
  storedPattern.value = readStoredPattern();
  rows.value = storedPattern.value?.grid.length || 0;
  cols.value = storedPattern.value?.grid[0]?.length || 0;
  loadPartitions();
});

const readStoredPattern = (): PatternSheet | null => {
  const stored = uni.getStorageSync(CURRENT_PATTERN_KEY);
  if (!stored) return null;
  return stored as PatternSheet;
};

const patternImageUrl = computed(() => {
  const url = storedPattern.value?.image_url || storedPattern.value?.metadata?.labeled_image_url || '';
  return normalizeAssetUrl(url);
});

const quadrantItems = computed(() => {
  return partitions.value.slice(0, 4).map((item, index) => ({
    ...item,
    title: item.label || QUADRANT_TITLES[index] || `第 ${index + 1} 区`,
    imageUrl: normalizeAssetUrl(item.url),
    imageFailed: failedImageUrls.value.includes(normalizeAssetUrl(item.url)),
    cells: partitionFallbackCells(item),
    gridStyle: {
      gridTemplateColumns: `repeat(${Math.max(item.cols, 1)}, 1fr)`
    }
  }));
});

const overviewCells = computed(() => {
  return Array.from({ length: 4 }, (_item, index) => ({
    index,
    shortLabel: QUADRANT_SHORT_TITLES[index]
  }));
});

const sheetSizeLabel = computed(() => `${cols.value || '-'} × ${rows.value || '-'}`);
const totalLabel = computed(() => quadrantItems.value.length ? `${quadrantItems.value.length} 区` : '待生成');

const normalizeAssetUrl = (url: string) => {
  if (!url) return '';
  if (/^https?:\/\//.test(url)) return url;
  if (url.startsWith('/static/') && !url.startsWith('/static/assets/')) return `${API_ORIGIN}${url}`;
  return url;
};

const loadPartitions = async () => {
  if (!artworkId.value) {
    errorMsg.value = '缺少作品编号，请重新生成图纸后再看分区。';
    return;
  }
  isLoading.value = true;
  errorMsg.value = '';
  try {
    const sheet = await api.getPatternPartitions(artworkId.value);
    partitions.value = sheet.items.slice(0, 4);
    failedImageUrls.value = [];
    rows.value = sheet.rows;
    cols.value = sheet.cols;
    activeIndex.value = 0;
  } catch (error: any) {
    console.error('加载分区图失败:', error);
    errorMsg.value = error?.message || '网络有点慢，请稍后再试。';
  } finally {
    isLoading.value = false;
  }
};

const previewFullPattern = () => {
  if (!patternImageUrl.value) return;
  uni.previewImage({ current: patternImageUrl.value, urls: [patternImageUrl.value] });
};

const previewPartition = (index: number) => {
  const urls = quadrantItems.value.map((item) => item.imageUrl).filter(Boolean);
  activeIndex.value = index;
  if (!urls.length || !urls[index] || failedImageUrls.value.includes(urls[index])) {
    uni.showToast({ title: '图片加载失败，已显示页面预览', icon: 'none' });
    return;
  }
  uni.previewImage({ current: urls[index], urls });
};

const handlePartitionImageLoad = (url: string) => {
  failedImageUrls.value = failedImageUrls.value.filter((item) => item !== url);
};

const handlePartitionImageError = (url: string, event: any) => {
  if (!failedImageUrls.value.includes(url)) {
    failedImageUrls.value = [...failedImageUrls.value, url];
  }
  console.warn('分区图图片加载失败，已切换为本地缩略预览:', url, event);
};

const partitionFallbackCells = (partition: PartitionItem): FallbackCell[] => {
  const grid = storedPattern.value?.grid || [];
  const cells: FallbackCell[] = [];
  for (let rowIndex = partition.row_start; rowIndex < partition.row_end; rowIndex += 1) {
    const row = grid[rowIndex] || [];
    for (let colIndex = partition.col_start; colIndex < partition.col_end; colIndex += 1) {
      const color = row[colIndex] || null;
      cells.push({
        key: `${rowIndex}-${colIndex}`,
        hex: color?.hex || 'transparent'
      });
    }
  }
  return cells;
};
</script>

<style lang="scss" scoped>
.partitions {
  padding: 14px 18px 28px;
}

.partitions__overview {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px;
  border-radius: var(--pd-r-card);
  background: var(--pd-card);
  box-shadow: var(--pd-shadow-card);
  margin-bottom: 14px;
}

.partitions__overview-image,
.partitions__overview-placeholder {
  width: 96px;
  height: 96px;
  border-radius: var(--pd-r-img);
  background: #fff;
  flex-shrink: 0;
}

.partitions__overview-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--pd-divider);
}

.partitions__overview-placeholder span {
  width: 24px;
  height: 24px;
  border-radius: 999px;
  background: var(--pd-gradient-warm);
  opacity: 0.72;
}

.partitions__overview-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.partitions__overview-title {
  font-size: 14px;
  font-weight: 800;
  color: var(--pd-fg-1);
}

.partitions__overview-sub {
  font-size: 12px;
  color: var(--pd-fg-2);
}

.partitions__map {
  width: 118px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 4px;
}

.partitions__map-cell {
  min-height: 28px;
  border: 1px solid var(--pd-divider);
  border-radius: 6px;
  background: var(--pd-bg-warm);
  color: var(--pd-fg-2);
  font-size: 11px;
  font-weight: 800;
  padding: 0;
}

.partitions__map-cell::after,
.partitions__card::after {
  border: 0;
}

.partitions__map-cell--active {
  border-color: var(--pd-pink);
  background: var(--pd-pink-100);
  color: var(--pd-pink-deep);
}

.partitions__loading,
.partitions__error {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 12px;
}

.partitions__loading {
  color: var(--pd-fg-2);
  font-size: 13px;
}

.partitions__loading-dot {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: var(--pd-gradient-warm);
  animation: partitions-pulse 900ms var(--pd-ease-soft) infinite alternate;
}

.partitions__error h2 {
  margin: 0;
  font-size: 18px;
  color: var(--pd-fg-1);
}

.partitions__error p {
  margin: 0;
  font-size: 13px;
  color: var(--pd-fg-2);
}

.partitions__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.partitions__card {
  min-width: 0;
  border: 1px solid var(--pd-divider);
  border-radius: var(--pd-r-card);
  background: var(--pd-card);
  box-shadow: var(--pd-shadow-card);
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--pd-fg-1);
  text-align: left;
}

.partitions__card--active {
  border-color: var(--pd-pink);
  box-shadow: 0 8px 18px rgba(255, 107, 157, 0.16);
}

.partitions__card-title {
  font-size: 14px;
  font-weight: 800;
  color: var(--pd-fg-1);
}

.partitions__thumb,
.partitions__thumb-grid,
.partitions__thumb-placeholder {
  width: 100%;
  height: 160px;
  border-radius: var(--pd-r-img);
  background: #fff;
}

.partitions__thumb {
  display: block;
}

.partitions__thumb-grid {
  display: grid;
  gap: 1px;
  padding: 6px;
  border: 1px solid var(--pd-divider);
  overflow: hidden;
}

.partitions__thumb-cell {
  min-width: 0;
  min-height: 0;
  border-radius: 1px;
  box-shadow: inset 0 0 0 0.5px rgba(45, 45, 45, 0.12);
}

.partitions__thumb-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--pd-divider);
  color: var(--pd-fg-2);
  font-size: 12px;
}

.partitions__card-meta {
  font-size: 11px;
  color: var(--pd-fg-2);
  line-height: 1.4;
}

@keyframes partitions-pulse {
  from { transform: scale(0.88); opacity: 0.62; }
  to { transform: scale(1); opacity: 1; }
}
</style>
