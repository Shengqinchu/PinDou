<template>
  <div class="frame" :style="frameStyle">
    <!-- 页面导航栏 -->
    <!-- 首页样式：Logo + 标题左对齐 -->
    <header v-if="variant === 'home'" class="frame__header frame__header--home">
      <span class="frame__logo">
        <span class="frame__logo-dot">
          <span class="frame__logo-dot-core"></span>
        </span>
        <span>{{ title }}</span>
      </span>
    </header>

    <!-- 内页样式：返回箭头 + 居中标题 -->
    <header v-else class="frame__header frame__header--inner">
      <div class="frame__back" aria-label="返回" @click="handleBack">
        <span class="frame__back-icon" aria-hidden="true"></span>
      </div>
      <span class="frame__title">{{ title }}</span>
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
  '--pd-title-side-inset': `${Math.max(52, uiMetrics.value.capsuleReserveRight)}px`,
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

</script>
