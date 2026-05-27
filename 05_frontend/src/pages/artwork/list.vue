<template>
  <MiniProgramLayout variant="home" title="我的作品" :scroll="true">
    <section class="works">
      <div v-if="isLoading && !artworks.length" class="works__loading">
        <span class="works__loading-dot"></span>
        <span>正在整理作品...</span>
      </div>

      <template v-else-if="artworks.length">
        <div class="works__stats">
          <div class="works__stat">
            <span class="works__stat-num">{{ totalCount }}</span>
            <span class="works__stat-label">总作品</span>
          </div>
          <span class="works__stat-divider" aria-hidden="true"></span>
          <div class="works__stat">
            <span class="works__stat-num">{{ monthCount }}</span>
            <span class="works__stat-label">本月新增</span>
          </div>
        </div>

        <div class="works__grid">
          <article
            v-for="artwork in artworks"
            :key="artwork.artwork_id"
            class="works__card"
            :class="{ 'works__card--paid': artwork.is_paid_unlocked }"
            @click="openArtwork(artwork)"
            @longpress.stop="showArtworkActions(artwork)"
          >
            <image
              class="works__thumb"
              :src="artworkThumb(artwork)"
              mode="aspectFit"
              @error="handleImageError(artwork.artwork_id)"
            />
            <h3 class="works__title">{{ artworkTitle(artwork) }}</h3>
            <p class="works__meta">{{ artworkMeta(artwork) }}</p>
            <span v-if="artwork.is_paid_unlocked" class="works__premium-tag works__premium-tag--paid">
              ✨ 月卡
            </span>
            <span v-else-if="isAiArtwork(artwork)" class="works__premium-tag tag tag--ai">
              AI
            </span>
            <button
              type="button"
              class="works__more"
              aria-label="更多操作"
              @click.stop="showArtworkActions(artwork)"
            >
              <span class="works__more-dot"></span>
              <span class="works__more-dot"></span>
              <span class="works__more-dot"></span>
            </button>
          </article>
        </div>

        <button type="button" class="works__more-cta" @click="goCreate">
          <span class="works__plus" aria-hidden="true"></span>
          再生成一张
        </button>
      </template>

      <section v-else class="works__empty">
        <div class="works__empty-art" aria-hidden="true">
          <span class="works__empty-card">
            <span class="works__empty-photo"></span>
            <span class="works__empty-check"></span>
          </span>
        </div>
        <h2 class="works__empty-title">还没作品哦</h2>
        <p class="works__empty-sub">上传一张照片，生成你的第一张拼豆图纸</p>
        <button type="button" class="btn btn--primary btn--lg works__empty-cta" @click="goCreate">
          立即生成 →
        </button>
      </section>

      <p v-if="loadError" class="works__error">{{ loadError }}</p>
    </section>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';
import { useArtworkStore } from '../../store/artwork';
import { Artwork } from '../../api';
import { BASE_URL } from '../../utils/request';

const artworkStore = useArtworkStore();
const isLoading = ref(false);
const loadError = ref('');
const brokenThumbIds = ref<string[]>([]);

const API_ORIGIN = BASE_URL.replace(/\/api\/v\d+$/, '');
const FALLBACK_THUMB = '/static/assets/bead-cat.svg';

const artworks = computed(() => artworkStore.artworks);
const totalCount = computed(() => artworks.value.length);
const monthCount = computed(() => {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  return artworks.value.filter((artwork) => {
    const created = new Date(artwork.created_at);
    return created.getFullYear() === year && created.getMonth() === month;
  }).length;
});

const normalizeAssetUrl = (url?: string | null) => {
  if (!url) return FALLBACK_THUMB;
  if (/^https?:\/\//.test(url)) return url;
  if (url.startsWith('/static/')) return `${API_ORIGIN}${url}`;
  return url;
};

const artworkThumb = (artwork: Artwork) => {
  if (brokenThumbIds.value.includes(artwork.artwork_id)) return FALLBACK_THUMB;
  return normalizeAssetUrl(artwork.thumbnail_url || artwork.preview_url || artwork.original_image_url);
};

const styleLabel = (style: Artwork['style_preset']) => {
  const labels: Record<Artwork['style_preset'], string> = {
    q_portrait: 'Q版人像',
    q_pet: '萌宠拼豆',
    q_couple: '情侣拼豆',
    cartoon_fallback: '基础图纸',
  };
  return labels[style] || '拼豆图纸';
};

const artworkTitle = (artwork: Artwork) => {
  return artwork.title || `${styleLabel(artwork.style_preset)} · ${artwork.size_preset}`;
};

const artworkMeta = (artwork: Artwork) => {
  const pattern = artwork.pattern_data;
  const beadTotal = pattern?.bead_total || 0;
  const colorsCount = Object.keys(pattern?.color_counts || {}).length;
  return `${beadTotal} 颗 · ${colorsCount} 色 · ${formatDate(artwork.created_at)}`;
};

const isAiArtwork = (artwork: Artwork) => artwork.style_preset !== 'cartoon_fallback';

const formatDate = (dateText: string) => {
  const date = new Date(dateText);
  if (Number.isNaN(date.getTime())) return '刚刚';
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${month}/${day}`;
};

const handleImageError = (id: string) => {
  if (!brokenThumbIds.value.includes(id)) {
    brokenThumbIds.value.push(id);
  }
};

const loadArtworks = async () => {
  isLoading.value = true;
  loadError.value = '';
  try {
    await artworkStore.fetchArtworks();
  } catch (error) {
    console.error('加载作品集失败:', error);
    loadError.value = '作品集暂时加载失败，稍后再看。';
  } finally {
    isLoading.value = false;
  }
};

const openArtwork = async (artwork: Artwork) => {
  uni.showLoading({ title: '打开图纸...' });
  try {
    await artworkStore.fetchArtworkDetail(artwork.artwork_id);
    uni.hideLoading();
    uni.navigateTo({
      url: `/pages/result/basic?tier=${isAiArtwork(artwork) ? 'premium' : 'quick'}`
    });
  } catch (error) {
    uni.hideLoading();
    console.error('打开作品失败:', error);
    uni.showToast({ title: '作品详情加载失败', icon: 'none' });
  }
};

const showArtworkActions = (artwork: Artwork) => {
  uni.showActionSheet({
    itemList: ['分享', '删除'],
    success: async (res) => {
      if (res.tapIndex === 0) {
        uni.showToast({ title: '分享卡片稍后开放', icon: 'none' });
      }
      if (res.tapIndex === 1) {
        confirmDelete(artwork);
      }
    }
  });
};

const confirmDelete = (artwork: Artwork) => {
  uni.showModal({
    title: '删除作品',
    content: '删除后会同步移除图纸记录，确定继续吗？',
    confirmText: '删除',
    confirmColor: '#FF5A5A',
    success: async (res) => {
      if (!res.confirm) return;
      uni.showLoading({ title: '删除中...' });
      try {
        await artworkStore.deleteArtwork(artwork.artwork_id);
        uni.hideLoading();
        uni.showToast({ title: '已删除', icon: 'success' });
      } catch (error) {
        uni.hideLoading();
        console.error('删除作品失败:', error);
        uni.showToast({ title: '删除失败，请稍后再试', icon: 'none' });
      }
    }
  });
};

const goCreate = () => {
  uni.switchTab({
    url: '/pages/index/index',
    fail: () => {
      uni.reLaunch({ url: '/pages/index/index' });
    }
  });
};

onShow(() => {
  loadArtworks();
});
</script>

<style lang="scss" scoped>
.works {
  padding: 16px 16px 28px;
}

.works__loading {
  min-height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--pd-fg-2);
  font-size: 13px;
}

.works__loading-dot {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: var(--pd-gradient-warm);
  animation: works-pulse 900ms var(--pd-ease-soft) infinite alternate;
}

.works__stats {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 16px 20px;
  background: var(--pd-card);
  border-radius: var(--pd-r-card);
  box-shadow: var(--pd-shadow-card);
  margin-bottom: 16px;
}

.works__stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.works__stat-num {
  font-family: var(--pd-font-display);
  font-size: 22px;
  font-weight: 800;
  color: var(--pd-fg-1);
}

.works__stat-label {
  font-size: 11px;
  color: var(--pd-fg-2);
}

.works__stat-divider {
  width: 1px;
  height: 32px;
  background: var(--pd-divider);
}

.works__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.works__card {
  position: relative;
  min-width: 0;
  background: var(--pd-card);
  border-radius: var(--pd-r-card);
  box-shadow: var(--pd-shadow-card);
  padding: 10px 10px 12px;
  overflow: hidden;
}

.works__card--paid {
  background: rgba(255, 192, 128, 0.05);
}

.works__card:active {
  transform: scale(0.98);
}

.works__thumb {
  width: 100%;
  height: 152px;
  border-radius: var(--pd-r-img);
  background: var(--pd-bg-warm);
  display: block;
  margin-bottom: 8px;
}

.works__title {
  margin: 0 0 2px;
  font-family: var(--pd-font-display);
  font-size: 13px;
  font-weight: 700;
  color: var(--pd-fg-1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.works__meta {
  margin: 0;
  font-size: 11px;
  color: var(--pd-fg-2);
}

.works__premium-tag {
  position: absolute;
  top: 14px;
  left: 14px;
}

.works__premium-tag--paid {
  right: 14px;
  left: auto;
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--pd-gradient-warm);
  color: #fff;
  box-shadow: 0 4px 10px rgba(255, 138, 128, 0.28);
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
}

.works__more {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  border: 0;
  color: var(--pd-fg-2);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 0;
}

.works__card--paid .works__more {
  top: 42px;
}

.works__more-dot {
  width: 3px;
  height: 3px;
  border-radius: 999px;
  background: currentColor;
}

.works__more-cta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin: 16px auto 0;
  padding: 12px 20px;
  border-radius: 999px;
  background: var(--pd-pink-50);
  color: var(--pd-pink-deep);
  border: 0;
  font-size: 13px;
  font-weight: 700;
}

.works__plus {
  width: 14px;
  height: 14px;
  position: relative;
}

.works__plus::before,
.works__plus::after {
  content: "";
  position: absolute;
  left: 6px;
  top: 1px;
  width: 2px;
  height: 12px;
  border-radius: 999px;
  background: currentColor;
}

.works__plus::after {
  transform: rotate(90deg);
}

.works__empty {
  min-height: 420px;
  padding: 48px 24px 24px;
  text-align: center;
}

.works__empty-art {
  width: 120px;
  height: 120px;
  margin: 0 auto 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.works__empty-card {
  width: 92px;
  height: 72px;
  border-radius: 14px;
  background: var(--pd-pink-100);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.works__empty-photo {
  width: 60px;
  height: 42px;
  border-radius: 10px;
  background: #fff;
  position: relative;
}

.works__empty-photo::after {
  content: "";
  position: absolute;
  left: 20px;
  top: 10px;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: var(--pd-peach-50);
}

.works__empty-check {
  position: absolute;
  right: 26px;
  top: 48px;
  width: 24px;
  height: 14px;
  border-left: 3px solid var(--pd-orange);
  border-bottom: 3px solid var(--pd-orange);
  transform: rotate(-45deg);
  border-radius: 2px;
}

.works__empty-title {
  margin: 0 0 8px;
  font-family: var(--pd-font-display);
  font-size: var(--pd-fs-h2);
  font-weight: 800;
  color: var(--pd-fg-1);
}

.works__empty-sub {
  margin: 0 0 28px;
  font-size: var(--pd-fs-sub);
  color: var(--pd-fg-2);
  line-height: 1.6;
}

.works__empty-cta {
  min-width: 200px;
}

.works__error {
  margin: 14px 0 0;
  text-align: center;
  font-size: 12px;
  color: var(--pd-danger);
}

@keyframes works-pulse {
  from { transform: scale(0.88); opacity: 0.62; }
  to { transform: scale(1); opacity: 1; }
}
</style>
