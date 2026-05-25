<template>
  <div class="frame" :style="frameStyle">
    <!-- 微信系统状态栏 -->
    <div class="frame__status">
      <span class="frame__time">9:41</span>
      <span class="frame__indicators">
        <span class="frame__signal" aria-hidden="true">
          <span class="frame__signal-bar frame__signal-bar--1"></span>
          <span class="frame__signal-bar frame__signal-bar--2"></span>
          <span class="frame__signal-bar frame__signal-bar--3"></span>
          <span class="frame__signal-bar frame__signal-bar--4"></span>
        </span>
        <span class="frame__wifi" aria-hidden="true">
          <span class="frame__wifi-arc frame__wifi-arc--outer"></span>
          <span class="frame__wifi-arc frame__wifi-arc--inner"></span>
          <span class="frame__wifi-dot"></span>
        </span>
        <span class="frame__battery" aria-hidden="true">
          <span class="frame__battery-fill"></span>
          <span class="frame__battery-tip"></span>
        </span>
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
            <span class="frame__menu-dot"></span>
            <span class="frame__menu-dot"></span>
            <span class="frame__menu-dot"></span>
          </span>
          <span class="frame__capsule-divider"></span>
          <span class="frame__capsule-btn frame__capsule-btn--close" @click="handleExit">
            <span class="frame__close">x</span>
          </span>
        </span>
      </span>
    </header>

    <!-- 内页样式：返回箭头 + 居中标题 -->
    <header v-else class="frame__header frame__header--inner">
      <div class="frame__back" aria-label="返回" @click="handleBack">
        <span class="frame__back-icon">&lt;</span>
      </div>
      <span class="frame__title">{{ title }}</span>
      <span class="frame__right">
        <span class="frame__capsule" aria-hidden="true">
          <span class="frame__capsule-btn frame__capsule-btn--menu">
            <span class="frame__menu-dot"></span>
            <span class="frame__menu-dot"></span>
            <span class="frame__menu-dot"></span>
          </span>
          <span class="frame__capsule-divider"></span>
          <span class="frame__capsule-btn frame__capsule-btn--close" @click="handleExit">
            <span class="frame__close">x</span>
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
