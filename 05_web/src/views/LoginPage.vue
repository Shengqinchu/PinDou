<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { ApiError } from '../api';
import { useAuthStore } from '../stores/auth';

type BeadTone = 'blank' | 'ink' | 'peach' | 'coral' | 'mint' | 'cream';

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

const beadPalette: Record<BeadTone, string> = {
  blank: '#fff7ef',
  ink: '#263238',
  peach: '#ffb084',
  coral: '#ff6b5a',
  mint: '#a4d4c5',
  cream: '#ffe2c6'
};

const sampleCards = [
  {
    title: '萌宠头像',
    caption: '52 x 52 拼豆图纸',
    rows: toBeadRows([
      '000111100000',
      '001222210000',
      '012222221000',
      '122122122100',
      '122222222100',
      '122211222100',
      '012222221000',
      '001211210000',
      '000133100000',
      '000033000000',
      '000000000000',
      '000000000000'
    ])
  },
  {
    title: '手作配色',
    caption: '干净色块和轮廓',
    rows: toBeadRows([
      '000044000000',
      '000444400000',
      '004444440000',
      '044444444000',
      '044144144000',
      '044444444000',
      '004411440000',
      '000433400000',
      '000333000000',
      '000000000000',
      '000000000000',
      '000000000000'
    ])
  }
];

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

function toBeadRows(rows: string[]): BeadTone[] {
  const toneMap: Record<string, BeadTone> = {
    '0': 'blank',
    '1': 'ink',
    '2': 'peach',
    '3': 'coral',
    '4': 'mint'
  };
  return rows.flatMap((row) => row.split('').map((value) => toneMap[value] || 'blank'));
}

onUnmounted(() => {
  if (cooldownTimer) {
    window.clearInterval(cooldownTimer);
  }
});
</script>

<template>
  <section class="login-page">
    <div class="auth-landing">
      <aside class="auth-story" aria-label="PinDou 登录说明">
        <div class="story-copy">
          <p class="eyebrow">PinDou Web</p>
          <h1>把照片变成可以开工的拼豆图纸</h1>
          <p>登录后保存作品、继续生成图纸、查看订单和额度。我们只用邮箱验证码确认是你本人。</p>
        </div>

        <div class="sample-stack" aria-label="拼豆样例">
          <article v-for="sample in sampleCards" :key="sample.title" class="sample-card">
            <div class="bead-board" aria-hidden="true">
              <span
                v-for="(cell, index) in sample.rows"
                :key="`${sample.title}-${index}`"
                class="bead-dot"
                :style="`--bead-color:${beadPalette[cell]}`"
              ></span>
            </div>
            <div>
              <strong>{{ sample.title }}</strong>
              <span>{{ sample.caption }}</span>
            </div>
          </article>
        </div>

        <ol class="flow-list" aria-label="生成流程">
          <li><span>1</span>上传照片</li>
          <li><span>2</span>AI 生成</li>
          <li><span>3</span>拿图纸开做</li>
        </ol>

        <p class="privacy-note">照片仅用于生成拼豆图纸，并按隐私策略定期删除。</p>
      </aside>

      <div class="login-card">
        <p class="eyebrow">邮箱验证码</p>
        <h2>欢迎来到 PinDou</h2>
        <p class="login-card__intro">输入邮箱接收 6 位验证码。首次验证会自动创建账号。</p>

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
            {{ verifying ? '正在进入...' : '继续生成图纸' }}
          </button>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>
.login-page {
  min-height: calc(100vh - 160px);
  display: grid;
  place-items: center;
}

.auth-landing {
  width: min(100%, 1060px);
  display: grid;
  grid-template-columns: minmax(0, 1.06fr) minmax(380px, 0.94fr);
  align-items: stretch;
  gap: clamp(22px, 4vw, 48px);
  min-width: 0;
}

.auth-story,
.login-card {
  min-width: 0;
  padding: clamp(30px, 6vw, 56px);
  border: 1px solid rgba(237, 228, 218, 0.82);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--pd-shadow-float);
}

.auth-story {
  position: relative;
  overflow: hidden;
  display: grid;
  align-content: space-between;
  gap: 24px;
  background:
    radial-gradient(circle at 84% 12%, rgba(164, 212, 197, 0.24), transparent 30%),
    linear-gradient(145deg, rgba(255, 241, 232, 0.96), rgba(255, 255, 255, 0.9));
}

.auth-story::after {
  content: "";
  position: absolute;
  width: 150px;
  height: 150px;
  right: -48px;
  bottom: -52px;
  border-radius: 48% 52% 46% 54%;
  background: rgba(255, 176, 136, 0.18);
  pointer-events: none;
}

.story-copy {
  position: relative;
  z-index: 1;
}

.story-copy h1 {
  max-width: 520px;
  margin: 0 0 14px;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(34px, 4.2vw, 56px);
  line-height: 1.08;
  letter-spacing: 0;
  overflow-wrap: anywhere;
}

.story-copy p:last-child,
.privacy-note {
  max-width: 480px;
  margin: 0;
  color: var(--pd-fg-2);
}

.sample-stack {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.sample-card {
  display: grid;
  gap: 14px;
  border: 1px solid rgba(237, 228, 218, 0.82);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.76);
  padding: 16px;
  box-shadow: var(--pd-shadow-card);
}

.sample-card strong,
.sample-card span {
  display: block;
}

.sample-card strong {
  color: var(--pd-fg-1);
  font-size: 15px;
}

.sample-card span {
  color: var(--pd-fg-2);
  font-size: 12px;
}

.bead-board {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 3px;
  aspect-ratio: 1;
  border-radius: 18px;
  background: var(--pd-bg);
  padding: 10px;
}

.bead-dot {
  aspect-ratio: 1;
  border-radius: 50%;
  background: var(--bead-color);
  box-shadow: inset 0 -1px 1px rgba(45, 45, 45, 0.08);
}

.flow-list {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.flow-list li {
  display: grid;
  gap: 8px;
  border-radius: 18px;
  background: rgba(255, 176, 136, 0.15);
  color: var(--pd-fg-1);
  font-weight: 900;
  padding: 14px;
}

.flow-list span {
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: var(--pd-r-full);
  background: var(--pd-gradient-warm);
  color: #fff;
  font-size: 12px;
}

.privacy-note {
  position: relative;
  z-index: 1;
  border-radius: 18px;
  background: rgba(164, 212, 197, 0.18);
  padding: 14px 16px;
  font-size: 13px;
  font-weight: 800;
}

.login-card {
  align-self: center;
  text-align: center;
}

.login-card h2 {
  margin: 0 0 12px;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(30px, 3.8vw, 42px);
  line-height: 1.12;
  letter-spacing: 0;
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
  letter-spacing: 0;
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
  font-size: 16px;
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
  background: #ede5dd;
  color: #9b8e84;
  box-shadow: none;
  opacity: 1;
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

  .auth-landing {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .auth-story {
    padding: 24px 20px;
    border-radius: 22px;
  }

  .story-copy h1 {
    font-size: 28px;
  }

  .sample-stack {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .sample-card {
    padding: 12px;
    border-radius: 18px;
  }

  .bead-board {
    gap: 2px;
    padding: 8px;
    border-radius: 14px;
  }

  .flow-list {
    grid-template-columns: 1fr;
  }

  .privacy-note {
    font-size: 12px;
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
