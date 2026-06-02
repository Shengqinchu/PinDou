<template>
  <div class="frame" :style="frameStyle">
    <!-- #ifdef H5 -->
    <nav class="desktop-nav" aria-label="PinDou 桌面导航">
      <button type="button" class="desktop-nav__brand" @click="goHome">
        <span class="desktop-nav__logo-dot" aria-hidden="true"></span>
        <span>PinDou 拼豆</span>
      </button>
      <div class="desktop-nav__links" aria-label="主导航">
        <button
          type="button"
          class="desktop-nav__link"
          :class="{ 'desktop-nav__link--active': isDesktopNavActive('home') }"
          @click="goHome"
        >
          首页
        </button>
        <button
          type="button"
          class="desktop-nav__link"
          :class="{ 'desktop-nav__link--active': isDesktopNavActive('works') }"
          @click="goWorks"
        >
          作品集
        </button>
        <button
          type="button"
          class="desktop-nav__link"
          :class="{ 'desktop-nav__link--active': isDesktopNavActive('me') }"
          @click="goMe"
        >
          我的
        </button>
        <button type="button" class="desktop-nav__user" @click="goMe" aria-label="打开个人中心">
          <span class="desktop-nav__avatar" aria-hidden="true">{{ desktopUserInitial }}</span>
          <span class="desktop-nav__user-text">{{ desktopUserName }}</span>
        </button>
      </div>
    </nav>
    <!-- #endif -->

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

    <!-- #ifdef H5 -->
    <footer class="desktop-footer" aria-label="PinDou 页脚">
      <button type="button" class="desktop-footer__link" @click="goAgreement">用户服务协议</button>
      <span class="desktop-footer__dot" aria-hidden="true"></span>
      <button type="button" class="desktop-footer__link" @click="goPrivacy">隐私政策</button>
    </footer>
    <!-- #endif -->
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
const currentRoute = computed(() => {
  const pages = getCurrentPages();
  const page = pages[pages.length - 1] as { route?: string } | undefined;
  return page?.route || '';
});
const desktopUserName = computed(() => userStore.userInfo?.nickname || '我的账户');
const desktopUserInitial = computed(() => {
  const first = desktopUserName.value.trim().charAt(0);
  return first || 'P';
});

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

const isDesktopNavActive = (section: 'home' | 'works' | 'me') => {
  if (section === 'home') return currentRoute.value.includes('pages/index/');
  if (section === 'works') return currentRoute.value.includes('pages/artwork/');
  return currentRoute.value.includes('pages/user/');
};

const goHome = () => {
  uni.switchTab({
    url: '/pages/index/index',
    fail: () => {
      uni.reLaunch({ url: '/pages/index/index' });
    }
  });
};

const goWorks = () => {
  uni.switchTab({
    url: '/pages/artwork/list',
    fail: () => {
      uni.navigateTo({ url: '/pages/artwork/list' });
    }
  });
};

const goMe = () => {
  uni.switchTab({
    url: '/pages/user/me',
    fail: () => {
      uni.navigateTo({ url: '/pages/user/me' });
    }
  });
};

const goAgreement = () => {
  uni.navigateTo({ url: '/pages/consent/consent?type=agreement' });
};

const goPrivacy = () => {
  uni.navigateTo({ url: '/pages/consent/consent?type=privacy' });
};

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
