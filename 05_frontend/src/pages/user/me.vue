<template>
  <MiniProgramLayout variant="home" title="我的" :scroll="true">
    <section class="me">
      <section class="me__profile">
        <image v-if="avatarUrl" class="me__avatar-img" :src="avatarUrl" mode="aspectFill" />
        <div v-else class="me__avatar" aria-hidden="true">
          <span class="me__avatar-head"></span>
          <span class="me__avatar-body"></span>
        </div>
        <div class="me__user">
          <h2 class="me__nickname">{{ nickname }}</h2>
          <p class="me__user-meta">{{ profileStatus }}</p>
        </div>
        <button v-if="!isLoggedIn" type="button" class="me__login-btn" @click="goLogin">
          登录/注册
        </button>
      </section>

      <section v-if="!isLoggedIn" class="card me__guest">
        <h3 class="me__guest-title">登录后保存你的拼豆作品</h3>
        <p class="me__guest-text">{{nativeCopy.native_intro[0]}}</p>
        <button type="button" class="btn btn--primary btn--block btn--md" @click="goLogin">
          登录 / 注册
        </button>
      </section>

      <section v-else class="card me__credits">
        <div class="me__credits-head">
          <h3 class="me__credits-title">我的额度</h3>
          <button type="button" class="me__credits-more" @click="goCdk">去兑换 ›</button>
        </div>
        <div class="me__credits-list">
          <div class="me__credits-row">
            <div class="me__credits-label">
              <span class="me__credits-name">脚本生成</span>
              <span class="me__credits-sub">快速量化图纸</span>
            </div>
            <span class="me__credits-value">{{ scriptQuotaLabel }}</span>
          </div>
          <div class="me__credits-row">
            <div class="me__credits-label">
              <span class="me__credits-name">AI 精品</span>
              <span class="me__credits-sub">Q版预览 + 图纸</span>
            </div>
            <span class="me__credits-value">{{ aiCreditsLabel }}</span>
          </div>
          <div class="me__credits-row">
            <div class="me__credits-label">
              <span class="me__credits-name">月卡</span>
              <span class="me__credits-sub">高级图纸与批量导出</span>
            </div>
            <span class="me__credits-value" :class="{ 'me__credits-value--off': !isMonthlyMember }">
              {{ monthlyLabel }}
            </span>
          </div>
        </div>
      </section>

      <nav class="me__menu" aria-label="个人中心">
        <button type="button" class="me__menu-item" @click="goWorks">
          <span class="me__menu-icon me__menu-icon--grid" aria-hidden="true">
            <span></span><span></span><span></span><span></span>
          </span>
          <span class="me__menu-label">我的作品</span>
          <span class="me__menu-arrow" aria-hidden="true">›</span>
        </button>

        <button type="button" class="me__menu-item" @click="goCdk">
          <span class="me__menu-icon me__menu-icon--ticket" aria-hidden="true"></span>
          <span class="me__menu-label">兑换 CDK</span>
          <span class="me__menu-arrow" aria-hidden="true">›</span>
        </button>

        <button type="button" class="me__menu-item" @click="showCsQr = true">
          <span class="me__menu-icon me__menu-icon--chat" aria-hidden="true"></span>
          <span class="me__menu-label">加客服微信</span>
          <span class="me__menu-arrow" aria-hidden="true">›</span>
        </button>

        <button type="button" class="me__menu-item" @click="goAgreement">
          <span class="me__menu-icon me__menu-icon--doc" aria-hidden="true"></span>
          <span class="me__menu-label">用户协议与隐私政策</span>
          <span class="me__menu-arrow" aria-hidden="true">›</span>
        </button>

        <button type="button" class="me__menu-item" @click="showAbout">
          <span class="me__menu-icon me__menu-icon--info" aria-hidden="true"></span>
          <span class="me__menu-label">关于 PinDou</span>
          <span class="me__menu-arrow" aria-hidden="true">v0.1.0 ›</span>
        </button>

        <button v-if="isLoggedIn" type="button" class="me__menu-item" @click="handleLogout">
          <span class="me__menu-icon me__menu-icon--logout" aria-hidden="true"></span>
          <span class="me__menu-label">退出登录</span>
          <span class="me__menu-arrow" aria-hidden="true">›</span>
        </button>
      </nav>

      <p v-if="loadError" class="me__error">{{ loadError }}</p>
      <p class="footnote me__footer">
        上传图片仅用于生成图纸，原图按隐私策略定期删除
      </p>

      <div v-if="showCsQr" class="me__cs-sheet">
        <button type="button" class="me__cs-backdrop" aria-label="关闭" @click="showCsQr = false"></button>
        <div class="me__cs-panel" role="dialog" aria-label="客服二维码">
          <div class="me__cs-handle" aria-hidden="true"></div>
          <h3 class="me__cs-title">加客服微信</h3>
          <p class="me__cs-sub">付款、CDK 售后、人工精修都可以找客服</p>
          <image class="me__cs-qr" src="/static/assets/qr-placeholder.svg" mode="aspectFit" />
          <p class="me__cs-hint">长按二维码识别</p>
          <button type="button" class="btn btn--secondary btn--block btn--md me__cs-close" @click="showCsQr = false">
            关闭
          </button>
        </div>
      </div>
    </section>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';
import { useUserStore } from '../../store/user';
import { BASE_URL, IS_H5_CLIENT } from '../../utils/request';
import nativeCopy from '../../../../05_studio/src/content/miniapp.json';

const userStore = useUserStore();
const showCsQr = ref(false);
const loadError = ref('');

const API_ORIGIN = BASE_URL.replace(/\/api\/v\d+$/, '');

const user = computed(() => userStore.userInfo);
const isLoggedIn = computed(() => userStore.isLoggedIn);
const nickname = computed(() => user.value?.email || user.value?.nickname || '未登录');
const avatarUrl = computed(() => normalizeAssetUrl(user.value?.avatar));
const isMonthlyMember = computed(() => userStore.isMonthlyMember);
const freeCredits = computed(() => user.value?.free_credits_remaining || 0);
const paidCredits = computed(() => user.value?.paid_credits || 0);

const profileStatus = computed(() => {
  if (!userStore.token) return '未登录';
  if (user.value?.email) return '邮箱账号 · 已登录';
  if (IS_H5_CLIENT) return '邮箱账号 · 待验证';
  if (user.value?.sensitive_consent_at) return '微信用户 · 已授权生成';
  if (user.value?.privacy_consent_at) return '微信用户 · 已同意隐私协议';
  return '微信用户 · 待授权';
});

const scriptQuotaLabel = computed(() => {
  const total = freeCredits.value + paidCredits.value;
  if (total >= 9999) return '不限';
  return '每日免费';
});

const aiCreditsLabel = computed(() => {
  if (isMonthlyMember.value) return '不限';
  const total = freeCredits.value + paidCredits.value;
  if (total >= 9999) return '不限';
  return `剩 ${total} 次`;
});

const monthlyLabel = computed(() => {
  if (!isMonthlyMember.value || !user.value?.monthly_card_expires_at) return '未开通';
  return `${formatDate(user.value.monthly_card_expires_at)} 到期`;
});

const normalizeAssetUrl = (url?: string | null) => {
  if (!url) return '';
  if (/^https?:\/\//.test(url)) return url;
  if (url.startsWith('/static/')) return `${API_ORIGIN}${url}`;
  return url;
};

const formatDate = (dateText: string) => {
  const date = new Date(dateText);
  if (Number.isNaN(date.getTime())) return '未知';
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${month}/${day}`;
};

const loadProfile = async () => {
  loadError.value = '';
  if (!userStore.token) {
    return;
  }
  try {
    await userStore.fetchProfile();
  } catch (error) {
    console.error('加载个人资料失败:', error);
    loadError.value = '个人资料暂时加载失败，稍后刷新即可。';
  }
};

const goLogin = () => {
  uni.navigateTo({
    url: IS_H5_CLIENT ? `/pages/auth/email-login?redirect=${encodeURIComponent('/pages/user/me')}` : '/pages/auth/studio-login'
  });
};

const goWorks = () => {
  if (!userStore.requireH5Login('/pages/artwork/list')) return;
  uni.switchTab({
    url: '/pages/artwork/list'
  });
};

const goCdk = () => {
  if (!userStore.requireH5Login('/pages/cdk/redeem')) return;
  uni.navigateTo({
    url: '/pages/cdk/redeem'
  });
};

const handleLogout = () => {
  userStore.logout();
  uni.showToast({ title: '已退出', icon: 'none' });
};

const goAgreement = () => {
  uni.navigateTo({
    url: '/pages/consent/consent?type=privacy'
  });
};

const showAbout = () => {
  uni.showModal({
    title: '关于 PinDou',
    content: 'PinDou 是面向拼豆玩家的照片转图纸工具。当前为 Phase 2 测试版本，生成效果和导出格式会继续打磨。',
    showCancel: false,
    confirmText: '知道了',
    confirmColor: '#FF6B9D'
  });
};

onShow(() => {
  loadProfile();
});
</script>

<style lang="scss" scoped>
.me {
  padding-bottom: 28px;
}

.me__profile {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 20px 16px;
}

.me__avatar,
.me__avatar-img {
  width: 60px;
  height: 60px;
  border-radius: 999px;
  overflow: hidden;
  flex-shrink: 0;
  background: var(--pd-pink-100);
}

.me__avatar {
  position: relative;
}

.me__avatar-head {
  position: absolute;
  left: 20px;
  top: 14px;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: #fff;
}

.me__avatar-body {
  position: absolute;
  left: 10px;
  top: 40px;
  width: 40px;
  height: 28px;
  border-radius: 999px 999px 0 0;
  background: #fff;
}

.me__user {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.me__nickname {
  margin: 0;
  font-family: var(--pd-font-display);
  font-size: 18px;
  font-weight: 800;
  color: var(--pd-fg-1);
}

.me__user-meta {
  margin: 0;
  font-size: 12px;
  color: var(--pd-fg-2);
}

.me__login-btn {
  border: 0;
  border-radius: 999px;
  background: var(--pd-gradient-warm);
  color: #fff;
  height: 36px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 800;
  box-shadow: 0 10px 22px rgba(255, 142, 83, 0.22);
}

.me__guest {
  margin: 0 16px 16px;
  padding: 18px;
}

.me__guest-title {
  margin: 0 0 8px;
  font-family: var(--pd-font-display);
  font-size: 16px;
  font-weight: 800;
  color: var(--pd-fg-1);
}

.me__guest-text {
  margin: 0 0 16px;
  font-size: 13px;
  line-height: 1.65;
  color: var(--pd-fg-2);
}

.me__credits {
  margin: 0 16px 16px;
  padding: 16px 18px 8px;
}

.me__credits-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.me__credits-title {
  margin: 0;
  font-family: var(--pd-font-display);
  font-size: 14px;
  font-weight: 800;
  color: var(--pd-fg-1);
}

.me__credits-more {
  border: 0;
  background: transparent;
  color: var(--pd-pink-deep);
  font-size: 13px;
  font-weight: 700;
  padding: 4px 0;
  line-height: 1.2;
}

.me__credits-list {
  display: flex;
  flex-direction: column;
}

.me__credits-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 0.5px solid var(--pd-divider);
}

.me__credits-row:last-child {
  border-bottom: 0;
}

.me__credits-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
  max-width: 190px;
}

.me__credits-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--pd-fg-1);
}

.me__credits-sub {
  font-size: 11px;
  color: var(--pd-fg-2);
}

.me__credits-value {
  font-size: 13px;
  color: var(--pd-fg-1);
  flex-shrink: 0;
  white-space: nowrap;
  text-align: right;
}

.me__credits-value strong {
  font-family: var(--pd-font-display);
  font-size: 15px;
  color: var(--pd-pink-deep);
}

.me__credits-value--off {
  color: var(--pd-fg-3);
  font-size: 12px;
}

.me__menu {
  background: var(--pd-card);
  border-radius: var(--pd-r-card);
  box-shadow: var(--pd-shadow-card);
  margin: 0 16px;
  overflow: hidden;
}

.me__menu-item {
  border: 0;
  background: transparent;
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 14px 18px;
  border-bottom: 0.5px solid var(--pd-divider);
  font-size: 14px;
  color: var(--pd-fg-1);
  text-align: left;
}

.me__menu-item:last-child {
  border-bottom: 0;
}

.me__menu-item:active {
  background: var(--pd-bg-warm);
}

.me__menu-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--pd-pink-50);
  color: var(--pd-pink-deep);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
}

.me__menu-icon--grid {
  display: grid;
  grid-template-columns: repeat(2, 7px);
  grid-template-rows: repeat(2, 7px);
  gap: 3px;
}

.me__menu-icon--grid span {
  border-radius: 2px;
  border: 1.5px solid currentColor;
}

.me__menu-icon--ticket::before {
  content: "";
  width: 16px;
  height: 12px;
  border: 1.6px solid currentColor;
  border-radius: 3px;
}

.me__menu-icon--ticket::after {
  content: "";
  position: absolute;
  width: 1.6px;
  height: 12px;
  background: currentColor;
  opacity: 0.55;
}

.me__menu-icon--chat::before {
  content: "";
  width: 16px;
  height: 13px;
  border: 1.6px solid currentColor;
  border-radius: 5px;
}

.me__menu-icon--chat::after {
  content: "";
  position: absolute;
  left: 8px;
  top: 18px;
  width: 7px;
  height: 7px;
  border-left: 1.6px solid currentColor;
  border-bottom: 1.6px solid currentColor;
  transform: skew(-12deg);
}

.me__menu-icon--doc::before {
  content: "";
  width: 14px;
  height: 17px;
  border: 1.6px solid currentColor;
  border-radius: 3px;
}

.me__menu-icon--doc::after {
  content: "";
  position: absolute;
  width: 8px;
  height: 1.6px;
  background: currentColor;
  box-shadow: 0 5px 0 currentColor;
}

.me__menu-icon--info::before {
  content: "i";
  font-family: var(--pd-font-display);
  font-weight: 900;
  font-size: 16px;
}

.me__menu-icon--logout::before {
  content: "";
  width: 14px;
  height: 14px;
  border: 1.6px solid currentColor;
  border-radius: 4px;
}

.me__menu-icon--logout::after {
  content: "";
  position: absolute;
  right: 6px;
  width: 9px;
  height: 1.6px;
  border-radius: 99px;
  background: currentColor;
}

.me__menu-label {
  flex: 1;
}

.me__menu-arrow {
  font-size: 13px;
  color: var(--pd-fg-3);
}

.me__error {
  margin: 14px 20px 0;
  text-align: center;
  color: var(--pd-danger);
  font-size: 12px;
}

.me__footer {
  margin: 20px 20px 12px;
}

.me__cs-sheet {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: flex;
  align-items: flex-end;
}

.me__cs-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(45, 45, 45, 0.32);
  border: 0;
  padding: 0;
}

.me__cs-panel {
  position: relative;
  width: 100%;
  background: var(--pd-card);
  border-radius: 20px 20px 0 0;
  padding: 12px 20px calc(20px + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: var(--pd-shadow-modal);
  animation: me-slide-up var(--pd-dur-base) var(--pd-ease-soft);
}

.me__cs-handle {
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background: var(--pd-divider);
  margin-bottom: 12px;
}

.me__cs-title {
  margin: 0 0 4px;
  font-family: var(--pd-font-display);
  font-size: 17px;
  font-weight: 800;
  color: var(--pd-fg-1);
}

.me__cs-sub {
  margin: 0 0 16px;
  font-size: 12px;
  color: var(--pd-fg-2);
  text-align: center;
}

.me__cs-qr {
  width: 180px;
  height: 180px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid var(--pd-divider);
  margin-bottom: 10px;
}

.me__cs-hint {
  margin: 0 0 16px;
  font-size: 12px;
  color: var(--pd-fg-2);
}

.me__cs-close {
  width: 100%;
}

@keyframes me-slide-up {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}
</style>
