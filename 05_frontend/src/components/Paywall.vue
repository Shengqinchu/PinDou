<template>
  <div class="paywall-overlay" @click.self="handleClose">
    <transition name="sheet">
      <!-- ===== Sheet: plan-selection state ===== -->
      <section v-if="currentState === 'plans'" class="paywall__sheet" data-state="plans" @click.stop>
        <div class="paywall__handle" @click="handleClose" aria-hidden="true"></div>

        <header class="paywall__head">
          <h2 class="paywall__title">升级解锁高级图纸</h2>
          <p class="paywall__subtitle">PDF 图纸 · Excel 色号 · 分区拼接图 · 打印 · 邮件</p>
        </header>

        <ul class="paywall__plans" role="list">
          <li 
            class="paywall__plan" 
            :class="{ 'paywall__plan--active': selectedPlan === 'single' }"
            @click.stop="selectSku('single')"
          >
            <div class="paywall__plan-label">单次</div>
            <div class="paywall__plan-price">¥9.9</div>
            <div class="paywall__plan-meta">解锁本张</div>
          </li>

          <li 
            class="paywall__plan paywall__plan--recommended" 
            :class="{ 'paywall__plan--active': selectedPlan === 'monthly' }"
            @click.stop="selectSku('monthly')"
          >
            <span class="paywall__plan-badge">推荐</span>
            <div class="paywall__plan-label">月卡</div>
            <div class="paywall__plan-price text-grad">¥28</div>
            <div class="paywall__plan-meta">本月无限</div>
          </li>

          <li 
            class="paywall__plan" 
            :class="{ 'paywall__plan--active': selectedPlan === 'artisan' }"
            @click.stop="selectSku('artisan')"
          >
            <div class="paywall__plan-label">人工精修</div>
            <div class="paywall__plan-price">¥99<span class="paywall__plan-price-sub">起</span></div>
            <div class="paywall__plan-meta">设计师调色</div>
          </li>
        </ul>

        <button 
          type="button" 
          class="btn btn--primary btn--block btn--lg paywall__cta" 
          :disabled="isLoading"
          @click.stop="handleShowQR"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="margin-right: 4px; display: block;">
            <rect x="3" y="3" width="7" height="7" rx="1"/>
            <rect x="14" y="3" width="7" height="7" rx="1"/>
            <rect x="3" y="14" width="7" height="7" rx="1"/>
            <path d="M14 14h3v3h-3z M19 14h2 M14 19h2 M19 17v4"/>
          </svg>
          {{ isLoading ? '正在生成订单...' : ctaText }}
        </button>

        <navigator class="paywall__cdk" url="/pages/cdk/redeem" @click.stop>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="1.8"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="margin-right: 4px; display: block;">
            <path d="M21 7v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7"/>
            <path d="M3 7l9 6 9-6"/>
            <path d="M3 7l9-4 9 4"/>
          </svg>
          我有 CDK 兑换码
        </navigator>
      </section>

      <!-- ===== Sheet: QR-payment state ===== -->
      <section v-else class="paywall__sheet paywall__sheet--qr" data-state="qr" @click.stop>
        <div class="paywall__handle" aria-hidden="true"></div>

        <header class="paywall__head">
          <h2 class="paywall__title">{{ qrTitle }}</h2>
          <p class="paywall__subtitle">{{ qrSubtitle }}</p>
        </header>

        <div class="paywall__qr-wrap">
          <image class="paywall__qr-code" :src="qrUrl" mode="aspectFit" :show-menu-by-longpress="true" />
          <div v-if="showQrOverlay" class="paywall__qr-overlay" aria-hidden="true">
            <div class="paywall__qr-overlay-inner">
              <span class="paywall__qr-overlay-dot"></span>
              <span class="paywall__qr-overlay-text">PD</span>
            </div>
          </div>
        </div>

        <dl class="paywall__order">
          <div class="paywall__order-row">
            <dt class="paywall__order-label">订单号</dt>
            <dd class="paywall__order-value">{{ orderId }}</dd>
          </div>
          <div class="paywall__order-row">
            <dt class="paywall__order-label">套餐</dt>
            <dd class="paywall__order-value">{{ planNameText }}</dd>
          </div>
          <div v-if="currentState === 'hupijiao_qr'" class="paywall__order-row">
            <dt class="paywall__order-label">状态</dt>
            <dd class="paywall__order-value">{{ pollingText }}</dd>
          </div>
        </dl>

        <p class="paywall__qr-hint">
          {{ qrHint }}
        </p>

        <button
          v-if="currentState === 'hupijiao_qr'"
          type="button"
          class="btn btn--secondary btn--block btn--md paywall__back"
          :disabled="isLoading"
          @click.stop="handleCustomerServiceFallback"
        >
          换种付款方式
        </button>

        <button type="button" class="btn btn--secondary btn--block btn--md paywall__back" @click.stop="backToPlans">
          返回选择套餐
        </button>
      </section>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue';
import { usePaymentStore } from '../store/payment';
import { useUserStore } from '../store/user';

const props = defineProps({
  artworkId: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['close']);

const paymentStore = usePaymentStore();
const userStore = useUserStore();

const currentState = ref<'plans' | 'hupijiao_qr' | 'customer_service_qr'>('plans');
const selectedPlan = ref<'single' | 'monthly' | 'artisan'>('monthly'); // 推荐月卡默认
const isLoading = ref(false);

const orderId = ref('');
const qrUrl = ref('/static/assets/qr-placeholder.svg'); // fallback placeholder
const pollingText = ref('等待付款中');
let pollTimer: ReturnType<typeof setInterval> | null = null;
let pollAttempts = 0;

const planNameText = computed(() => {
  if (selectedPlan.value === 'single') return '单次 · ¥9.9';
  if (selectedPlan.value === 'monthly') return '月卡 · ¥28';
  return '人工精修 · ¥99 起';
});

const ctaText = computed(() => `立即付款 · ${planNameText.value}`);
const qrTitle = computed(() => (
  currentState.value === 'hupijiao_qr' ? '虎皮椒微信支付' : '扫码加客服微信'
));
const qrSubtitle = computed(() => (
  currentState.value === 'hupijiao_qr'
    ? '通过虎皮椒安全付款，支付成功后自动开通'
    : '付款后我们会在 5 分钟内为你开通'
));
const qrHint = computed(() => (
  currentState.value === 'hupijiao_qr'
    ? '长按二维码识别付款；本页会自动刷新支付结果'
    : '长按二维码可保存到相册，或截屏后在微信里“识别图中二维码”'
));
const showQrOverlay = computed(() => qrUrl.value.includes('qr-placeholder'));

const selectSku = (plan: 'single' | 'monthly' | 'artisan') => {
  selectedPlan.value = plan;
};

const handleClose = () => {
  stopPolling();
  emit('close');
};

const backToPlans = () => {
  stopPolling();
  currentState.value = 'plans';
};

const handleShowQR = async () => {
  isLoading.value = true;
  stopPolling();
  try {
    let sku: 'single_9.9' | 'monthly_28' | 'custom_99' = 'monthly_28';
    if (selectedPlan.value === 'single') sku = 'single_9.9';
    else if (selectedPlan.value === 'artisan') sku = 'custom_99';
    
    const { order, qrInfo } = await paymentStore.createPayOrder(sku, props.artworkId);
    orderId.value = order.order_id;
    qrUrl.value = qrInfo.qr_url || '/static/assets/qr-placeholder.svg';
    pollingText.value = '等待付款中';

    currentState.value = 'hupijiao_qr';
    startPolling(order.order_id);
  } catch (e) {
    uni.showToast({
      title: '创建订单失败，请稍后重试',
      icon: 'none'
    });
  } finally {
    isLoading.value = false;
  }
};

const handleCustomerServiceFallback = async () => {
  isLoading.value = true;
  stopPolling();
  try {
    let sku: 'single_9.9' | 'monthly_28' | 'custom_99' = 'monthly_28';
    if (selectedPlan.value === 'single') sku = 'single_9.9';
    else if (selectedPlan.value === 'artisan') sku = 'custom_99';

    const { order, qrInfo } = await paymentStore.createCustomerServiceOrder(sku, props.artworkId);
    orderId.value = order.order_id;
    qrUrl.value = qrInfo.qr_url || '/static/assets/qr-placeholder.svg';
    currentState.value = 'customer_service_qr';
  } catch (e) {
    uni.showToast({
      title: '客服付款入口暂时不可用',
      icon: 'none'
    });
  } finally {
    isLoading.value = false;
  }
};

const startPolling = (targetOrderId: string) => {
  pollAttempts = 0;
  pollTimer = setInterval(async () => {
    pollAttempts += 1;
    try {
      const result = await paymentStore.checkOrderStatus(targetOrderId);
      if (result.status === 'paid_confirmed') {
        stopPolling();
        pollingText.value = '支付成功';
        try {
          await userStore.fetchProfile();
        } catch (e) {
          console.warn('刷新用户额度失败:', e);
        }
        uni.showToast({ title: '支付成功', icon: 'success' });
        emit('close');
        setTimeout(() => {
          uni.switchTab({ url: '/pages/artwork/list' });
        }, 500);
      } else if (result.status === 'failed') {
        stopPolling();
        pollingText.value = '订单已失效';
        uni.showToast({ title: '订单已失效，请重新下单', icon: 'none' });
        currentState.value = 'plans';
      } else {
        pollingText.value = `等待付款中 ${pollAttempts * 3}s`;
      }
    } catch (e) {
      console.warn('轮询订单状态失败:', e);
      pollingText.value = '网络波动，继续等待';
    }

    if (pollAttempts >= 100) {
      stopPolling();
      pollingText.value = '订单超时';
      uni.showToast({ title: '支付超时，请重新下单', icon: 'none' });
      currentState.value = 'plans';
    }
  }, 3000);
};

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

onUnmounted(stopPolling);
</script>

<style scoped lang="scss">
.paywall-overlay {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(45, 45, 45, 0.42);
  z-index: 998;
  display: block;
  backdrop-filter: blur(4px);
  box-sizing: border-box;
  padding: 0;
}

/* ===== Sheet shell ===== */
.paywall__sheet {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 999;
  width: 100vw;
  max-width: 100vw;
  max-height: calc(100vh - 64px);
  margin: 0;
  background: var(--pd-card);
  border-radius: 24px 24px 0 0;
  padding: 8px 20px calc(24px + constant(safe-area-inset-bottom));
  padding: 8px 20px calc(24px + env(safe-area-inset-bottom));
  box-shadow: 0 -12px 40px rgba(45, 45, 45, 0.18);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  box-sizing: border-box;
  -webkit-overflow-scrolling: touch;
  transform: translateY(0);
}

.paywall__handle {
  width: 36px;
  height: 4px;
  border-radius: 999px;
  background: var(--pd-divider);
  margin: 4px auto 12px;
  cursor: pointer;
}

/* ===== Sheet head ===== */
.paywall__head {
  text-align: center;
  margin-bottom: 18px;
}
.paywall__title {
  margin: 0 0 6px;
  font-family: var(--pd-font-display);
  font-size: 20px;
  font-weight: 800;
  color: var(--pd-fg-1);
  letter-spacing: -0.01em;
}
.paywall__subtitle {
  margin: 0;
  font-size: 12px;
  color: var(--pd-fg-2);
  line-height: 1.5;
}

/* ===== Plans row ===== */
.paywall__plans {
  list-style: none;
  margin: 0 0 18px;
  padding: 0;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}

.paywall__plan {
  position: relative;
  min-width: 0;
  border-radius: var(--pd-r-card);
  background: var(--pd-bg);
  border: 1.5px solid transparent;
  padding: 14px 8px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: transform 180ms var(--pd-ease-out),
              box-shadow 200ms var(--pd-ease-out);
              
  &:active { 
    transform: scale(0.98); 
  }
}

.paywall__plan-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--pd-fg-2);
  letter-spacing: 0.3px;
}
.paywall__plan-price {
  font-family: var(--pd-font-display);
  font-size: 22px;
  font-weight: 800;
  color: var(--pd-fg-1);
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.paywall__plan-price-sub {
  font-size: 11px;
  font-weight: 500;
  color: var(--pd-fg-2);
  margin-left: 2px;
}
.paywall__plan-meta {
  font-size: 10px;
  color: var(--pd-fg-3);
  letter-spacing: 0.2px;
}

.paywall__plan--recommended {
  background:
    linear-gradient(#fff, #fff) padding-box,
    var(--pd-gradient) border-box;
  border-color: transparent;
  box-shadow: 0 6px 18px rgba(255, 107, 157, 0.18);
}
.paywall__plan-badge {
  position: absolute;
  top: -9px;
  left: 50%;
  transform: translateX(-50%);
  padding: 3px 9px;
  background: var(--pd-gradient);
  border-radius: 999px;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
  white-space: nowrap;
  box-shadow: 0 3px 8px rgba(255, 107, 157, 0.3);
}

.paywall__plan--active {
  background:
    linear-gradient(var(--pd-pink-50), var(--pd-pink-50)) padding-box,
    var(--pd-pink) border-box;
}

/* ===== CTA + CDK link ===== */
.paywall__cta {
  margin-bottom: 12px;
  
  &:disabled {
    opacity: 0.7;
    background: var(--pd-pink-200);
  }
}
.paywall__cdk {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  color: var(--pd-fg-2);
  text-decoration: none;
  padding: 6px 12px;
  align-self: center;
  cursor: pointer;
  
  &:active { 
    opacity: 0.7; 
  }
}

/* ===== QR sub-state ===== */
.paywall__sheet--qr { 
  padding-bottom: calc(24px + constant(safe-area-inset-bottom));
  padding-bottom: calc(24px + env(safe-area-inset-bottom));
}

.paywall__qr-wrap {
  width: 200px;
  height: 200px;
  margin: 0 auto 18px;
  padding: 10px;
  border-radius: var(--pd-r-card);
  background: #fff;
  box-shadow: 0 8px 24px rgba(255, 138, 168, 0.18);
  border: 1px solid var(--pd-divider);
  position: relative;
}
.paywall__qr-code {
  width: 100%;
  height: 100%;
  display: block;
}
.paywall__qr-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.paywall__qr-overlay-inner {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--pd-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  box-shadow: 0 0 0 4px #fff, 0 6px 14px rgba(255, 107, 157, 0.32);
  color: #fff;
}
.paywall__qr-overlay-text {
  font-family: var(--pd-font-display);
  font-weight: 800;
  font-size: 14px;
  letter-spacing: 0.5px;
}

.paywall__order {
  margin: 0 0 14px;
  padding: 12px 14px;
  background: var(--pd-bg-warm);
  border-radius: var(--pd-r-card);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.paywall__order-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0;
}
.paywall__order-label {
  font-size: 12px;
  color: var(--pd-fg-2);
  margin: 0;
}
.paywall__order-value {
  margin: 0;
  font-family: var(--pd-font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--pd-fg-1);
  min-width: 0;
  max-width: 70%;
  text-align: right;
  overflow-wrap: anywhere;
}

.paywall__qr-hint {
  margin: 0 0 14px;
  font-size: 11px;
  line-height: 1.55;
  color: var(--pd-fg-2);
  text-align: center;
}

/* Slide transition for bottom sheet */
.sheet-enter-active, .sheet-leave-active {
  transition: transform 300ms var(--pd-ease-out), opacity 300ms var(--pd-ease-out);
}
.sheet-enter-from, .sheet-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

@media (max-width: 360px) {
  .paywall__sheet {
    padding-left: 14px;
    padding-right: 14px;
  }

  .paywall__plans {
    gap: 6px;
  }

  .paywall__plan {
    padding: 12px 6px 10px;
  }

  .paywall__plan-price {
    font-size: 20px;
  }

  .paywall__plan-meta {
    font-size: 9px;
  }

  .paywall__subtitle {
    font-size: 11px;
  }
}
</style>
