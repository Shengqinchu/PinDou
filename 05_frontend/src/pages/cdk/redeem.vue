<template>
  <MiniProgramLayout title="兑换 CDK" backUrl="/pages/result/basic" :scroll="true">
    <!-- ===== Entry form ===== -->
    <section v-if="currentState === 'entry'" class="cdk" data-state="entry">
      <p class="cdk__hint">
        输入 18 位 CDK 码即可解锁
      </p>

      <div class="cdk__field">
        <label class="cdk__label" for="cdk-input">CDK 兑换码</label>
        <div
          class="cdk__input-shell"
          :class="{ 'cdk__input-shell--error': errorMsg, 'cdk__input-shell--valid': isCodeValid }"
        >
          <input
            id="cdk-input"
            type="text"
            class="cdk__input"
            :value="cleanCode"
            @input="handleInput"
            placeholder="请输入 18 位兑换码"
            placeholder-class="cdk__input-placeholder"
            maxlength="18"
            confirm-type="done"
            :adjust-position="true"
            :cursor-spacing="28"
          />
        </div>
        <div class="cdk__field-meta">
          <span class="cdk__format-preview">{{ formattedCode || 'XXXXXX XXXXXX XXXXXX' }}</span>
          <span class="cdk__counter">{{ cleanCode.length }} / 18</span>
        </div>
      </div>

      <p v-if="errorMsg" class="cdk__error">
        <span class="cdk__error-icon" aria-hidden="true">!</span>
        <span>{{ errorMsg }}</span>
      </p>

      <button 
        type="button" 
        class="btn btn--primary btn--block btn--lg cdk__submit"
        :disabled="!isCodeValid || isLoading"
        @click="handleRedeem"
      >
        {{ isLoading ? '兑换中...' : '兑换' }}
      </button>

      <div class="help-link cdk__help" @click="handleHelp">
        <span class="cdk__help-icon" aria-hidden="true">?</span>
        <span class="help-link__label">CDK 在哪买？</span>
      </div>
    </section>

    <!-- ===== Success state ===== -->
    <section v-else class="cdk__success" data-state="success">
      <div class="cdk__success-burst" aria-hidden="true">
        <!-- 自动播放的 6 个爆破礼花点 -->
        <span class="cdk__dot cdk__dot--1"></span>
        <span class="cdk__dot cdk__dot--2"></span>
        <span class="cdk__dot cdk__dot--3"></span>
        <span class="cdk__dot cdk__dot--4"></span>
        <span class="cdk__dot cdk__dot--5"></span>
        <span class="cdk__dot cdk__dot--6"></span>

        <div class="cdk__check-ring">
          <span class="cdk__check-mark" aria-hidden="true">✓</span>
        </div>
      </div>

      <h2 class="cdk__success-title">兑换成功</h2>
      <div class="card cdk__success-card">
        <div class="cdk__success-row">
          <span class="cdk__success-key">已为你添加</span>
          <span class="cdk__success-val text-grad">{{ rewardType }}</span>
        </div>
        <div class="cdk__success-row">
          <span class="cdk__success-key">有效期</span>
          <span class="cdk__success-val">{{ rewardExpires }}</span>
        </div>
        <div class="cdk__success-row">
          <span class="cdk__success-key">兑换码</span>
          <span class="cdk__success-val cdk__success-val--mono">{{ formattedCode }}</span>
        </div>
      </div>

      <div class="cdk__success-actions">
        <button class="btn btn--primary btn--block btn--lg" @click="handleGoToPremium">
          去看高级图纸
        </button>
        <button class="btn btn--secondary btn--block btn--md" @click="handleGoHome">
          回首页
        </button>
      </div>
    </section>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';
import { useCDKStore } from '../../store/cdk';
import { useUserStore } from '../../store/user';

const cdkStore = useCDKStore();
const userStore = useUserStore();

const currentState = ref<'entry' | 'success'>('entry');
const cleanCode = ref('');
const errorMsg = ref('');
const isLoading = ref(false);

const rewardType = ref('月卡');
const rewardExpires = ref('30 天无限解锁');

const isCodeValid = computed(() => cleanCode.value.length === 18);

const formattedCode = computed(() => {
  // 每 6 个字符追加两个空格
  const matches = cleanCode.value.match(/.{1,6}/g);
  return matches ? matches.join('  ') : '';
});

const handleInput = (e: any) => {
  const inputVal = e.detail.value || '';
  // 滤除非字母数字字符并转为大写，截断至 18 位
  const cleaned = inputVal.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 18);
  cleanCode.value = cleaned;
  
  // 输入时清空错误状态
  errorMsg.value = '';
};

const handleRedeem = async () => {
  if (!isCodeValid.value) return;
  if (!userStore.requireH5Login('/pages/cdk/redeem')) return;
  
  isLoading.value = true;
  errorMsg.value = '';
  
  try {
    const result = await cdkStore.redeem(cleanCode.value);
    if (result.success) {
      rewardType.value = result.cdk_type === 'monthly_card' ? '月卡高级特权' : '单次付费图纸';
      rewardExpires.value = result.expires_at 
        ? `到期日: ${result.expires_at.slice(0, 10)}` 
        : '永久有效';
        
      currentState.value = 'success';
    } else {
      errorMsg.value = '该兑换码已失效或已使用';
    }
  } catch (err: any) {
    // 捕获 API 契约中的报错
    errorMsg.value = err.message || '网络连接异常，请稍后再试';
  } finally {
    isLoading.value = false;
  }
};

const handleHelp = () => {
  uni.showModal({
    title: 'CDK 购买指引',
    content: '您可以通过在小红书、闲鱼等社区搜索“PinDou 拼豆 CDK”或“拼豆图纸兑换码”购买高级激活卡密，购买后将获得一串 18 位不区分大小写的专属兑换字符，在此输入即可立即开通畅享无阻下载特权。',
    showCancel: false,
    confirmText: '我知道了',
    confirmColor: '#FF6B9D'
  });
};

const handleGoToPremium = () => {
  uni.redirectTo({
    url: '/pages/result/premium'
  });
};

const handleGoHome = () => {
  uni.reLaunch({
    url: '/pages/index/index'
  });
};
</script>

<style scoped lang="scss">
.cdk {
  padding: 20px 22px calc(28px + constant(safe-area-inset-bottom));
  padding: 20px 22px calc(28px + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 112px);
  box-sizing: border-box;
}

.cdk__hint {
  width: 100%;
  margin: 0 0 22px;
  font-size: 14px;
  line-height: 1.45;
  color: var(--pd-fg-2);
  text-align: center;
  white-space: normal;
  
  strong {
    color: var(--pd-fg-1);
    font-weight: 700;
  }
}

.cdk__field {
  width: 100%;
  margin-bottom: 0;
}
.cdk__label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--pd-fg-2);
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.cdk__input-shell {
  width: 100%;
  height: 48px;
  min-height: 48px;
  border-radius: var(--pd-r-input);
  border: 1.5px solid var(--pd-divider);
  background: #fff;
  transition: border-color 200ms var(--pd-ease-out),
              box-shadow 200ms var(--pd-ease-out);
  box-sizing: border-box;
  overflow: hidden;
  display: flex;
  align-items: center;
  padding: 0 14px;
}

.cdk__input-shell--error {
  border-color: var(--pd-danger);
}

.cdk__input-shell--valid {
  border-color: var(--pd-success);
}

.cdk__input {
  width: 100%;
  height: 46px;
  line-height: 46px;
  min-height: 46px;
  font-family: Menlo, Consolas, monospace;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 1px;
  text-align: center;
  color: var(--pd-fg-1);
  background: transparent;
  border: 0;
  outline: none;
  padding: 0;
  box-sizing: border-box;
}

:global(.cdk__input-placeholder) {
  color: #B7B0B5;
  font-size: 14px;
  font-weight: 400;
  letter-spacing: 0;
}

.cdk__field-meta {
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 2px 0;
  box-sizing: border-box;
}

.cdk__format-preview {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: Menlo, Consolas, monospace;
  font-size: 11px;
  color: var(--pd-fg-3);
  letter-spacing: 0.6px;
}

.cdk__counter {
  flex: 0 0 auto;
  font-family: Menlo, Consolas, monospace;
  font-size: 11px;
  color: var(--pd-fg-3);
  white-space: nowrap;
}

.cdk__error {
  margin: 14px 0 0;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--pd-danger);
  animation: cdk-shake 320ms var(--pd-ease-out);
  justify-content: center;
}

.cdk__error-icon,
.cdk__help-icon {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 1.5px solid currentColor;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 800;
  line-height: 1;
}

.cdk__help-icon {
  color: var(--pd-fg-2);
}

@keyframes cdk-shake {
  0%, 100% { transform: translateX(0); }
  20%      { transform: translateX(-4px); }
  40%      { transform: translateX(4px); }
  60%      { transform: translateX(-2px); }
  80%      { transform: translateX(2px); }
}

.cdk__submit {
  margin-top: 18px;
  
  &:disabled {
    opacity: 0.55;
    box-shadow: none;
  }
}

.cdk__help {
  align-self: center;
  cursor: pointer;
  margin-top: 28px;
  margin-bottom: 0;
}

/* ===== Success state ===== */
.cdk__success {
  padding: 28px 22px calc(24px + constant(safe-area-inset-bottom));
  padding: 28px 22px calc(24px + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: calc(100vh - 120px);
  box-sizing: border-box;
}

.cdk__success-burst {
  width: 140px;
  height: 140px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 6px;
}

.cdk__check-ring {
  width: 80px;
  height: 80px;
  border-radius: 999px;
  background: rgba(52, 199, 89, 0.16);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: cdk-pop 480ms var(--pd-ease-soft);
}

.cdk__check-mark {
  width: 56px;
  height: 56px;
  border-radius: 999px;
  background: #34C759;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 34px;
  font-weight: 800;
  line-height: 1;
}

@keyframes cdk-pop {
  0%   { transform: scale(0.4); opacity: 0; }
  60%  { transform: scale(1.12); opacity: 1; }
  100% { transform: scale(1); opacity: 1; }
}

.cdk__dot {
  position: absolute;
  border-radius: 999px;
  opacity: 0;
  animation: cdk-dot 720ms var(--pd-ease-soft) forwards;
}
.cdk__dot--1 { top: 8%;  left: 50%; width: 6px;  height: 6px; background: #FF6B9D; animation-delay: 180ms; --tx:0px;   --ty:-30px; }
.cdk__dot--2 { top: 28%; left: 90%; width: 5px;  height: 5px; background: #FFB088; animation-delay: 220ms; --tx:24px;  --ty:-12px; }
.cdk__dot--3 { top: 72%; left: 88%; width: 4px;  height: 4px; background: #FFE5A0; animation-delay: 280ms; --tx:22px;  --ty:18px; }
.cdk__dot--4 { top: 90%; left: 50%; width: 6px;  height: 6px; background: #B8E6C9; animation-delay: 200ms; --tx:0px;   --ty:30px; }
.cdk__dot--5 { top: 70%; left: 8%;  width: 5px;  height: 5px; background: #FFB6C1; animation-delay: 260ms; --tx:-22px; --ty:18px; }
.cdk__dot--6 { top: 26%; left: 10%; width: 4px;  height: 4px; background: #FFCDA6; animation-delay: 240ms; --tx:-24px; --ty:-14px; }

@keyframes cdk-dot {
  0%   { transform: translate(0,0)             scale(0.5); opacity: 0; }
  40%  { transform: translate(0,0)             scale(1);   opacity: 1; }
  100% { transform: translate(var(--tx),var(--ty)) scale(1); opacity: 0; }
}

.cdk__success-title {
  margin: 6px 0 18px;
  font-family: var(--pd-font-display);
  font-size: 22px;
  font-weight: 800;
  color: var(--pd-fg-1);
  letter-spacing: -0.01em;
}

.cdk__success-card {
  width: 100%;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cdk__success-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
}
.cdk__success-key { 
  color: var(--pd-fg-2); 
}
.cdk__success-val { 
  color: var(--pd-fg-1); 
  font-weight: 600; 
}
.cdk__success-val--mono {
  font-family: var(--pd-font-mono);
  font-size: 12px;
  font-weight: 500;
  color: var(--pd-fg-2);
  max-width: 62%;
  text-align: right;
  overflow-wrap: anywhere;
}

.cdk__success-actions {
  width: 100%;
  margin-top: auto;
  padding-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

@media (max-width: 360px) {
  .cdk,
  .cdk__success {
    padding-left: 16px;
    padding-right: 16px;
  }

  .cdk__hint {
    font-size: 12px;
  }

  .cdk__input {
    font-size: 16px;
    letter-spacing: 0.4px;
  }

  .cdk__format-preview {
    font-size: 10px;
    letter-spacing: 0.2px;
  }

  .cdk__success-row {
    gap: 12px;
  }
}
</style>
