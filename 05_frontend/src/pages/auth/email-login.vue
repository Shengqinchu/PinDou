<template>
  <MiniProgramLayout title="登录 / 注册" :backUrl="backUrl" :scroll="true">
    <section class="email-login">
      <div class="email-login__card">
        <div class="email-login__badge" aria-hidden="true">PD</div>
        <h1 class="email-login__title">用邮箱登录 PinDou</h1>
        <p class="email-login__subtitle">首次验证即自动注册，后续用同一个邮箱继续查看作品和订单。</p>

        <label class="email-login__field">
          <span class="email-login__label">邮箱</span>
          <input
            v-model="email"
            class="email-login__input"
            type="email"
            inputmode="email"
            autocomplete="email"
            placeholder="you@example.com"
            placeholder-class="email-login__placeholder"
          />
        </label>

        <div class="email-login__code-row">
          <label class="email-login__field email-login__field--code">
            <span class="email-login__label">验证码</span>
            <input
              v-model="code"
              class="email-login__input email-login__input--code"
              type="text"
              inputmode="numeric"
              maxlength="6"
              autocomplete="one-time-code"
              placeholder="6 位数字"
              placeholder-class="email-login__placeholder"
            />
          </label>
          <button
            type="button"
            class="email-login__send"
            :disabled="sending || cooldown > 0"
            @click="handleSendCode"
          >
            {{ sendButtonText }}
          </button>
        </div>

        <button
          type="button"
          class="btn btn--primary btn--block btn--lg email-login__submit"
          :disabled="verifying || !canSubmit"
          @click="handleVerify"
        >
          {{ verifying ? '登录中...' : '登录 / 注册' }}
        </button>

        <p v-if="message" class="email-login__message" :class="`email-login__message--${messageTone}`">
          {{ message }}
        </p>
      </div>
    </section>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';
import { useUserStore } from '../../store/user';

const userStore = useUserStore();

const email = ref('');
const code = ref('');
const redirect = ref('/pages/user/me');
const sending = ref(false);
const verifying = ref(false);
const cooldown = ref(0);
const message = ref('');
const messageTone = ref<'info' | 'success' | 'error'>('info');
let cooldownTimer: ReturnType<typeof setInterval> | null = null;

const backUrl = computed(() => redirect.value || '/pages/index/index');
const normalizedEmail = computed(() => email.value.trim().toLowerCase());
const canSubmit = computed(() => /^\d{6}$/.test(code.value.trim()) && isValidEmail(normalizedEmail.value));
const sendButtonText = computed(() => {
  if (sending.value) return '发送中';
  if (cooldown.value > 0) return `${cooldown.value}s`;
  return '发验证码';
});

onLoad((options: any) => {
  // #ifdef MP-WEIXIN
  uni.redirectTo({url:'/pages/auth/studio-login'});
  return;
  // #endif
  if (options.redirect) {
    redirect.value = decodeURIComponent(options.redirect);
  }
});

const handleSendCode = async () => {
  message.value = '';
  if (!isValidEmail(normalizedEmail.value)) {
    showMessage('请输入正确的邮箱地址。', 'error');
    return;
  }

  sending.value = true;
  try {
    const result = await userStore.sendEmailCode(normalizedEmail.value);
    showMessage(result.message || '验证码已发送，请查收邮箱。', 'success');
    startCooldown(result.cooldown_seconds || 60);
  } catch (error: any) {
    showMessage(error?.message || '验证码发送失败，请稍后再试。', 'error');
  } finally {
    sending.value = false;
  }
};

const handleVerify = async () => {
  if (!canSubmit.value) {
    showMessage('请填写邮箱和 6 位验证码。', 'error');
    return;
  }

  verifying.value = true;
  try {
    await userStore.loginWithEmail(normalizedEmail.value, code.value.trim());
    showMessage('登录成功。', 'success');
    uni.showToast({ title: '登录成功', icon: 'success' });
    setTimeout(navigateAfterLogin, 250);
  } catch (error: any) {
    showMessage(error?.message || '验证码不正确或已过期。', 'error');
  } finally {
    verifying.value = false;
  }
};

const navigateAfterLogin = () => {
  const target = redirect.value || '/pages/user/me';
  if (isTabPage(target)) {
    uni.switchTab({ url: target.split('?')[0] });
    return;
  }
  uni.redirectTo({
    url: target,
    fail: () => uni.reLaunch({ url: '/pages/index/index' })
  });
};

const startCooldown = (seconds: number) => {
  cooldown.value = seconds;
  if (cooldownTimer) {
    clearInterval(cooldownTimer);
  }
  cooldownTimer = setInterval(() => {
    cooldown.value = Math.max(0, cooldown.value - 1);
    if (cooldown.value <= 0 && cooldownTimer) {
      clearInterval(cooldownTimer);
      cooldownTimer = null;
    }
  }, 1000);
};

const showMessage = (text: string, tone: 'info' | 'success' | 'error') => {
  message.value = text;
  messageTone.value = tone;
};

const isValidEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

const isTabPage = (url: string) => {
  const path = url.split('?')[0];
  return ['/pages/index/index', '/pages/artwork/list', '/pages/user/me'].includes(path);
};

onUnmounted(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer);
  }
});
</script>

<style scoped lang="scss">
.email-login {
  min-height: calc(100vh - 96px);
  padding: 28px 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.email-login__card {
  width: 100%;
  max-width: 420px;
  padding: 24px 22px 22px;
  border-radius: 24px;
  background: rgba(255, 250, 240, 0.96);
  border: 1px solid rgba(229, 229, 229, 0.82);
  box-shadow: 0 18px 48px rgba(255, 142, 83, 0.14);
}

.email-login__badge {
  width: 44px;
  height: 44px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--pd-peach, #ffb084), #ff6b5a);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  box-shadow: 0 12px 28px rgba(255, 107, 90, 0.22);
}

.email-login__title {
  margin: 18px 0 8px;
  font-family: var(--pd-font-display);
  font-size: 24px;
  line-height: 1.18;
  color: var(--pd-fg-1);
}

.email-login__subtitle {
  margin: 0 0 22px;
  font-size: 13px;
  line-height: 1.65;
  color: var(--pd-fg-2);
}

.email-login__field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  width: 100%;
}

.email-login__field--code {
  flex: 1;
  min-width: 0;
}

.email-login__label {
  font-size: 12px;
  font-weight: 700;
  color: var(--pd-fg-2);
}

.email-login__input {
  width: 100%;
  height: 48px;
  border: 1.5px solid var(--pd-divider);
  border-radius: 14px;
  background: #fff;
  padding: 0 14px;
  color: var(--pd-fg-1);
  font-size: 16px;
  outline: none;
}

.email-login__input--code {
  letter-spacing: 2px;
  font-weight: 800;
}

:global(.email-login__placeholder) {
  color: #b7b0b5;
  font-size: 14px;
  letter-spacing: 0;
  font-weight: 400;
}

.email-login__code-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  margin-top: 16px;
}

.email-login__send {
  flex: 0 0 104px;
  height: 48px;
  border: 0;
  border-radius: 14px;
  background: var(--pd-bg-warm);
  color: var(--pd-pink-deep);
  font-size: 13px;
  font-weight: 800;
  padding: 0;
}

.email-login__send:disabled {
  color: var(--pd-fg-3);
  opacity: 0.78;
}

.email-login__submit {
  margin-top: 22px;
}

.email-login__message {
  margin: 14px 0 0;
  font-size: 13px;
  line-height: 1.5;
}

.email-login__message--success {
  color: var(--pd-success);
}

.email-login__message--error {
  color: var(--pd-danger);
}

.email-login__message--info {
  color: var(--pd-fg-2);
}

/* #ifdef H5 */
@media (min-width: 1024px) {
  .email-login {
    min-height: calc(100vh - 180px);
    padding: 60px 20px;
  }
}
/* #endif */
</style>
