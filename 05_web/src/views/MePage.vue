<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { useAuthStore } from '../stores/auth';

const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const error = ref('');

const credits = computed(() => {
  const free = auth.user?.free_credits_remaining || 0;
  const paid = auth.user?.paid_credits || 0;
  return free + paid;
});

onMounted(async () => {
  if (!auth.user && auth.token) {
    loading.value = true;
    try {
      await auth.refreshProfile();
    } catch (refreshError) {
      error.value = refreshError instanceof Error ? refreshError.message : '账号信息加载失败，请重新登录。';
    } finally {
      loading.value = false;
    }
  }
});

async function logout(): Promise<void> {
  auth.logout();
  await router.replace('/login');
}
</script>

<template>
  <section class="me-page">
    <div class="me-card">
      <div class="me-hero">
        <div>
          <p class="eyebrow">我的 PinDou</p>
          <h1>欢迎回来</h1>
          <p>这里会收纳你的拼豆图纸、AI 额度和订单记录。</p>
        </div>
        <div class="me-badge" aria-hidden="true">PD</div>
      </div>

      <p v-if="loading" class="me-muted">正在读取账号信息...</p>
      <p v-else-if="error" class="me-error">{{ error }}</p>

      <template v-if="auth.user">
        <div class="me-profile">
          <div class="me-avatar" aria-hidden="true">{{ auth.displayName.slice(0, 1).toUpperCase() }}</div>
          <div>
            <strong>{{ auth.displayName }}</strong>
            <span>邮箱账号 · 已登录</span>
          </div>
        </div>

        <dl class="me-stats">
          <div class="me-stat me-stat--primary">
            <dt><span aria-hidden="true">AI</span> AI 额度</dt>
            <dd>{{ credits }}</dd>
            <small>可用于生成和重试图纸</small>
          </div>
          <div class="me-stat">
            <dt><span aria-hidden="true">赠</span> 免费额度</dt>
            <dd>{{ auth.user.free_credits_remaining || 0 }}</dd>
            <small>系统赠送额度</small>
          </div>
          <div class="me-stat">
            <dt><span aria-hidden="true">购</span> 付费额度</dt>
            <dd>{{ auth.user.paid_credits || 0 }}</dd>
            <small>购买后长期保留</small>
          </div>
        </dl>

        <div class="me-next">
          <strong>下一步</strong>
          <p>上传一张主体清晰、背景简单的照片，生成更干净的拼豆图纸。</p>
          <RouterLink class="pd-btn pd-btn--primary" to="/upload">去上传照片</RouterLink>
        </div>

        <button class="pd-btn me-logout" type="button" @click="logout">退出登录</button>
      </template>
    </div>
  </section>
</template>

<style scoped>
.me-page {
  display: grid;
  place-items: start center;
}

.me-card {
  width: min(100%, 760px);
  padding: clamp(28px, 5vw, 48px);
  border: 1px solid rgba(237, 228, 218, 0.82);
  border-radius: 28px;
  background:
    radial-gradient(circle at 88% 12%, rgba(164, 212, 197, 0.22), transparent 30%),
    rgba(255, 255, 255, 0.9);
  box-shadow: var(--pd-shadow-float);
}

.me-hero {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 28px;
}

.me-card h1 {
  margin: 0 0 8px;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(30px, 5vw, 44px);
  line-height: 1.1;
  letter-spacing: 0;
}

.me-hero p:last-child {
  max-width: 420px;
  margin: 0;
  color: var(--pd-fg-2);
}

.eyebrow {
  margin: 0 0 10px;
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
  text-transform: uppercase;
}

.me-badge {
  width: 70px;
  height: 70px;
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 26px;
  background: var(--pd-gradient-warm);
  color: #fff;
  font-weight: 900;
  box-shadow: var(--pd-shadow-cta);
  transform: rotate(4deg);
}

.me-profile {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  border: 1px solid rgba(237, 228, 218, 0.8);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.76);
  padding: 16px;
}

.me-profile strong,
.me-profile span {
  display: block;
}

.me-profile strong {
  color: var(--pd-fg-1);
  font-size: 18px;
}

.me-profile span,
.me-muted {
  color: var(--pd-fg-2);
}

.me-avatar {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  border-radius: var(--pd-r-full);
  background: var(--pd-gradient-warm);
  color: #fff;
  font-weight: 900;
  box-shadow: var(--pd-shadow-cta);
}

.me-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 0 0 24px;
}

.me-stat {
  border: 1px solid var(--pd-stroke);
  border-radius: 18px;
  background: var(--pd-peach-50);
  padding: 16px;
}

.me-stat--primary {
  background: linear-gradient(145deg, rgba(255, 176, 136, 0.3), rgba(255, 241, 232, 0.86));
}

.me-stats dt {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 8px;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
}

.me-stats dt span {
  width: 24px;
  height: 24px;
  display: inline-grid;
  place-items: center;
  border-radius: var(--pd-r-full);
  background: rgba(255, 142, 83, 0.16);
  color: var(--pd-orange);
  font-size: 11px;
}

.me-stats dd {
  margin: 0;
  color: var(--pd-fg-1);
  font-size: 24px;
  font-weight: 900;
}

.me-stats small {
  display: block;
  margin-top: 6px;
  color: var(--pd-fg-2);
  font-size: 12px;
}

.me-next {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 12px 20px;
  margin-bottom: 14px;
  border: 1px solid rgba(164, 212, 197, 0.42);
  border-radius: 22px;
  background: rgba(164, 212, 197, 0.16);
  padding: 18px;
}

.me-next strong,
.me-next p {
  grid-column: 1;
}

.me-next strong {
  color: var(--pd-fg-1);
}

.me-next p {
  margin: 0;
  color: var(--pd-fg-2);
}

.me-next .pd-btn {
  grid-column: 2;
  grid-row: 1 / span 2;
  white-space: nowrap;
}

.me-error {
  border-radius: 14px;
  background: rgba(255, 90, 90, 0.12);
  color: #cc3d3d;
  font-size: 13px;
  font-weight: 800;
  padding: 12px 14px;
}

.me-logout {
  width: 100%;
  border: 1px solid rgba(255, 90, 90, 0.28);
  background: rgba(255, 90, 90, 0.1);
  color: var(--pd-danger);
}

@media (max-width: 640px) {
  .me-card {
    padding: 28px 20px;
    border-radius: 22px;
  }

  .me-hero {
    align-items: flex-start;
  }

  .me-badge {
    width: 54px;
    height: 54px;
    border-radius: 20px;
  }

  .me-stats {
    grid-template-columns: 1fr;
  }

  .me-next {
    grid-template-columns: 1fr;
  }

  .me-next .pd-btn {
    grid-column: 1;
    grid-row: auto;
    width: 100%;
  }
}
</style>
