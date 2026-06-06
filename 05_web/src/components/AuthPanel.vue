<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue';

import { ApiError } from '../api';
import { useAuthStore } from '../stores/auth';

type AuthMode = 'register' | 'login';
type LoginMethod = 'password' | 'code';
type FeedbackKind = 'info' | 'success' | 'error';

const emit = defineEmits<{
  success: [];
}>();

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
const activeCodeEmail = computed(() => (
  mode.value === 'login' && loginMethod.value === 'code'
    ? normalizedLoginEmail.value
    : normalizedRegisterEmail.value
));
const canSendCode = computed(() => isEmail(activeCodeEmail.value) && !sending.value && cooldown.value <= 0);
const canRegister = computed(() => (
  isEmail(normalizedRegisterEmail.value) &&
  /^\d{6}$/.test(registerCode.value.trim()) &&
  registerPassword.value.length >= 6 &&
  confirmPassword.value.length >= 6 &&
  registerPassword.value === confirmPassword.value &&
  !submitting.value
));
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
  mode.value = 'login';
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
    showMessage(response.cdk?.message_cn || '账号创建成功，正在继续生成。', response.cdk?.success === false && cdk.value.trim() ? 'info' : 'success');
    await wait(360);
    emit('success');
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
    showMessage('登录成功，正在继续生成。', 'success');
    await wait(260);
    emit('success');
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
  <div class="auth-card" :class="`auth-card--${mode}`">
    <div class="auth-brand">
      <span class="auth-brand__mark" aria-hidden="true"></span>
      <div>
        <strong>PinDou 拼豆</strong>
        <span>登录后保存作品和额度</span>
      </div>
    </div>

    <div class="auth-tabs" role="tablist" aria-label="登录注册切换">
      <span class="auth-tabs__indicator" :class="`auth-tabs__indicator--${mode}`" aria-hidden="true"></span>
      <button type="button" role="tab" :aria-selected="mode === 'register'" :class="{ 'is-active': mode === 'register' }" @click="switchMode('register')">注册</button>
      <button type="button" role="tab" :aria-selected="mode === 'login'" :class="{ 'is-active': mode === 'login' }" @click="switchMode('login')">登录</button>
    </div>

    <Transition name="auth-form" mode="out-in">
      <form v-if="mode === 'register'" key="register" class="auth-form" @submit.prevent="handleRegister">
        <div class="auth-heading">
          <h1>创建你的拼豆账号</h1>
          <p>邮箱验证后即可生成图纸、保存作品和同步额度。</p>
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
          <button class="code-button" type="button" :disabled="!canSendCode" @click="handleSendCode">{{ sendButtonText }}</button>
        </div>

        <label class="auth-field">
          <span>设置密码</span>
          <span class="password-wrap">
            <input v-model="registerPassword" :type="showRegisterPassword ? 'text' : 'password'" autocomplete="new-password" placeholder="至少 6 位" />
            <button class="eye-button" type="button" :aria-label="showRegisterPassword ? '隐藏密码' : '显示密码'" @click="showRegisterPassword = !showRegisterPassword">
              <span class="eye-icon" :class="{ 'eye-icon--hidden': !showRegisterPassword }"></span>
            </button>
          </span>
        </label>

        <label class="auth-field">
          <span>确认密码</span>
          <span class="password-wrap">
            <input v-model="confirmPassword" :type="showConfirmPassword ? 'text' : 'password'" autocomplete="new-password" placeholder="再输入一次" />
            <button class="eye-button" type="button" :aria-label="showConfirmPassword ? '隐藏密码' : '显示密码'" @click="showConfirmPassword = !showConfirmPassword">
              <span class="eye-icon" :class="{ 'eye-icon--hidden': !showConfirmPassword }"></span>
            </button>
          </span>
        </label>

        <label class="auth-field">
          <span>CDK 可选</span>
          <input v-model="cdk" type="text" autocomplete="off" placeholder="有兑换码可填" />
        </label>

        <p v-if="feedback" class="auth-feedback" :class="`auth-feedback--${feedbackKind}`" role="status" aria-live="polite">{{ feedback }}</p>
        <button class="auth-submit" type="submit" :disabled="!canRegister">{{ submitting ? '注册中' : '注册并继续' }}</button>
      </form>

      <form v-else key="login" class="auth-form" @submit.prevent="handleLogin">
        <div class="auth-heading">
          <h1>欢迎回来</h1>
          <p>{{ loginMethod === 'code' ? '收取邮箱验证码，临时登录并继续生成。' : '用邮箱和密码登录，继续刚才的生成。' }}</p>
        </div>

        <label class="auth-field">
          <span>邮箱</span>
          <input v-model="loginEmail" type="email" inputmode="email" autocomplete="email" placeholder="you@example.com" />
        </label>

        <label v-if="loginMethod === 'password'" class="auth-field">
          <span>密码</span>
          <span class="password-wrap">
            <input v-model="loginPassword" :type="showLoginPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="输入密码" />
            <button class="eye-button" type="button" :aria-label="showLoginPassword ? '隐藏密码' : '显示密码'" @click="showLoginPassword = !showLoginPassword">
              <span class="eye-icon" :class="{ 'eye-icon--hidden': !showLoginPassword }"></span>
            </button>
          </span>
        </label>

        <div v-else class="auth-code-row">
          <label class="auth-field">
            <span>邮箱验证码</span>
            <input v-model="loginCode" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="6 位数字" />
          </label>
          <button class="code-button" type="button" :disabled="!canSendCode" @click="handleSendCode">{{ sendButtonText }}</button>
        </div>

        <div class="login-options">
          <button v-if="loginMethod === 'password'" type="button" @click="switchLoginMethod('code', '验证码已切换到登录邮箱。')">验证码登录</button>
          <button v-else type="button" @click="switchLoginMethod('password')">密码登录</button>
        </div>

        <p v-if="feedback" class="auth-feedback" :class="`auth-feedback--${feedbackKind}`" role="status" aria-live="polite">{{ feedback }}</p>
        <button class="auth-submit" type="submit" :disabled="!canLogin">{{ submitting ? '登录中' : '登录并继续' }}</button>
      </form>
    </Transition>

    <p class="auth-note">照片仅用于生成图纸，并按隐私策略定期删除。</p>
  </div>
</template>

<style scoped>
.auth-card {
  position: relative;
  width: min(100%, 520px);
  display: grid;
  gap: 18px;
  overflow: hidden;
  border: 1px solid rgba(237, 228, 218, 0.86);
  border-radius: 30px;
  background:
    radial-gradient(circle at 16% 0%, rgba(255, 176, 136, 0.2), transparent 34%),
    rgba(255, 255, 255, 0.94);
  box-shadow: var(--pd-shadow-float);
  padding: clamp(20px, 4vw, 30px);
}

.auth-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.auth-brand__mark {
  width: 42px;
  height: 42px;
  border-radius: 15px;
  background: center / contain no-repeat url("/brand/logo.png"), rgba(255, 241, 232, 0.82);
  box-shadow: 0 12px 24px rgba(255, 142, 83, 0.14);
}

.auth-brand strong,
.auth-brand span {
  display: block;
}

.auth-brand strong {
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: 22px;
  line-height: 1;
}

.auth-brand span {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
}

.auth-tabs {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  border: 1px solid rgba(255, 142, 83, 0.18);
  border-radius: 999px;
  background: rgba(255, 241, 232, 0.64);
  padding: 4px;
}

.auth-tabs__indicator {
  position: absolute;
  inset: 4px auto 4px 4px;
  width: calc(50% - 4px);
  border-radius: 999px;
  background: #fff;
  box-shadow: 0 10px 22px rgba(255, 142, 83, 0.12);
  transition: transform 180ms var(--pd-ease-out);
}

.auth-tabs__indicator--login {
  transform: translateX(100%);
}

.auth-tabs button,
.code-button,
.eye-button,
.login-options button,
.auth-submit {
  cursor: pointer;
  font: inherit;
  font-weight: 900;
}

.auth-tabs button {
  position: relative;
  z-index: 1;
  min-height: 40px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--pd-fg-2);
}

.auth-tabs button.is-active {
  color: var(--pd-orange);
}

.auth-form {
  display: grid;
  gap: 13px;
}

.auth-heading {
  display: grid;
  gap: 5px;
}

.auth-heading h1 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(28px, 6vw, 38px);
  line-height: 1;
}

.auth-heading p,
.auth-note {
  margin: 0;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
  line-height: 1.5;
}

.auth-field {
  display: grid;
  gap: 6px;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
}

.auth-field input {
  width: 100%;
  min-height: 46px;
  border: 1px solid var(--pd-stroke);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.94);
  color: var(--pd-fg-1);
  font: inherit;
  font-weight: 900;
  outline: none;
  padding: 0 14px;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out);
}

.auth-field input:focus {
  border-color: rgba(255, 142, 83, 0.58);
  box-shadow: 0 0 0 4px rgba(255, 142, 83, 0.12);
}

.auth-code-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 10px;
}

.password-wrap {
  position: relative;
  display: block;
}

.password-wrap input {
  padding-right: 46px;
}

.eye-button {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 12px;
  background: rgba(255, 241, 232, 0.78);
}

.eye-icon {
  width: 16px;
  height: 16px;
  display: block;
  margin: auto;
  border: 2px solid var(--pd-orange);
  border-radius: 999px 999px 8px 8px;
  transform: rotate(45deg);
}

.eye-icon--hidden {
  opacity: 0.42;
}

.code-button,
.auth-submit {
  min-height: 46px;
  border: 0;
  border-radius: 16px;
  background: var(--pd-gradient-warm);
  color: #fff;
  padding: 0 16px;
  box-shadow: var(--pd-shadow-cta);
  transition:
    opacity 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out);
}

.code-button:hover:not(:disabled),
.auth-submit:hover:not(:disabled) {
  box-shadow: 0 16px 28px rgba(255, 142, 83, 0.24);
  transform: translateY(-1px);
}

.code-button:disabled,
.auth-submit:disabled {
  cursor: not-allowed;
  opacity: 0.5;
  transform: none;
}

.login-options {
  display: flex;
  justify-content: flex-end;
}

.login-options button {
  border: 0;
  background: transparent;
  color: var(--pd-orange);
}

.auth-feedback {
  margin: 0;
  border-radius: 14px;
  font-size: 12px;
  font-weight: 900;
  padding: 10px 12px;
}

.auth-feedback--success {
  background: rgba(133, 200, 150, 0.14);
  color: #438b57;
}

.auth-feedback--error {
  background: rgba(255, 90, 90, 0.12);
  color: #c74242;
}

.auth-feedback--info {
  background: rgba(255, 241, 232, 0.82);
  color: var(--pd-orange);
}

.auth-submit {
  width: 100%;
}

.auth-note {
  text-align: center;
}

.auth-form-enter-active,
.auth-form-leave-active {
  transition: opacity 150ms var(--pd-ease-out), transform 150ms var(--pd-ease-out);
}

.auth-form-enter-from,
.auth-form-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (max-width: 520px) {
  .auth-card {
    border-radius: 24px;
    padding: 18px;
  }

  .auth-code-row {
    grid-template-columns: 1fr;
  }
}
</style>
