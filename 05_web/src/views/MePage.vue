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
      <p class="eyebrow">Account</p>
      <h1>我的账户</h1>

      <p v-if="loading" class="me-muted">正在读取账号信息...</p>
      <p v-else-if="error" class="me-error">{{ error }}</p>

      <template v-if="auth.user">
        <div class="me-profile">
          <div class="me-avatar" aria-hidden="true">{{ auth.displayName.slice(0, 1).toUpperCase() }}</div>
          <div>
            <strong>{{ auth.displayName }}</strong>
            <span>邮箱账号</span>
          </div>
        </div>

        <dl class="me-stats">
          <div>
            <dt>AI 额度</dt>
            <dd>{{ credits }}</dd>
          </div>
          <div>
            <dt>免费额度</dt>
            <dd>{{ auth.user.free_credits_remaining || 0 }}</dd>
          </div>
          <div>
            <dt>付费额度</dt>
            <dd>{{ auth.user.paid_credits || 0 }}</dd>
          </div>
        </dl>

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
  width: min(100%, 640px);
  padding: clamp(30px, 6vw, 56px);
  border: 1px solid rgba(237, 228, 218, 0.82);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--pd-shadow-float);
}

.me-card h1 {
  margin: 0 0 24px;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(30px, 5vw, 44px);
  line-height: 1.1;
}

.eyebrow {
  margin: 0 0 10px;
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.me-profile {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
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

.me-stats div {
  border: 1px solid var(--pd-stroke);
  border-radius: 18px;
  background: var(--pd-peach-50);
  padding: 16px;
}

.me-stats dt {
  margin: 0 0 8px;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
}

.me-stats dd {
  margin: 0;
  color: var(--pd-fg-1);
  font-size: 24px;
  font-weight: 900;
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

  .me-stats {
    grid-template-columns: 1fr;
  }
}
</style>
