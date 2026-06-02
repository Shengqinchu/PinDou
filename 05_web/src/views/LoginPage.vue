<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { ApiError } from '../api';
import { useAuthStore } from '../stores/auth';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const email = ref('');
const code = ref('');
const feedback = ref('');
const feedbackKind = ref<'info' | 'success' | 'error'>('info');
const sending = ref(false);
const verifying = ref(false);
const cooldown = ref(0);

let cooldownTimer: number | undefined;

const normalizedEmail = computed(() => email.value.trim().toLowerCase());
const canSendCode = computed(() => isEmail(normalizedEmail.value) && !sending.value && cooldown.value <= 0);
const canVerify = computed(() => isEmail(normalizedEmail.value) && /^\d{6}$/.test(code.value.trim()) && !verifying.value);
const sendButtonText = computed(() => {
  if (sending.value) {
    return '发送中...';
  }
  if (cooldown.value > 0) {
    return `${cooldown.value}s 后重发`;
  }
  return '发送验证码';
});

async function handleSendCode(): Promise<void> {
  if (!isEmail(normalizedEmail.value)) {
    showMessage('请输入正确的邮箱地址。', 'error');
    return;
  }

  sending.value = true;
  showMessage('', 'info');

  try {
    const response = await auth.sendEmailCode(normalizedEmail.value);
    showMessage(response.message || '验证码已发送，请查看邮箱。', 'success');
    startCooldown(response.cooldown_seconds || 60);
  } catch (error) {
    showMessage(readErrorMessage(error, '验证码发送失败，请稍后再试。'), 'error');
  } finally {
    sending.value = false;
  }
}

async function handleVerify(): Promise<void> {
  if (!canVerify.value) {
    showMessage('请填写邮箱和 6 位验证码。', 'error');
    return;
  }

  verifying.value = true;
  showMessage('', 'info');

  try {
    await auth.loginWithEmail(normalizedEmail.value, code.value.trim());
    showMessage('登录成功，正在进入 PinDou。', 'success');
    await router.replace(readRedirectPath());
  } catch (error) {
    showMessage(readErrorMessage(error, '验证码不正确或已过期。'), 'error');
  } finally {
    verifying.value = false;
  }
}

function startCooldown(seconds: number): void {
  cooldown.value = Math.max(1, Math.floor(seconds));
  if (cooldownTimer) {
    window.clearInterval(cooldownTimer);
  }
  cooldownTimer = window.setInterval(() => {
    cooldown.value = Math.max(0, cooldown.value - 1);
    if (cooldown.value <= 0 && cooldownTimer) {
      window.clearInterval(cooldownTimer);
      cooldownTimer = undefined;
    }
  }, 1000);
}

function showMessage(message: string, kind: 'info' | 'success' | 'error'): void {
  feedback.value = message;
  feedbackKind.value = kind;
}

function readRedirectPath(): string {
  const redirect = route.query.redirect;
  if (typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')) {
    return redirect;
  }
  return '/me';
}

function readErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message || fallback;
  }
  if (error instanceof Error) {
    return error.message || fallback;
  }
  return fallback;
}

function isEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

onUnmounted(() => {
  if (cooldownTimer) {
    window.clearInterval(cooldownTimer);
  }
});
</script>

<template>
  <section class="login-page">
    <div class="login-card">
      <p class="eyebrow">Email Login</p>
      <h1>登录 / 注册 PinDou</h1>
      <p class="login-card__intro">输入邮箱接收 6 位验证码。首次验证会自动创建账号，之后用同一个邮箱继续查看作品和订单。</p>

      <form class="login-form" @submit.prevent="handleVerify">
        <label class="login-field">
          <span>邮箱</span>
          <input
            v-model="email"
            type="email"
            inputmode="email"
            autocomplete="email"
            placeholder="you@example.com"
          />
        </label>

        <div class="login-code-row">
          <label class="login-field login-field--code">
            <span>验证码</span>
            <input
              v-model="code"
              type="text"
              inputmode="numeric"
              autocomplete="one-time-code"
              maxlength="6"
              placeholder="6 位数字"
            />
          </label>
          <button class="login-send" type="button" :disabled="!canSendCode" @click="handleSendCode">
            {{ sendButtonText }}
          </button>
        </div>

        <p v-if="feedback" class="login-feedback" :class="`login-feedback--${feedbackKind}`" role="status" aria-live="polite">
          {{ feedback }}
        </p>

        <button class="pd-btn pd-btn--primary login-submit" type="submit" :disabled="!canVerify">
          {{ verifying ? '登录中...' : '登录 / 注册' }}
        </button>
      </form>
    </div>
  </section>
</template>

<style scoped>
.login-page {
  min-height: calc(100vh - 160px);
  display: grid;
  place-items: center;
}

.login-card {
  width: min(100%, 520px);
  padding: clamp(30px, 6vw, 56px);
  border: 1px solid rgba(237, 228, 218, 0.82);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--pd-shadow-float);
  text-align: center;
}

.login-card h1 {
  margin: 0 0 12px;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(30px, 5vw, 44px);
  line-height: 1.1;
}

.login-card__intro {
  margin: 0 auto 28px;
  max-width: 420px;
  color: var(--pd-fg-2);
}

.eyebrow {
  margin: 0 0 10px;
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.login-form {
  display: grid;
  gap: 16px;
  text-align: left;
}

.login-field {
  display: grid;
  gap: 8px;
  color: var(--pd-fg-1);
  font-size: 13px;
  font-weight: 900;
}

.login-field input {
  width: 100%;
  min-height: 50px;
  border: 1px solid var(--pd-stroke);
  border-radius: var(--pd-r-input);
  background: #fff;
  color: var(--pd-fg-1);
  font: inherit;
  font-size: 15px;
  outline: none;
  padding: 0 16px;
  transition: border-color var(--pd-dur-fast) var(--pd-ease-out), box-shadow var(--pd-dur-fast) var(--pd-ease-out);
}

.login-field input:focus {
  border-color: var(--pd-orange);
  box-shadow: 0 0 0 4px rgba(255, 142, 83, 0.16);
}

.login-code-row {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: end;
  gap: 12px;
}

.login-send {
  min-width: 116px;
  min-height: 50px;
  border: 1px solid rgba(255, 142, 83, 0.36);
  border-radius: var(--pd-r-input);
  background: var(--pd-peach-50);
  color: var(--pd-orange);
  cursor: pointer;
  font: inherit;
  font-size: 14px;
  font-weight: 900;
  padding: 0 16px;
}

.login-send:disabled,
.login-submit:disabled {
  cursor: not-allowed;
  filter: grayscale(0.35);
  opacity: 0.58;
  transform: none;
}

.login-feedback {
  margin: 0;
  border-radius: 14px;
  font-size: 13px;
  font-weight: 800;
  padding: 12px 14px;
  text-align: left;
}

.login-feedback--success {
  background: rgba(52, 199, 89, 0.12);
  color: #168538;
}

.login-feedback--error {
  background: rgba(255, 90, 90, 0.12);
  color: #cc3d3d;
}

.login-feedback--info {
  background: var(--pd-peach-50);
  color: var(--pd-fg-2);
}

.login-submit {
  width: 100%;
}

@media (max-width: 640px) {
  .login-page {
    min-height: calc(100vh - 112px);
  }

  .login-card {
    padding: 28px 20px;
    border-radius: 22px;
  }

  .login-code-row {
    grid-template-columns: 1fr;
  }

  .login-send {
    width: 100%;
  }
}
</style>
