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
        <div class="partitions__overview-info">
          <span class="partitions__overview-title">全图位置</span>
          <span class="partitions__overview-sub">{{ sheetSizeLabel }} · {{ totalLabel }}</span>
          <div class="partitions__map" :style="overviewMapStyle">
            <span
              v-for="cell in overviewCells"
              :key="cell.index"
              class="partitions__map-cell"
              :class="{
                'partitions__map-cell--active': cell.index === currentIndex,
                'partitions__map-cell--done': doneIndexes.includes(cell.index)
              }"
            ></span>
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

      <template v-else>
        <swiper
          class="partitions__swiper"
          :current="currentIndex"
          @change="handleSwiperChange"
        >
          <swiper-item
            v-for="item in partitions"
            :key="item.index"
            class="partitions__slide"
          >
            <image
              class="partitions__image"
              :src="normalizeAssetUrl(item.url)"
              mode="widthFix"
              @click="previewPartition(item.index - 1)"
            />
          </swiper-item>
        </swiper>

        <div class="partitions__pager">
          <button type="button" class="partitions__nav" :disabled="currentIndex === 0" @click="goPrev">上一 区</button>
          <span class="partitions__counter">{{ currentIndex + 1 }} / {{ partitions.length }}</span>
          <button type="button" class="partitions__nav" :disabled="currentIndex >= partitions.length - 1" @click="goNext">下一 区</button>
        </div>

        <button
          type="button"
          class="partitions__done"
          :class="{ 'partitions__done--active': isCurrentDone }"
          @click="toggleCurrentDone"
        >
          {{ isCurrentDone ? '已拼完 · 点此取消' : '标记这一区已拼完' }}
        </button>
      </template>
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

const artworkId = ref('');
const isLoading = ref(false);
const errorMsg = ref('');
const currentIndex = ref(0);
const partitions = ref<PartitionItem[]>([]);
const partitionSize = ref(13);
const rows = ref(0);
const cols = ref(0);
const doneIndexes = ref<number[]>([]);

const storedPattern = ref<PatternSheet | null>(null);

onLoad((options: any) => {
  artworkId.value = String(options?.artwork_id || '');
  storedPattern.value = readStoredPattern();
  rows.value = storedPattern.value?.grid.length || 0;
  cols.value = storedPattern.value?.grid[0]?.length || 0;
  loadDoneState();
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

const overviewCols = computed(() => Math.max(1, Math.ceil(cols.value / partitionSize.value)));
const overviewRows = computed(() => Math.max(1, Math.ceil(rows.value / partitionSize.value)));
const overviewCells = computed(() => {
  return Array.from({ length: overviewCols.value * overviewRows.value }, (_item, index) => ({ index }));
});
const overviewMapStyle = computed(() => ({
  gridTemplateColumns: `repeat(${overviewCols.value}, 1fr)`
}));
const sheetSizeLabel = computed(() => `${cols.value || '-'} × ${rows.value || '-'}`);
const totalLabel = computed(() => partitions.value.length ? `${partitions.value.length} 区` : '待生成');
const isCurrentDone = computed(() => doneIndexes.value.includes(currentIndex.value));

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
    partitions.value = sheet.items;
    partitionSize.value = sheet.partition_size;
    rows.value = sheet.rows;
    cols.value = sheet.cols;
    currentIndex.value = Math.min(currentIndex.value, Math.max(0, sheet.items.length - 1));
  } catch (error: any) {
    console.error('加载分区图失败:', error);
    errorMsg.value = error?.message || '网络有点慢，请稍后再试。';
  } finally {
    isLoading.value = false;
  }
};

const handleSwiperChange = (event: any) => {
  currentIndex.value = Number(event.detail?.current || 0);
};

const goPrev = () => {
  currentIndex.value = Math.max(0, currentIndex.value - 1);
};

const goNext = () => {
  currentIndex.value = Math.min(partitions.value.length - 1, currentIndex.value + 1);
};

const loadDoneState = () => {
  if (!artworkId.value) return;
  const stored = uni.getStorageSync(doneStorageKey());
  doneIndexes.value = Array.isArray(stored) ? stored : [];
};

const persistDoneState = () => {
  if (!artworkId.value) return;
  uni.setStorageSync(doneStorageKey(), doneIndexes.value);
};

const doneStorageKey = () => `pd_partition_done_${artworkId.value}`;

const toggleCurrentDone = () => {
  if (isCurrentDone.value) {
    doneIndexes.value = doneIndexes.value.filter((index) => index !== currentIndex.value);
  } else {
    doneIndexes.value = [...doneIndexes.value, currentIndex.value].sort((a, b) => a - b);
  }
  persistDoneState();
};

const previewFullPattern = () => {
  if (!patternImageUrl.value) return;
  uni.previewImage({ current: patternImageUrl.value, urls: [patternImageUrl.value] });
};

const previewPartition = (index: number) => {
  const urls = partitions.value.map((item) => normalizeAssetUrl(item.url));
  if (!urls.length) return;
  uni.previewImage({ current: urls[index], urls });
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

.partitions__overview-image {
  width: 96px;
  height: 96px;
  border-radius: var(--pd-r-img);
  background: #fff;
  flex-shrink: 0;
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
  display: grid;
  gap: 4px;
  max-width: 150px;
}

.partitions__map-cell {
  min-height: 16px;
  border-radius: 4px;
  background: var(--pd-bg-warm);
  border: 1px solid var(--pd-divider);
}

.partitions__map-cell--active {
  border-color: var(--pd-pink);
  background: var(--pd-pink-100);
}

.partitions__map-cell--done {
  background: #DDF7E6;
  border-color: #72D99B;
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

.partitions__swiper {
  height: 560px;
  border-radius: var(--pd-r-card);
  background: var(--pd-card);
  box-shadow: var(--pd-shadow-card);
  overflow: hidden;
}

.partitions__slide {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow-y: auto;
}

.partitions__image {
  width: 100%;
  display: block;
  background: #fff;
}

.partitions__pager {
  margin: 14px 0 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.partitions__nav {
  flex: 1;
  height: 42px;
  border: 0;
  border-radius: 999px;
  background: var(--pd-pink-50);
  color: var(--pd-pink-deep);
  font-size: 13px;
  font-weight: 700;
}

.partitions__nav:disabled {
  opacity: 0.45;
}

.partitions__counter {
  min-width: 64px;
  text-align: center;
  font-family: var(--pd-font-display);
  font-size: 16px;
  font-weight: 800;
  color: var(--pd-fg-1);
}

.partitions__done {
  width: 100%;
  height: 48px;
  border: 0;
  border-radius: 999px;
  background: var(--pd-bg-warm);
  color: var(--pd-fg-1);
  font-size: 14px;
  font-weight: 800;
}

.partitions__done--active {
  background: #DDF7E6;
  color: #168C45;
}

@keyframes partitions-pulse {
  from { transform: scale(0.88); opacity: 0.62; }
  to { transform: scale(1); opacity: 1; }
}
</style>
