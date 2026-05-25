<template>
  <div class="frame" :style="frameStyle">
    <!-- 微信系统状态栏 -->
    <div class="frame__status">
      <span class="frame__time">9:41</span>
      <span class="frame__indicators">
        <!-- 信号 SVG -->
        <svg width="17" height="11" viewBox="0 0 17 11" aria-hidden="true" style="display: block;">
          <rect x="0" y="7" width="3" height="4" rx="0.5" fill="currentColor"/>
          <rect x="4.5" y="5" width="3" height="6" rx="0.5" fill="currentColor"/>
          <rect x="9" y="2.5" width="3" height="8.5" rx="0.5" fill="currentColor"/>
          <rect x="13.5" y="0" width="3" height="11" rx="0.5" fill="currentColor"/>
        </svg>
        <!-- WIFI SVG -->
        <svg width="15" height="11" viewBox="0 0 15 11" aria-hidden="true" style="display: block;">
          <path d="M7.5 2.8C9.6 2.8 11.5 3.6 12.8 5L13.8 4C12.2 2.3 9.9 1.2 7.5 1.2 5.1 1.2 2.8 2.3 1.2 4L2.2 5C3.5 3.6 5.4 2.8 7.5 2.8Z" fill="currentColor"/>
          <path d="M7.5 6C8.7 6 9.8 6.5 10.6 7.3L11.6 6.3C10.5 5.2 9 4.4 7.5 4.4 6 4.4 4.5 5.2 3.4 6.3L4.4 7.3C5.2 6.5 6.3 6 7.5 6Z" fill="currentColor"/>
          <circle cx="7.5" cy="9.5" r="1.3" fill="currentColor"/>
        </svg>
        <!-- 电池 SVG -->
        <svg width="25" height="12" viewBox="0 0 25 12" aria-hidden="true" style="display: block;">
          <rect x="0.5" y="0.5" width="21" height="11" rx="2.8" stroke="currentColor" stroke-opacity="0.4" fill="none"/>
          <rect x="2" y="2" width="18" height="8" rx="1.5" fill="currentColor"/>
          <path d="M22.7 4.3v3.4c.8-.2 1.3-.9 1.3-1.7 0-.8-.5-1.5-1.3-1.7Z" fill="currentColor" fill-opacity="0.4"/>
        </svg>
      </span>
    </div>

    <!-- 页面导航栏 -->
    <!-- 首页样式：Logo + 标题左对齐 -->
    <header v-if="variant === 'home'" class="frame__header frame__header--home">
      <span class="frame__logo">
        <span class="frame__logo-dot">
          <span class="frame__logo-dot-core"></span>
        </span>
        <span>{{ title }}</span>
      </span>
      <span class="frame__right">
        <span class="frame__capsule" aria-hidden="true">
          <span class="frame__capsule-btn frame__capsule-btn--menu">
            <svg width="20" height="6" viewBox="0 0 20 6" aria-hidden="true" style="display: block;">
              <circle cx="3" cy="3" r="1.6" fill="currentColor"/>
              <circle cx="10" cy="3" r="1.6" fill="currentColor"/>
              <circle cx="17" cy="3" r="1.6" fill="currentColor"/>
            </svg>
          </span>
          <span class="frame__capsule-divider"></span>
          <span class="frame__capsule-btn frame__capsule-btn--close" @click="handleExit">
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" style="display: block;">
              <path d="M1 1l10 10M11 1L1 11" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
          </span>
        </span>
      </span>
    </header>

    <!-- 内页样式：返回箭头 + 居中标题 -->
    <header v-else class="frame__header frame__header--inner">
      <div class="frame__back" aria-label="返回" @click="handleBack">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="display: block;">
          <path d="M15 18l-6-6 6-6"/>
        </svg>
      </div>
      <span class="frame__title">{{ title }}</span>
      <span class="frame__right">
        <span class="frame__capsule" aria-hidden="true">
          <span class="frame__capsule-btn frame__capsule-btn--menu">
            <svg width="20" height="6" viewBox="0 0 20 6" aria-hidden="true" style="display: block;">
              <circle cx="3" cy="3" r="1.6" fill="currentColor"/>
              <circle cx="10" cy="3" r="1.6" fill="currentColor"/>
              <circle cx="17" cy="3" r="1.6" fill="currentColor"/>
            </svg>
          </span>
          <span class="frame__capsule-divider"></span>
          <span class="frame__capsule-btn frame__capsule-btn--close" @click="handleExit">
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" style="display: block;">
              <path d="M1 1l10 10M11 1L1 11" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
          </span>
        </span>
      </span>
    </header>

    <!-- 主体区域 -->
    <main class="frame__body" :class="{ 'frame__body--scroll': scroll }">
      <slot></slot>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useUserStore } from '../store/user';

interface Props {
  variant?: 'home' | 'inner';
  title?: string;
  backUrl?: string; // 手动返回路径，如果不指定，默认执行 uni.navigateBack()
  scroll?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'inner',
  title: 'PinDou',
  backUrl: '',
  scroll: true
});

const userStore = useUserStore();
const uiMetrics = computed(() => userStore.uiMetrics);

const frameStyle = computed(() => ({
  '--pd-status-height': `${uiMetrics.value.statusBarHeight}px`,
  '--pd-menu-top': `${uiMetrics.value.menuButtonTop}px`,
  '--pd-menu-height': `${uiMetrics.value.menuButtonHeight}px`,
  '--pd-top-chrome-height': `${uiMetrics.value.topChromeHeight}px`,
  '--pd-safe-bottom': `${uiMetrics.value.safeAreaBottom}px`,
  '--pd-capsule-reserve': `${uiMetrics.value.capsuleReserveRight}px`,
  '--pd-capsule-width': `${uiMetrics.value.menuButtonWidth}px`,
}));

const handleBack = () => {
  if (props.backUrl) {
    uni.reLaunch({
      url: props.backUrl
    });
  } else {
    // 默认行为：返回上一个历史页面
    uni.navigateBack({
      fail: () => {
        // 如果返回失败 (例如没有上级页面)，则 fallback 回首页
        uni.reLaunch({
          url: '/pages/index/index'
        });
      }
    });
  }
};

const handleExit = () => {
  // 微信小程序退出模拟，或者直接跳转首页
  uni.reLaunch({
    url: '/pages/index/index'
  });
};
</script>
