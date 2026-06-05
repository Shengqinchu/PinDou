<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';

import { getArtworkGallery } from '../api';
import type { ArtworkListItem } from '../api/types';
import { resultSizeLabel } from '../stores/generation';

const MOBILE_PAGE_SIZE = 4;
const TABLET_PAGE_SIZE = 6;
const DESKTOP_PAGE_SIZE = 12;

const router = useRouter();
const works = ref<ArtworkListItem[]>([]);
const page = ref(1);
const pageSize = ref(DESKTOP_PAGE_SIZE);
const total = ref(0);
const hasMore = ref(false);
const loading = ref(true);
const errorMessage = ref('');
const failedImages = ref(new Set<string>());
const showBackTop = ref(false);
let resizeTimer: number | undefined;

const totalLabel = computed(() => {
  if (loading.value) {
    return '正在整理作品';
  }
  return `共 ${total.value} 个作品`;
});

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)));
const isFirstPage = computed(() => page.value <= 1);
const isLastPage = computed(() => page.value >= totalPages.value);

onMounted(() => {
  pageSize.value = responsivePageSize();
  void loadWorks(1);
  updateBackTopVisibility();
  window.addEventListener('scroll', updateBackTopVisibility, { passive: true });
  window.addEventListener('resize', schedulePageSizeRefresh, { passive: true });
});

onUnmounted(() => {
  window.removeEventListener('scroll', updateBackTopVisibility);
  window.removeEventListener('resize', schedulePageSizeRefresh);
  if (resizeTimer) {
    window.clearTimeout(resizeTimer);
  }
});

async function loadWorks(targetPage: number): Promise<void> {
  loading.value = true;
  errorMessage.value = '';
  try {
    const response = await getArtworkGallery(targetPage, pageSize.value);
    page.value = response.page;
    total.value = response.total;
    hasMore.value = response.has_more;
    works.value = response.items;
    failedImages.value = new Set();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '作品集暂时加载失败，请稍后再试。';
  } finally {
    loading.value = false;
  }
}

function openWork(work: ArtworkListItem): void {
  void router.push({ name: 'result', params: { id: work.artwork_id } });
}

function goToPage(targetPage: number): void {
  const normalizedPage = Math.min(Math.max(targetPage, 1), totalPages.value);
  if (loading.value || normalizedPage === page.value) {
    return;
  }
  void loadWorks(normalizedPage);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function goPreviousPage(): void {
  goToPage(page.value - 1);
}

function goNextPage(): void {
  goToPage(page.value + 1);
}

function responsivePageSize(): number {
  if (window.innerWidth <= 640) {
    return MOBILE_PAGE_SIZE;
  }
  if (window.innerWidth <= 1024) {
    return TABLET_PAGE_SIZE;
  }
  return DESKTOP_PAGE_SIZE;
}

function schedulePageSizeRefresh(): void {
  if (resizeTimer) {
    window.clearTimeout(resizeTimer);
  }
  resizeTimer = window.setTimeout(() => {
    const nextPageSize = responsivePageSize();
    if (nextPageSize === pageSize.value) {
      return;
    }
    const firstVisibleIndex = (page.value - 1) * pageSize.value;
    pageSize.value = nextPageSize;
    const nextPage = Math.floor(firstVisibleIndex / nextPageSize) + 1;
    void loadWorks(nextPage);
  }, 140);
}

function updateBackTopVisibility(): void {
  showBackTop.value = window.scrollY > window.innerHeight;
}

function scrollToTop(): void {
  window.scrollTo({ top: 0, behavior: 'smooth' });
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
        <h1>我的拼豆作品</h1>
        <p>{{ totalLabel }}</p>
      </div>
      <RouterLink class="works-hero__cta" to="/upload">去生成</RouterLink>
    </header>

    <section v-if="loading" class="works-grid" aria-label="作品加载中">
      <div v-for="item in pageSize" :key="item" class="work-card work-card--skeleton" aria-hidden="true">
        <span class="work-card__thumb"></span>
        <span class="work-card__line work-card__line--wide"></span>
        <span class="work-card__line"></span>
      </div>
    </section>

    <section v-else-if="errorMessage" class="works-empty" role="alert">
      <span class="works-empty__mark" aria-hidden="true">!</span>
      <h2>作品集没加载出来</h2>
      <p>{{ errorMessage }}</p>
      <button class="works-empty__button" type="button" @click="loadWorks(page)">重新加载</button>
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
              decoding="async"
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

      <nav class="works-pager" aria-label="作品分页">
        <button
          class="works-pager__button"
          type="button"
          :disabled="isFirstPage || loading"
          @click="goPreviousPage"
        >
          上一页
        </button>
        <span class="works-pager__status">第 {{ page }} / {{ totalPages }} 页</span>
        <button
          class="works-pager__button"
          type="button"
          :disabled="isLastPage || loading || !hasMore"
          @click="goNextPage"
        >
          下一页
        </button>
      </nav>
    </template>

    <button
      v-show="showBackTop"
      class="works-backtop"
      type="button"
      aria-label="回到顶部"
      @click="scrollToTop"
    >
      ↑
    </button>
  </section>
</template>

<style scoped>
.works-page {
  width: 100%;
  max-width: 1120px;
  min-height: calc(100dvh - var(--app-header-height, 64px) - clamp(36px, 10vw, 112px));
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: clamp(12px, 2vw, 22px);
  padding-inline: clamp(0px, 0.8vw, 6px);
  overflow-x: clip;
}

.works-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: clamp(10px, 2vw, 18px);
  min-width: 0;
  border: 1px solid rgba(237, 228, 218, 0.82);
  border-radius: clamp(20px, 2.4vw, 26px);
  background:
    linear-gradient(135deg, rgba(255, 241, 232, 0.92), rgba(255, 255, 255, 0.9) 56%, rgba(236, 247, 241, 0.72)),
    #fffaf7;
  box-shadow: 0 14px 34px rgba(255, 142, 83, 0.11);
  padding: clamp(14px, 2.4vw, 24px);
}

.works-hero__copy {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.works-hero__copy h1 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(26px, 3.8vw, 40px);
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
  min-height: 44px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: var(--pd-gradient);
  box-shadow: var(--pd-shadow-cta);
  color: #fff;
  cursor: pointer;
  font: inherit;
  font-weight: 900;
  padding: 0 20px;
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
  grid-template-columns: repeat(4, minmax(0, 1fr));
  grid-template-rows: repeat(3, minmax(0, 1fr));
  gap: clamp(12px, 1.8vw, 20px);
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
}

.work-card {
  display: grid;
  align-content: start;
  gap: clamp(8px, 1.2vw, 12px);
  height: 100%;
  min-width: 0;
  min-height: 0;
  appearance: none;
  border: 1px solid rgba(237, 228, 218, 0.86);
  border-radius: clamp(18px, 2vw, 22px);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 16px 34px rgba(45, 45, 45, 0.07);
  color: inherit;
  cursor: pointer;
  font: inherit;
  padding: clamp(9px, 1.35vw, 12px);
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
  border-radius: clamp(12px, 1.8vw, 16px);
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
  gap: clamp(4px, 0.8vw, 6px);
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
  font-size: clamp(15px, 1.8vw, 19px);
  font-weight: 900;
}

.work-card__meta {
  color: var(--pd-fg-2);
  font-size: clamp(11px, 1.25vw, 13px);
  font-weight: 900;
}

.work-card__date {
  color: #a5968b;
  font-size: clamp(10px, 1.15vw, 12px);
  font-weight: 800;
}

.works-empty {
  display: grid;
  align-content: center;
  justify-items: center;
  gap: 12px;
  flex: 1 1 auto;
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
  display: flex;
  align-items: center;
  justify-content: center;
  gap: clamp(8px, 2vw, 14px);
  min-width: 0;
}

.works-pager__status {
  min-width: 92px;
  color: var(--pd-fg-2);
  font-size: clamp(13px, 1.7vw, 15px);
  font-weight: 900;
  text-align: center;
  white-space: nowrap;
}

.works-pager__button:disabled {
  background: #ede5dd;
  border-color: rgba(217, 206, 195, 0.72);
  box-shadow: none;
  color: #9b8e84;
  cursor: not-allowed;
  filter: none;
  transform: none;
}

.works-backtop {
  position: fixed;
  right: max(18px, calc(env(safe-area-inset-right) + 18px));
  bottom: max(20px, calc(env(safe-area-inset-bottom) + 20px));
  z-index: 30;
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border: 1px solid rgba(255, 142, 83, 0.38);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 16px 36px rgba(45, 45, 45, 0.14), 0 8px 16px rgba(255, 142, 83, 0.16);
  color: var(--pd-orange);
  cursor: pointer;
  font: inherit;
  font-size: 22px;
  font-weight: 900;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.works-backtop:hover {
  border-color: rgba(255, 142, 83, 0.68);
  box-shadow: 0 20px 42px rgba(255, 142, 83, 0.2), 0 10px 20px rgba(45, 45, 45, 0.12);
  transform: translateY(-2px);
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

@media (max-width: 1024px) {
  .works-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    grid-template-rows: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .works-page {
    width: calc(100% + 24px);
    max-width: calc(100vw - 8px);
    height: calc(100svh - var(--app-header-height, 62px) - 36px);
    height: calc(100dvh - var(--app-header-height, 62px) - 36px);
    min-height: 0;
    margin-inline: -12px;
    gap: 10px;
    padding-inline: 0;
  }

  .works-hero {
    border-radius: 20px;
    padding: 12px;
  }

  .works-hero__copy {
    gap: 2px;
  }

  .works-hero__copy h1 {
    font-size: clamp(23px, 6.2vw, 27px);
  }

  .works-hero__copy p {
    font-size: 12px;
  }

  .works-hero__cta {
    flex: 0 0 auto;
    min-height: 44px;
    padding: 0 14px;
    font-size: 13px;
  }

  .works-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-rows: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .work-card {
    border-radius: 16px;
    gap: 8px;
    padding: 7px;
  }

  .work-card__thumb {
    border-radius: 12px;
  }

  .work-card__body {
    gap: 3px;
  }

  .work-card__body strong {
    font-size: 14px;
  }

  .work-card__meta {
    font-size: 10.5px;
  }

  .work-card__date {
    font-size: 10px;
  }

  .works-pager {
    gap: 8px;
  }

  .works-pager__button {
    min-width: 78px;
    min-height: 44px;
    padding: 0 14px;
    font-size: 13px;
  }

  .works-pager__status {
    min-width: 82px;
    font-size: 12px;
  }

  .work-card__fallback {
    width: 46px;
    height: 46px;
    font-size: 18px;
  }

  .works-backtop {
    width: 42px;
    height: 42px;
    font-size: 20px;
  }
}
</style>
