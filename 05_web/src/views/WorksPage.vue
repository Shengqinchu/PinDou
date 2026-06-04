<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';

import { getArtworkGallery } from '../api';
import type { ArtworkListItem } from '../api/types';
import { resultSizeLabel } from '../stores/generation';

const PAGE_SIZE = 12;

const router = useRouter();
const works = ref<ArtworkListItem[]>([]);
const page = ref(1);
const total = ref(0);
const hasMore = ref(false);
const loading = ref(true);
const loadingMore = ref(false);
const errorMessage = ref('');
const failedImages = ref(new Set<string>());

const totalLabel = computed(() => {
  if (loading.value) {
    return '正在整理作品';
  }
  if (total.value <= 0) {
    return '还没有作品';
  }
  return `共 ${total.value} 个作品`;
});

onMounted(() => {
  void loadWorks(1);
});

async function loadWorks(targetPage: number, append = false): Promise<void> {
  if (append) {
    loadingMore.value = true;
  } else {
    loading.value = true;
  }
  errorMessage.value = '';
  try {
    const response = await getArtworkGallery(targetPage, PAGE_SIZE);
    page.value = response.page;
    total.value = response.total;
    hasMore.value = response.has_more;
    works.value = append ? [...works.value, ...response.items] : response.items;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '作品集暂时加载失败，请稍后再试。';
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
}

function openWork(work: ArtworkListItem): void {
  void router.push({ name: 'result', params: { id: work.artwork_id } });
}

function loadMore(): void {
  if (!hasMore.value || loadingMore.value) {
    return;
  }
  void loadWorks(page.value + 1, true);
}

function markImageFailed(artworkId: string): void {
  failedImages.value = new Set([...failedImages.value, artworkId]);
}

function workTitle(work: ArtworkListItem, index: number): string {
  return work.title?.trim() || `拼豆作品 ${total.value - index || index + 1}`;
}

function imageSrc(work: ArtworkListItem): string {
  return work.thumbnail_url || work.preview_url || '';
}

function formatDate(value?: string): string {
  if (!value) {
    return '刚刚';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '时间未知';
  }
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}
</script>

<template>
  <section class="works-page">
    <header class="works-hero">
      <div class="works-hero__copy">
        <span>作品集</span>
        <h1>我的拼豆作品</h1>
        <p>{{ totalLabel }}</p>
      </div>
      <RouterLink class="works-hero__cta" to="/upload">去生成</RouterLink>
    </header>

    <section v-if="loading" class="works-grid" aria-label="作品加载中">
      <div v-for="item in 6" :key="item" class="work-card work-card--skeleton" aria-hidden="true">
        <span class="work-card__thumb"></span>
        <span class="work-card__line work-card__line--wide"></span>
        <span class="work-card__line"></span>
      </div>
    </section>

    <section v-else-if="errorMessage" class="works-empty" role="alert">
      <span class="works-empty__mark" aria-hidden="true">!</span>
      <h2>作品集没加载出来</h2>
      <p>{{ errorMessage }}</p>
      <button class="works-empty__button" type="button" @click="loadWorks(1)">重新加载</button>
    </section>

    <section v-else-if="!works.length" class="works-empty">
      <span class="works-empty__mark" aria-hidden="true">豆</span>
      <h2>还没有保存的作品</h2>
      <p>生成一张照片，作品会自动出现在这里，之后可以随时回来查看和继续编辑。</p>
      <RouterLink class="works-empty__button" to="/upload">去生成</RouterLink>
    </section>

    <template v-else>
      <section class="works-grid" aria-label="我的作品">
        <button
          v-for="(work, index) in works"
          :key="work.artwork_id"
          class="work-card"
          type="button"
          @click="openWork(work)"
        >
          <span class="work-card__thumb">
            <img
              v-if="imageSrc(work) && !failedImages.has(work.artwork_id)"
              :src="imageSrc(work)"
              :alt="workTitle(work, index)"
              loading="lazy"
              @error="markImageFailed(work.artwork_id)"
            />
            <span v-else class="work-card__fallback" aria-hidden="true">拼</span>
          </span>
          <span class="work-card__body">
            <strong>{{ workTitle(work, index) }}</strong>
            <span class="work-card__meta">{{ resultSizeLabel(work.size_preset) }} · {{ work.bead_count }} 豆 · {{ work.color_count }} 色</span>
            <span class="work-card__date">{{ formatDate(work.created_at) }}</span>
          </span>
        </button>
      </section>

      <div class="works-pager" v-if="hasMore">
        <button class="works-pager__button" type="button" :disabled="loadingMore" @click="loadMore">
          {{ loadingMore ? '加载中…' : '加载更多' }}
        </button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.works-page {
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  display: grid;
  gap: clamp(16px, 2.6vw, 26px);
  overflow-x: clip;
}

.works-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  min-width: 0;
  border: 1px solid rgba(237, 228, 218, 0.82);
  border-radius: 26px;
  background:
    linear-gradient(135deg, rgba(255, 241, 232, 0.92), rgba(255, 255, 255, 0.9) 56%, rgba(236, 247, 241, 0.72)),
    #fffaf7;
  box-shadow: 0 18px 44px rgba(255, 142, 83, 0.12);
  padding: clamp(18px, 3.2vw, 30px);
}

.works-hero__copy {
  display: grid;
  gap: 7px;
  min-width: 0;
}

.works-hero__copy span {
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 900;
}

.works-hero__copy h1 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(30px, 5vw, 48px);
  line-height: 1.08;
}

.works-hero__copy p {
  margin: 0;
  color: var(--pd-fg-2);
  font-size: clamp(13px, 1.6vw, 15px);
  font-weight: 800;
}

.works-hero__cta,
.works-empty__button,
.works-pager__button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 46px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: var(--pd-gradient);
  box-shadow: var(--pd-shadow-cta);
  color: #fff;
  cursor: pointer;
  font: inherit;
  font-weight: 900;
  padding: 0 22px;
  text-decoration: none;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    filter 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.works-hero__cta:hover,
.works-empty__button:hover,
.works-pager__button:hover:not(:disabled) {
  border-color: rgba(255, 142, 83, 0.54);
  box-shadow: 0 18px 32px rgba(255, 142, 83, 0.23), 0 9px 18px rgba(255, 107, 90, 0.16);
  filter: brightness(1.03);
  transform: translateY(-2px);
}

.works-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr));
  gap: clamp(14px, 2vw, 20px);
  min-width: 0;
}

.work-card {
  display: grid;
  gap: 13px;
  min-width: 0;
  appearance: none;
  border: 1px solid rgba(237, 228, 218, 0.86);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 16px 34px rgba(45, 45, 45, 0.07);
  color: inherit;
  cursor: pointer;
  font: inherit;
  padding: 12px;
  text-align: left;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.work-card:hover {
  border-color: rgba(255, 142, 83, 0.48);
  box-shadow: 0 22px 46px rgba(255, 142, 83, 0.16), 0 14px 28px rgba(45, 45, 45, 0.08);
  transform: translateY(-3px);
}

.work-card__thumb {
  position: relative;
  display: grid;
  place-items: center;
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  border-radius: 16px;
  background:
    repeating-linear-gradient(45deg, rgba(237, 228, 218, 0.28) 0 1px, transparent 1px 12px),
    linear-gradient(135deg, rgba(255, 241, 232, 0.94), rgba(244, 250, 247, 0.88));
}

.work-card__thumb img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
}

.work-card__fallback,
.works-empty__mark {
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: var(--pd-gradient-warm);
  color: #fff;
  font-family: var(--pd-font-display);
  font-weight: 900;
}

.work-card__fallback {
  width: 58px;
  height: 58px;
  font-size: 22px;
  box-shadow: var(--pd-shadow-cta);
}

.work-card__body {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.work-card__body strong,
.work-card__meta,
.work-card__date {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.work-card__body strong {
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(17px, 2vw, 19px);
  font-weight: 900;
}

.work-card__meta {
  color: var(--pd-fg-2);
  font-size: 13px;
  font-weight: 900;
}

.work-card__date {
  color: #a5968b;
  font-size: 12px;
  font-weight: 800;
}

.works-empty {
  display: grid;
  justify-items: center;
  gap: 12px;
  border: 1px solid rgba(237, 228, 218, 0.86);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--pd-shadow-float);
  padding: clamp(34px, 6vw, 64px) clamp(18px, 4vw, 36px);
  text-align: center;
}

.works-empty__mark {
  width: 62px;
  height: 62px;
  box-shadow: var(--pd-shadow-cta);
}

.works-empty h2 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(24px, 4vw, 34px);
}

.works-empty p {
  width: min(100%, 460px);
  margin: 0;
  color: var(--pd-fg-2);
  font-weight: 800;
  line-height: 1.65;
}

.works-pager {
  display: grid;
  justify-items: center;
}

.works-pager__button:disabled {
  background: #ede5dd;
  box-shadow: none;
  color: #9b8e84;
  cursor: wait;
}

.work-card--skeleton {
  cursor: wait;
  pointer-events: none;
}

.work-card--skeleton .work-card__thumb,
.work-card__line {
  overflow: hidden;
  background: linear-gradient(90deg, rgba(255, 241, 232, 0.8), rgba(255, 255, 255, 0.94), rgba(255, 241, 232, 0.8));
  background-size: 220% 100%;
  animation: worksShimmer 1.5s ease-in-out infinite;
}

.work-card__line {
  width: 62%;
  height: 15px;
  border-radius: 999px;
}

.work-card__line--wide {
  width: 86%;
}

@keyframes worksShimmer {
  from {
    background-position: 100% 0;
  }

  to {
    background-position: -100% 0;
  }
}

@media (max-width: 560px) {
  .works-hero {
    align-items: stretch;
    border-radius: 22px;
    flex-direction: column;
  }

  .works-hero__cta,
  .works-empty__button,
  .works-pager__button {
    width: 100%;
  }

  .works-grid {
    grid-template-columns: 1fr;
  }
}
</style>
