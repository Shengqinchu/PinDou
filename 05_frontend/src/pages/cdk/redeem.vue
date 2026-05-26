<template>
  <MiniProgramLayout title="兑换 CDK" backUrl="/pages/result/basic" :scroll="true">
    <!-- ===== Entry form ===== -->
    <section v-if="currentState === 'entry'" class="cdk" data-state="entry">
      <p class="cdk__hint">
        在小红书 / 闲鱼买到的 CDK 码，输入 <strong>18 位</strong>字母数字即可解锁
      </p>

      <div class="cdk__field">
        <label class="cdk__label" for="cdk-input">CDK 兑换码</label>
        <input
          id="cdk-input"
          type="text"
          class="cdk__input"
          :class="{ 'cdk__input--error': errorMsg, 'cdk__input--valid': isCodeValid }"
          :value="formattedCode"
          @input="handleInput"
          placeholder="XXXXXX  XXXXXX  XXXXXX"
          maxlength="22"
          autocomplete="off"
          autocapitalize="characters"
          spellcheck="false"
          inputmode="latin"
        />
        <span class="cdk__counter">{{ cleanCode.length }} / 18</span>
      </div>

      <p v-if="errorMsg" class="cdk__error">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="margin-right: 4px; display: block;">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 8v4"/>
          <path d="M12 16h.01"/>
        </svg>
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

      <div class="cdk__spacer"></div>

      <div class="help-link cdk__help" @click="handleHelp">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="1.8"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="display: block;">
          <circle cx="12" cy="12" r="10"/>
          <path d="M9.5 9.5a2.5 2.5 0 1 1 5 0c0 1.5-2.5 2-2.5 3.5"/>
          <circle cx="12" cy="17" r="0.5" fill="currentColor"/>
        </svg>
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
          <svg viewBox="0 0 60 60" width="80" height="80" aria-hidden="true">
            <circle cx="30" cy="30" r="28" fill="none" stroke="#34C759" stroke-width="2.5" opacity="0.25"/>
            <circle cx="30" cy="30" r="22" fill="#34C759"/>
            <path d="M19 30l8 8 14-16" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
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
import { useCdkStore } from '../../store/cdk';

const cdkStore = useCdkStore();

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
  
  isLoading.value = true;
  errorMsg.value = '';
  
  try {
    const result = await cdkStore.redeemCDK(cleanCode.value);
    if (result.success) {
      rewardType.value = result.type === 'monthly' ? '月卡高级特权' : '单次付费图纸';
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
  padding: 22px 22px calc(24px + constant(safe-area-inset-bottom));
  padding: 22px 22px calc(24px + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 120px);
  box-sizing: border-box;
}

.cdk__hint {
  margin: 0 0 24px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--pd-fg-2);
  text-align: center;
  
  strong {
    color: var(--pd-fg-1);
    font-weight: 700;
  }
}

.cdk__field {
  position: relative;
  margin-bottom: 6px;
}
.cdk__label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--pd-fg-2);
  letter-spacing: 0.5px;
  margin-bottom: 6px;
  text-transform: uppercase;
}
.cdk__input {
  width: 100%;
  font-family: var(--pd-font-mono);
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1.2px;
  text-align: center;
  color: var(--pd-fg-1);
  padding: 17px 12px;
  border-radius: var(--pd-r-input);
  border: 1.5px solid var(--pd-divider);
  background: #fff;
  transition: border-color 200ms var(--pd-ease-out),
              box-shadow 200ms var(--pd-ease-out);
  outline: none;
  box-sizing: border-box;
  
  &::placeholder {
    color: var(--pd-fg-3);
    font-weight: 400;
    letter-spacing: 1.5px;
  }
  &:focus {
    border-color: var(--pd-pink);
    box-shadow: 0 0 0 4px rgba(255, 107, 157, 0.12);
  }
}

.cdk__input--error {
  border-color: var(--pd-danger);
  
  &:focus {
    box-shadow: 0 0 0 4px rgba(255, 90, 90, 0.14);
  }
}

.cdk__input--valid {
  border-color: var(--pd-success);
  
  &:focus {
    box-shadow: 0 0 0 4px rgba(52, 199, 89, 0.14);
  }
}

.cdk__counter {
  position: absolute;
  right: 12px;
  bottom: -22px;
  font-family: var(--pd-font-mono);
  font-size: 11px;
  color: var(--pd-fg-3);
}

.cdk__error {
  margin: 24px 0 0;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--pd-danger);
  animation: cdk-shake 320ms var(--pd-ease-out);
  justify-content: center;
}

@keyframes cdk-shake {
  0%, 100% { transform: translateX(0); }
  20%      { transform: translateX(-4px); }
  40%      { transform: translateX(4px); }
  60%      { transform: translateX(-2px); }
  80%      { transform: translateX(2px); }
}

.cdk__submit {
  margin-top: 28px;
  
  &:disabled {
    opacity: 0.55;
    box-shadow: none;
  }
}

.cdk__spacer { 
  flex: 1; 
}

.cdk__help {
  align-self: center;
  cursor: pointer;
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

.cdk__check-ring svg {
  animation: cdk-pop 480ms var(--pd-ease-soft);
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
    letter-spacing: 0.8px;
    padding-left: 10px;
    padding-right: 10px;
  }

  .cdk__success-row {
    gap: 12px;
  }
}
</style>
