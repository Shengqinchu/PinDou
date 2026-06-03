<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { ApiError } from '../api';
import { useAuthStore } from '../stores/auth';

type AuthMode = 'register' | 'login';
type LoginMethod = 'password' | 'code';
type FeedbackKind = 'info' | 'success' | 'error';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const mode = ref<AuthMode>('register');
const loginMethod = ref<LoginMethod>('password');
const registerEmail = ref('');
const registerCode = ref('');
const registerPassword = ref('');
const confirmPassword = ref('');
const cdk = ref('');
const loginEmail = ref('');
const loginPassword = ref('');
const loginCode = ref('');
const feedback = ref('');
const feedbackKind = ref<FeedbackKind>('info');
const sending = ref(false);
const submitting = ref(false);
const cooldown = ref(0);
const showRegisterPassword = ref(false);
const showConfirmPassword = ref(false);
const showLoginPassword = ref(false);

let cooldownTimer: number | undefined;

const normalizedRegisterEmail = computed(() => registerEmail.value.trim().toLowerCase());
const normalizedLoginEmail = computed(() => loginEmail.value.trim().toLowerCase());
const activeCodeEmail = computed(() => {
  if (mode.value === 'login' && loginMethod.value === 'code') {
    return normalizedLoginEmail.value;
  }
  return normalizedRegisterEmail.value;
});
const canSendCode = computed(() => isEmail(activeCodeEmail.value) && !sending.value && cooldown.value <= 0);
const canRegister = computed(() => {
  return (
    isEmail(normalizedRegisterEmail.value) &&
    /^\d{6}$/.test(registerCode.value.trim()) &&
    registerPassword.value.length >= 6 &&
    confirmPassword.value.length >= 6 &&
    registerPassword.value === confirmPassword.value &&
    !submitting.value
  );
});
const canLogin = computed(() => {
  if (!isEmail(normalizedLoginEmail.value) || submitting.value) {
    return false;
  }
  if (loginMethod.value === 'code') {
    return /^\d{6}$/.test(loginCode.value.trim());
  }
  return loginPassword.value.length > 0;
});
const sendButtonText = computed(() => {
  if (sending.value) {
    return '发送中';
  }
  if (cooldown.value > 0) {
    return `${cooldown.value}s`;
  }
  return '发验证码';
});

function switchMode(nextMode: AuthMode): void {
  if (mode.value === nextMode) {
    return;
  }
  mode.value = nextMode;
  showMessage('', 'info');
  if (nextMode === 'login' && !loginEmail.value) {
    loginEmail.value = normalizedRegisterEmail.value;
  }
  if (nextMode === 'register' && !registerEmail.value) {
    registerEmail.value = normalizedLoginEmail.value;
  }
}

function switchLoginMethod(nextMethod: LoginMethod, message = ''): void {
  if (mode.value !== 'login') {
    mode.value = 'login';
  }
  if (loginMethod.value === nextMethod) {
    if (message) {
      showMessage(message, 'info');
    }
    return;
  }
  loginMethod.value = nextMethod;
  showMessage(message, message ? 'info' : 'info');
}

async function handleSendCode(): Promise<void> {
  const targetEmail = activeCodeEmail.value;
  if (!isEmail(targetEmail)) {
    showMessage('请输入正确的邮箱地址。', 'error');
    return;
  }

  sending.value = true;
  showMessage('', 'info');

  try {
    const response = await auth.sendEmailCode(targetEmail);
    showMessage(response.message || '验证码已发送，请查看邮箱。', 'success');
    startCooldown(response.cooldown_seconds || 60);
  } catch (error) {
    showMessage(readErrorMessage(error, '验证码发送失败，请稍后再试。'), 'error');
  } finally {
    sending.value = false;
  }
}

async function handleRegister(): Promise<void> {
  if (!isEmail(normalizedRegisterEmail.value)) {
    showMessage('请输入正确的邮箱地址。', 'error');
    return;
  }
  if (!/^\d{6}$/.test(registerCode.value.trim())) {
    showMessage('请填写 6 位邮箱验证码。', 'error');
    return;
  }
  if (registerPassword.value.length < 6) {
    showMessage('密码至少需要 6 位。', 'error');
    return;
  }
  if (registerPassword.value !== confirmPassword.value) {
    showMessage('两次输入的密码不一致。', 'error');
    return;
  }

  submitting.value = true;
  showMessage('', 'info');

  try {
    const response = await auth.registerWithPassword({
      email: normalizedRegisterEmail.value,
      code: registerCode.value.trim(),
      password: registerPassword.value,
      cdk: cdk.value.trim() || undefined
    });
    showMessage(response.cdk?.message_cn || '账号创建成功，正在进入 PinDou。', response.cdk?.success === false && cdk.value.trim() ? 'info' : 'success');
    await wait(420);
    await router.replace(readRedirectPath());
  } catch (error) {
    showMessage(readErrorMessage(error, '注册失败，请检查信息后重试。'), 'error');
  } finally {
    submitting.value = false;
  }
}

async function handleLogin(): Promise<void> {
  if (!isEmail(normalizedLoginEmail.value)) {
    showMessage('请输入正确的邮箱地址。', 'error');
    return;
  }
  if (loginMethod.value === 'code' && !/^\d{6}$/.test(loginCode.value.trim())) {
    showMessage('请填写 6 位邮箱验证码。', 'error');
    return;
  }
  if (loginMethod.value === 'password' && !loginPassword.value) {
    showMessage('请输入密码。', 'error');
    return;
  }

  submitting.value = true;
  showMessage('', 'info');

  try {
    if (loginMethod.value === 'code') {
      await auth.loginWithEmail(normalizedLoginEmail.value, loginCode.value.trim());
    } else {
      await auth.loginWithPassword(normalizedLoginEmail.value, loginPassword.value);
    }
    showMessage('登录成功，正在进入 PinDou。', 'success');
    await wait(260);
    await router.replace(readRedirectPath());
  } catch (error) {
    showMessage(readErrorMessage(error, '登录失败，请稍后再试。'), 'error');
  } finally {
    submitting.value = false;
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

function showMessage(message: string, kind: FeedbackKind): void {
  feedback.value = message;
  feedbackKind.value = kind;
}

function readRedirectPath(): string {
  const redirect = route.query.redirect;
  if (typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')) {
    return redirect;
  }
  return '/upload';
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

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

onUnmounted(() => {
  if (cooldownTimer) {
    window.clearInterval(cooldownTimer);
  }
});
</script>

<template>
  <section class="login-page">
    <div class="auth-card" :class="`auth-card--${mode}`">
      <div class="auth-brand">
        <span class="auth-brand__mark" aria-hidden="true"></span>
        <div>
          <strong>PinDou 拼豆</strong>
          <span>照片变图纸，开工更轻松</span>
        </div>
      </div>

      <div class="auth-tabs" role="tablist" aria-label="登录注册切换">
        <span class="auth-tabs__indicator" :class="`auth-tabs__indicator--${mode}`" aria-hidden="true"></span>
        <button
          type="button"
          role="tab"
          :aria-selected="mode === 'register'"
          :class="{ 'is-active': mode === 'register' }"
          @click="switchMode('register')"
        >
          注册
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="mode === 'login'"
          :class="{ 'is-active': mode === 'login' }"
          @click="switchMode('login')"
        >
          登录
        </button>
      </div>

      <div class="auth-form-stage">
        <Transition name="auth-form" mode="out-in">
          <form v-if="mode === 'register'" key="register" class="auth-form auth-form--register" @submit.prevent="handleRegister">
            <div class="auth-heading">
              <p class="eyebrow">Create Account</p>
              <h1>创建你的拼豆账号</h1>
              <p>邮箱验证后即可保存作品、同步额度和兑换激活码。</p>
            </div>

            <label class="auth-field">
              <span>邮箱</span>
              <input v-model="registerEmail" type="email" inputmode="email" autocomplete="email" placeholder="you@example.com" />
            </label>

            <div class="auth-code-row">
              <label class="auth-field">
                <span>邮箱验证码</span>
                <input v-model="registerCode" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="6 位数字" />
              </label>
              <button class="code-button" type="button" :disabled="!canSendCode" @click="handleSendCode">
                {{ sendButtonText }}
              </button>
            </div>

            <label class="auth-field">
              <span>设置密码</span>
              <span class="password-wrap">
                <input
                  v-model="registerPassword"
                  :type="showRegisterPassword ? 'text' : 'password'"
                  autocomplete="new-password"
                  placeholder="至少 6 位"
                />
                <button
                  class="eye-button"
                  type="button"
                  :aria-label="showRegisterPassword ? '隐藏密码' : '显示密码'"
                  @click="showRegisterPassword = !showRegisterPassword"
                >
                  <span class="eye-icon" :class="{ 'eye-icon--hidden': !showRegisterPassword }"></span>
                </button>
              </span>
            </label>

            <label class="auth-field">
              <span>确认密码</span>
              <span class="password-wrap">
                <input
                  v-model="confirmPassword"
                  :type="showConfirmPassword ? 'text' : 'password'"
                  autocomplete="new-password"
                  placeholder="再输入一次"
                />
                <button
                  class="eye-button"
                  type="button"
                  :aria-label="showConfirmPassword ? '隐藏密码' : '显示密码'"
                  @click="showConfirmPassword = !showConfirmPassword"
                >
                  <span class="eye-icon" :class="{ 'eye-icon--hidden': !showConfirmPassword }"></span>
                </button>
              </span>
            </label>

            <label class="auth-field">
              <span>激活码 <em>可选</em></span>
              <input v-model="cdk" type="text" autocomplete="off" placeholder="填写后赠送生成次数" />
            </label>

            <p v-if="feedback" class="auth-feedback" :class="`auth-feedback--${feedbackKind}`" role="status" aria-live="polite">
              {{ feedback }}
            </p>

            <button class="auth-submit" type="submit" :disabled="!canRegister">
              {{ submitting ? '创建中...' : '创建账号' }}
            </button>
          </form>

          <form v-else key="login" class="auth-form auth-form--login" @submit.prevent="handleLogin">
            <div class="auth-heading">
              <p class="eyebrow">Welcome Back</p>
              <h1>继续你的拼豆计划</h1>
              <p>{{ loginMethod === 'code' ? '收取邮箱验证码，临时登录并找回访问权限。' : '用邮箱和密码登录，回到上次保存的作品和额度。' }}</p>
            </div>

            <label class="auth-field">
              <span>邮箱</span>
              <input v-model="loginEmail" type="email" inputmode="email" autocomplete="email" placeholder="you@example.com" />
            </label>

            <label v-if="loginMethod === 'password'" class="auth-field">
              <span>密码</span>
              <span class="password-wrap">
                <input
                  v-model="loginPassword"
                  :type="showLoginPassword ? 'text' : 'password'"
                  autocomplete="current-password"
                  placeholder="输入密码"
                />
                <button
                  class="eye-button"
                  type="button"
                  :aria-label="showLoginPassword ? '隐藏密码' : '显示密码'"
                  @click="showLoginPassword = !showLoginPassword"
                >
                  <span class="eye-icon" :class="{ 'eye-icon--hidden': !showLoginPassword }"></span>
                </button>
              </span>
            </label>

            <div v-else class="auth-code-row">
              <label class="auth-field">
                <span>邮箱验证码</span>
                <input v-model="loginCode" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="6 位数字" />
              </label>
              <button class="code-button" type="button" :disabled="!canSendCode" @click="handleSendCode">
                {{ sendButtonText }}
              </button>
            </div>

            <div class="login-options">
              <button
                v-if="loginMethod === 'password'"
                type="button"
                @click="switchLoginMethod('code')"
              >
                用验证码登录
              </button>
              <button
                v-else
                type="button"
                @click="switchLoginMethod('password')"
              >
                用密码登录
              </button>
              <button
                type="button"
                @click="switchLoginMethod('code', '用邮箱验证码登录即可找回访问权限。')"
              >
                忘记密码？
              </button>
            </div>

            <p v-if="feedback" class="auth-feedback" :class="`auth-feedback--${feedbackKind}`" role="status" aria-live="polite">
              {{ feedback }}
            </p>

            <button class="auth-submit" type="submit" :disabled="!canLogin">
              {{ submitting ? '登录中...' : '登录' }}
            </button>
          </form>
        </Transition>
      </div>

      <p class="auth-note">照片仅用于生成图纸，并按隐私策略定期删除。</p>
    </div>
  </section>
</template>

<style scoped>
.login-page {
  width: 100%;
  display: grid;
  place-items: center;
  padding: 0;
}

.auth-card {
  width: min(100%, clamp(540px, 42vw, 620px));
  min-height: 720px;
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(237, 228, 218, 0.86);
  border-radius: 30px;
  background:
    radial-gradient(circle at 86% 10%, rgba(164, 212, 197, 0.2), transparent 30%),
    radial-gradient(circle at 8% 88%, rgba(255, 176, 136, 0.2), transparent 32%),
    rgba(255, 255, 255, 0.92);
  box-shadow: 0 28px 70px rgba(255, 107, 90, 0.14), 0 10px 26px rgba(45, 45, 45, 0.06);
  padding: clamp(24px, 5vw, 36px);
  animation: card-rise 420ms var(--pd-ease-soft) both;
}

.auth-card::before {
  content: "";
  position: absolute;
  width: 156px;
  height: 156px;
  right: -70px;
  top: -72px;
  border-radius: 44% 56% 52% 48%;
  background: rgba(255, 176, 136, 0.18);
  pointer-events: none;
}

.auth-brand {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 22px;
  text-align: left;
}

.auth-brand__mark {
  width: 42px;
  height: 42px;
  position: relative;
  display: inline-grid;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 16px;
  background: var(--pd-gradient-warm);
  box-shadow: var(--pd-shadow-cta);
  transform: rotate(-5deg);
}

.auth-brand__mark::after {
  content: "";
  width: 14px;
  height: 14px;
  border-radius: var(--pd-r-full);
  background: #fff;
}

.auth-brand strong,
.auth-brand span {
  display: block;
}

.auth-brand strong {
  color: var(--pd-fg-1);
  font-size: 20px;
  font-weight: 900;
}

.auth-brand span {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 800;
}

.auth-tabs {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0;
  margin-bottom: 24px;
  border: 1px solid rgba(237, 228, 218, 0.9);
  border-radius: 18px;
  background: rgba(255, 244, 236, 0.82);
  padding: 5px;
}

.auth-tabs__indicator {
  position: absolute;
  inset: 5px auto 5px 5px;
  width: calc(50% - 5px);
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 10px 26px rgba(255, 142, 83, 0.16), 0 1px 2px rgba(45, 45, 45, 0.04);
  transition: transform 260ms var(--pd-ease-soft);
}

.auth-tabs__indicator--login {
  transform: translateX(100%);
}

.auth-tabs button {
  position: relative;
  z-index: 1;
  min-height: 42px;
  border: 0;
  border-radius: 14px;
  background: transparent;
  color: var(--pd-fg-2);
  cursor: pointer;
  font: inherit;
  font-size: 15px;
  font-weight: 900;
  transition: color var(--pd-dur-base) var(--pd-ease-out), transform var(--pd-dur-fast) var(--pd-ease-out);
}

.auth-tabs button:hover {
  transform: translateY(-1px);
}

.auth-tabs button.is-active {
  color: var(--pd-fg-1);
}

.auth-form-stage {
  position: relative;
  z-index: 1;
  min-height: 484px;
  display: grid;
  align-items: center;
}

.auth-form {
  position: relative;
  display: grid;
  gap: 14px;
  width: 100%;
}

.auth-form--register {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-self: start;
}

.auth-form--login {
  align-self: center;
  grid-template-columns: 1fr;
  gap: 16px;
  padding: 18px 0 8px;
}

.auth-form--register > .auth-heading,
.auth-form--register > .auth-field:first-of-type,
.auth-form--register > .auth-code-row,
.auth-form--register > .auth-field:last-of-type,
.auth-form--register > .auth-feedback,
.auth-form--register > .auth-submit {
  grid-column: 1 / -1;
}

.auth-heading {
  margin-bottom: 2px;
  text-align: center;
}

.auth-heading h1 {
  margin: 0 0 8px;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(28px, 5vw, 38px);
  line-height: 1.08;
  letter-spacing: 0;
}

.auth-heading p:last-child {
  margin: 0 auto;
  max-width: 360px;
  color: var(--pd-fg-2);
  font-size: 14px;
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--pd-orange);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0;
  text-transform: uppercase;
}

.auth-field {
  display: grid;
  gap: 8px;
  color: var(--pd-fg-1);
  font-size: 13px;
  font-weight: 900;
}

.auth-field em {
  color: var(--pd-fg-2);
  font-style: normal;
  font-weight: 800;
}

.auth-field input {
  width: 100%;
  min-height: 50px;
  border: 1px solid var(--pd-stroke);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--pd-fg-1);
  font: inherit;
  font-size: 16px;
  outline: none;
  padding: 0 16px;
  transition:
    border-color var(--pd-dur-base) var(--pd-ease-out),
    box-shadow var(--pd-dur-base) var(--pd-ease-out),
    transform var(--pd-dur-fast) var(--pd-ease-out);
}

.auth-field input:hover {
  border-color: rgba(255, 142, 83, 0.42);
}

.auth-field input:focus {
  border-color: var(--pd-orange);
  box-shadow: 0 0 0 4px rgba(255, 142, 83, 0.16);
  transform: translateY(-1px);
}

.auth-code-row {
  display: grid;
  grid-template-columns: 1fr 118px;
  align-items: end;
  gap: 12px;
}

.login-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: -4px;
}

.login-options button {
  border: 0;
  border-radius: 999px;
  background: rgba(255, 244, 236, 0.7);
  color: var(--pd-orange);
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 900;
  padding: 8px 12px;
  transition:
    background var(--pd-dur-base) var(--pd-ease-out),
    color var(--pd-dur-base) var(--pd-ease-out),
    transform var(--pd-dur-fast) var(--pd-ease-out),
    box-shadow var(--pd-dur-base) var(--pd-ease-out);
}

.login-options button:hover {
  background: #fff;
  color: var(--pd-coral);
  box-shadow: 0 10px 24px rgba(255, 142, 83, 0.16);
  transform: translateY(-1px);
}

.code-button {
  min-height: 50px;
  border: 1px solid rgba(255, 142, 83, 0.32);
  border-radius: 16px;
  background: var(--pd-peach-50);
  color: var(--pd-orange);
  cursor: pointer;
  font: inherit;
  font-size: 14px;
  font-weight: 900;
  transition:
    background var(--pd-dur-base) var(--pd-ease-out),
    transform var(--pd-dur-fast) var(--pd-ease-out),
    box-shadow var(--pd-dur-base) var(--pd-ease-out);
}

.code-button:hover:not(:disabled) {
  background: #fff;
  box-shadow: var(--pd-shadow-card);
  transform: translateY(-1px);
}

.password-wrap {
  position: relative;
  display: block;
}

.password-wrap input {
  padding-right: 52px;
}

.eye-button {
  width: 40px;
  height: 40px;
  position: absolute;
  right: 6px;
  top: 50%;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 12px;
  background: transparent;
  cursor: pointer;
  transform: translateY(-50%);
  transition: background var(--pd-dur-fast) var(--pd-ease-out), transform var(--pd-dur-fast) var(--pd-ease-out);
}

.eye-button:hover {
  background: var(--pd-peach-50);
  transform: translateY(-50%) scale(1.04);
}

.eye-icon {
  width: 20px;
  height: 13px;
  position: relative;
  display: block;
  border: 2px solid var(--pd-orange);
  border-radius: 999px 999px 760px 760px;
  opacity: 0.9;
}

.eye-icon::before {
  content: "";
  position: absolute;
  inset: 3px 6px;
  border-radius: var(--pd-r-full);
  background: var(--pd-orange);
}

.eye-icon::after {
  content: "";
  position: absolute;
  width: 24px;
  height: 2px;
  left: -3px;
  top: 5px;
  border-radius: var(--pd-r-full);
  background: var(--pd-orange);
  opacity: 0;
  transform: rotate(-38deg);
  transition: opacity var(--pd-dur-fast) var(--pd-ease-out);
}

.eye-icon--hidden::after {
  opacity: 1;
}

.auth-feedback {
  margin: 0;
  border-radius: 14px;
  font-size: 13px;
  font-weight: 800;
  padding: 12px 14px;
}

.auth-feedback--success {
  background: rgba(52, 199, 89, 0.12);
  color: #168538;
}

.auth-feedback--error {
  background: rgba(255, 90, 90, 0.12);
  color: #cc3d3d;
}

.auth-feedback--info {
  background: rgba(164, 212, 197, 0.17);
  color: var(--pd-fg-2);
}

.auth-submit {
  min-height: 52px;
  border: 0;
  border-radius: 16px;
  background: var(--pd-gradient);
  box-shadow: var(--pd-shadow-cta);
  color: #fff;
  cursor: pointer;
  font: inherit;
  font-size: 16px;
  font-weight: 900;
  transition:
    filter var(--pd-dur-base) var(--pd-ease-out),
    transform var(--pd-dur-fast) var(--pd-ease-out),
    box-shadow var(--pd-dur-base) var(--pd-ease-out);
}

.auth-submit:hover:not(:disabled) {
  filter: brightness(1.035);
  box-shadow: 0 18px 38px rgba(255, 142, 83, 0.34), 0 8px 20px rgba(255, 107, 90, 0.2);
  transform: translateY(-2px) scale(1.01);
}

.auth-submit:active:not(:disabled) {
  transform: translateY(0) scale(0.99);
}

.auth-submit:disabled,
.code-button:disabled {
  background: #ede5dd;
  box-shadow: none;
  color: #9b8e84;
  cursor: not-allowed;
  transform: none;
}

.auth-note {
  position: relative;
  z-index: 1;
  margin: 18px 0 0;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 800;
  text-align: center;
}

.auth-form-enter-active,
.auth-form-leave-active {
  transition: opacity 180ms var(--pd-ease-out), transform 180ms var(--pd-ease-out);
}

.auth-form-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.auth-form-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@keyframes card-rise {
  from {
    opacity: 0;
    transform: translateY(18px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (max-height: 920px) and (min-width: 721px) {
  .auth-card {
    min-height: 674px;
    border-radius: 26px;
    padding: 24px 30px;
  }

  .auth-brand {
    margin-bottom: 16px;
  }

  .auth-brand__mark {
    width: 36px;
    height: 36px;
    border-radius: 14px;
  }

  .auth-brand strong {
    font-size: 18px;
  }

  .auth-tabs {
    margin-bottom: 18px;
  }

  .auth-form-stage {
    min-height: 462px;
  }

  .auth-tabs button {
    min-height: 38px;
  }

  .auth-form {
    gap: 11px;
  }

  .auth-heading h1 {
    font-size: 32px;
  }

  .auth-heading p:last-child {
    font-size: 13px;
  }

  .auth-field {
    gap: 6px;
  }

  .auth-field input,
  .code-button {
    min-height: 46px;
  }

  .auth-submit {
    min-height: 48px;
  }

  .auth-note {
    margin-top: 14px;
  }
}

@media (max-height: 820px) and (min-width: 721px) {
  .auth-card {
    min-height: 620px;
    padding: 20px 28px;
  }

  .auth-brand {
    margin-bottom: 12px;
  }

  .auth-tabs {
    margin-bottom: 14px;
  }

  .auth-form-stage {
    min-height: 430px;
  }

  .auth-form {
    gap: 9px;
  }

  .auth-heading h1 {
    font-size: 28px;
  }

  .auth-heading p:last-child,
  .auth-note {
    display: none;
  }

  .auth-field input,
  .code-button {
    min-height: 44px;
  }

  .auth-submit {
    min-height: 46px;
  }
}

@media (max-height: 680px) and (min-width: 721px) {
  .auth-card {
    width: min(100%, 600px);
    min-height: 560px;
    padding: 20px 28px;
  }

  .auth-brand {
    margin-bottom: 12px;
  }

  .auth-tabs {
    margin-bottom: 14px;
  }

  .auth-heading h1 {
    font-size: 28px;
  }

  .auth-heading p:last-child {
    display: none;
  }

  .auth-form {
    gap: 9px;
  }

  .auth-form-stage {
    min-height: 380px;
  }

  .auth-note {
    display: none;
  }
}

@media (max-width: 640px) {
  .login-page {
    place-items: start center;
  }

  .auth-card {
    width: 100%;
    min-height: auto;
    border-radius: 24px;
    padding: 22px 18px;
  }

  .auth-form-stage {
    min-height: 0;
    align-items: start;
  }

  .auth-form--register {
    grid-template-columns: 1fr;
  }

  .auth-form--login {
    padding: 0;
  }

  .auth-form--register > * {
    grid-column: 1;
  }

  .auth-brand {
    justify-content: flex-start;
  }

  .auth-heading {
    text-align: left;
  }

  .auth-heading h1 {
    font-size: 30px;
  }

  .auth-heading p:last-child {
    margin-left: 0;
  }

  .auth-code-row {
    grid-template-columns: 1fr;
  }

  .login-options {
    align-items: stretch;
    flex-direction: column;
  }

  .code-button {
    width: 100%;
  }
}
</style>
