<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';

import { ApiError, createOrder, getOrder, getSkus, redeemCdk } from '../api';
import { API_BASE } from '../api/client';
import type { Order, PaymentSku, PaymentSkuCategory, PaymentSkuCatalog, PaymentSkuId } from '../api/types';
import { useAuthStore } from '../stores/auth';

type PricingReason = 'manual' | 'ai-low' | 'script-low';

const props = withDefaults(defineProps<{
  open: boolean;
  initialPanel?: PaymentSkuCategory;
  reason?: PricingReason;
}>(), {
  initialPanel: 'points',
  reason: 'manual'
});

const emit = defineEmits<{
  close: [];
  success: [];
}>();

const auth = useAuthStore();
const activePanel = ref<PaymentSkuCategory>(props.initialPanel);
const catalog = ref<PaymentSkuCatalog | null>(null);
const loadingSkus = ref(false);
const skuError = ref('');
const selectedSku = ref<PaymentSku | null>(null);
const currentOrder = ref<Order | null>(null);
const paymentMessage = ref('');
const paymentError = ref('');
const isCreatingOrder = ref(false);
const isPollingOrder = ref(false);
const cdkCode = ref('');
const cdkMessage = ref('');
const cdkError = ref('');
const cdkBusy = ref(false);

let pollTimer: number | undefined;
let pollDeadline = 0;

const user = computed(() => auth.user);
const isLoggedIn = computed(() => auth.isLoggedIn);
const isUnlimitedAccount = computed(() => Boolean(user.value?.is_unlimited_account));
const aiCost = computed(() => Number(catalog.value?.ai_generation_cost_points || user.value?.ai_generation_cost_points || 0));
const aiCostLabel = computed(() => aiCost.value > 0 ? `${aiCost.value}` : '…');
const aiBalance = computed(() => Number(user.value?.ai_points_balance ?? user.value?.paid_credits ?? 0));
const normalTrialRemaining = computed(() => Number(user.value?.normal_trial_remaining ?? user.value?.free_credits_remaining ?? 0));
const membershipExpiresAt = computed(() => user.value?.membership_expires_at || user.value?.monthly_card_expires_at || null);
const membershipActive = computed(() => {
  if (!membershipExpiresAt.value) {
    return false;
  }
  const expiresAt = Date.parse(membershipExpiresAt.value);
  return Number.isFinite(expiresAt) && expiresAt > Date.now();
});
const membershipLabel = computed(() => {
  if (!isLoggedIn.value) {
    return '未登录';
  }
  if (isUnlimitedAccount.value) {
    return '普通不限';
  }
  if (membershipActive.value && membershipExpiresAt.value) {
    return `会员至 ${formatMonthDay(membershipExpiresAt.value)}`;
  }
  return `普通剩余 ${normalTrialRemaining.value} 次`;
});
const aiGenerations = computed(() => {
  if (isUnlimitedAccount.value) {
    return '不限';
  }
  if (!aiCost.value) {
    return '同步中';
  }
  return `${Math.floor(aiBalance.value / aiCost.value)}`;
});
const aiGenerationsUnit = computed(() => /^\d+$/.test(String(aiGenerations.value)) ? ' 张' : '');
const aiShortfall = computed(() => Math.max(0, aiCost.value - aiBalance.value));
const pointsSkus = computed(() => (catalog.value?.items || []).filter((sku) => sku.category === 'points'));
const membershipSkus = computed(() => (catalog.value?.items || []).filter((sku) => sku.category === 'membership'));
const reasonText = computed(() => {
  if (props.reason === 'ai-low') {
    if (!aiCost.value) {
      return `当前 ${aiBalance.value} 积分，正在同步本次所需积分。`;
    }
    return `当前 ${aiBalance.value} 积分，本次需要 ${aiCost.value}，还差 ${aiShortfall.value} 积分。`;
  }
  if (props.reason === 'script-low') {
    return '普通额度用完啦，开通时间卡后普通图纸不限次。';
  }
  return 'AI 生成按积分扣费，普通模式可用时间卡解锁不限次。';
});
const orderRef = computed(() => currentOrder.value?.order_no || currentOrder.value?.order_id || '');
const qrUrl = computed(() => normalizeQrUrl(currentOrder.value?.qr_code_url || ''));
const orderExpiresLabel = computed(() => currentOrder.value?.expires_at ? formatTime(currentOrder.value.expires_at) : '');
const canSubmitCdk = computed(() => Boolean(cdkCode.value.trim()) && !cdkBusy.value);

watch(
  () => props.open,
  (open) => {
    if (open) {
      activePanel.value = props.initialPanel;
      resetPaymentState();
      void loadSkus();
    } else {
      stopPolling();
    }
  },
  { immediate: true }
);

watch(
  () => props.initialPanel,
  (panel) => {
    activePanel.value = panel;
  }
);

onBeforeUnmount(() => {
  stopPolling();
});

async function loadSkus(): Promise<void> {
  if (catalog.value || loadingSkus.value) {
    return;
  }
  loadingSkus.value = true;
  skuError.value = '';
  try {
    catalog.value = await getSkus();
  } catch (error) {
    skuError.value = readErrorMessage(error, '套餐暂时加载失败，请稍后重试。');
  } finally {
    loadingSkus.value = false;
  }
}

function close(): void {
  emit('close');
}

async function buySku(sku: PaymentSku): Promise<void> {
  cdkError.value = '';
  cdkMessage.value = '';
  if (!isLoggedIn.value) {
    paymentError.value = '请先登录/注册后购买，避免换设备后余额丢失。';
    return;
  }
  stopPolling();
  selectedSku.value = sku;
  currentOrder.value = null;
  paymentError.value = '';
  paymentMessage.value = '正在生成支付二维码…';
  isCreatingOrder.value = true;
  try {
    const order = await createOrder({ sku_id: sku.sku_id as PaymentSkuId });
    currentOrder.value = order;
    paymentMessage.value = '请使用微信扫码完成支付，支付成功后会自动刷新余额。';
    startPolling();
  } catch (error) {
    paymentError.value = readErrorMessage(error, '下单失败，请稍后再试。');
    paymentMessage.value = '';
  } finally {
    isCreatingOrder.value = false;
  }
}

async function submitCdk(): Promise<void> {
  const code = cdkCode.value.trim();
  cdkMessage.value = '';
  cdkError.value = '';
  if (!code) {
    cdkError.value = '请输入兑换码。';
    return;
  }
  if (!isLoggedIn.value) {
    cdkError.value = '请先登录/注册后兑换，余额会绑定到你的账号。';
    return;
  }
  cdkBusy.value = true;
  try {
    const result = await redeemCdk(code);
    await refreshProfileAfterPayment();
    cdkCode.value = '';
    cdkMessage.value = result.cdk_type === 'membership' || result.cdk_type === 'monthly_card'
      ? '时间卡兑换成功，会员权益已刷新。'
      : '积分兑换成功，余额已刷新。';
    emit('success');
  } catch (error) {
    cdkError.value = readErrorMessage(error, '兑换失败，请检查兑换码。');
  } finally {
    cdkBusy.value = false;
  }
}

function startPolling(): void {
  if (!orderRef.value) {
    paymentError.value = '订单创建成功但缺少订单号，请重新打开支付页。';
    return;
  }
  isPollingOrder.value = true;
  pollDeadline = paymentDeadline();
  void pollOrderOnce();
  pollTimer = window.setInterval(() => {
    void pollOrderOnce();
  }, 2400);
}

async function pollOrderOnce(): Promise<void> {
  if (!orderRef.value) {
    return;
  }
  if (Date.now() > pollDeadline) {
    stopPolling();
    paymentError.value = '还没确认到账。若已付款，请保留支付截图和订单号，联系客服补单。';
    paymentMessage.value = '二维码可能已过期，可重新选择套餐生成新二维码。';
    return;
  }
  try {
    const result = await getOrder(orderRef.value);
    if (result.status === 'paid_confirmed' || result.status === 'paid') {
      stopPolling();
      paymentMessage.value = '支付成功，余额已刷新。';
      paymentError.value = '';
      await refreshProfileAfterPayment();
      emit('success');
      return;
    }
    if (result.status === 'failed' || result.status === 'cancelled') {
      stopPolling();
      paymentError.value = '这个订单已失效，请重新选择套餐。';
      paymentMessage.value = '';
    }
  } catch (error) {
    paymentError.value = readErrorMessage(error, '订单状态暂时查不到，稍后会继续刷新。');
  }
}

async function refreshProfileAfterPayment(): Promise<void> {
  try {
    await auth.refreshProfile();
  } catch (_error) {
    paymentMessage.value = '权益已处理，资料刷新失败时请手动刷新页面。';
  }
}

function stopPolling(): void {
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = undefined;
  }
  isPollingOrder.value = false;
}

function resetPaymentState(): void {
  selectedSku.value = null;
  currentOrder.value = null;
  paymentMessage.value = '';
  paymentError.value = '';
  cdkMessage.value = '';
  cdkError.value = '';
  isCreatingOrder.value = false;
  isPollingOrder.value = false;
}

function displaySkuName(sku: PaymentSku): string {
  return sku.title
    .replace(/^PinDou\s*/, '')
    .replace('积分包', '包')
    .replace('普通图纸', '');
}

function skuAiCount(sku: PaymentSku): number {
  if (!aiCost.value) {
    return 0;
  }
  return Math.floor(Number(sku.points || sku.gift_points || 0) / aiCost.value);
}

function afterBuyAiCount(sku: PaymentSku): number {
  if (!aiCost.value) {
    return 0;
  }
  return Math.floor((aiBalance.value + Number(sku.points || sku.gift_points || 0)) / aiCost.value);
}

function normalizeQrUrl(url: string): string {
  if (!url) {
    return '';
  }
  if (/^https?:\/\//i.test(url) || url.startsWith('data:')) {
    return url;
  }
  if (url.startsWith('/payment/')) {
    return `${API_BASE}${url}`;
  }
  if (url.startsWith('/static/assets/')) {
    return `/h5${url}`;
  }
  return url;
}

function paymentDeadline(): number {
  const expiresAt = currentOrder.value?.expires_at ? Date.parse(currentOrder.value.expires_at) : NaN;
  if (Number.isFinite(expiresAt) && expiresAt > Date.now()) {
    return expiresAt + 15_000;
  }
  return Date.now() + 5 * 60 * 1000;
}

function formatPrice(value: string): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return `¥${value}`;
  }
  return `¥${numeric.toFixed(2).replace(/\.00$/, '').replace(/(\.\d)0$/, '$1')}`;
}

function formatMonthDay(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

function readErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message || fallback;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}
</script>

<template>
  <Teleport to="body">
    <Transition name="pricing-fade">
      <div v-if="open" class="pricing-backdrop" role="presentation" @click.self="close">
        <section class="pricing-modal" role="dialog" aria-modal="true" aria-labelledby="pricing-title">
          <button class="pricing-close" type="button" aria-label="关闭定价弹窗" @click="close">×</button>

          <header class="pricing-header">
            <span class="pricing-kicker">PinDou 钱包</span>
            <h2 id="pricing-title">继续做拼豆图纸</h2>
            <p>{{ reasonText }}</p>
            <p class="pricing-note">生成成功才扣，失败不扣。时间卡只解锁普通模式不限次；AI 仍按 {{ aiCostLabel }} 积分/张，月卡通过赠积分间接抵 AI。</p>
            <div class="pricing-balance" aria-label="当前余额">
              <span>当前 {{ aiBalance }} 积分</span>
              <span>可生成 AI {{ aiGenerations }}{{ aiGenerationsUnit }}</span>
              <span>{{ membershipLabel }}</span>
            </div>
            <p v-if="!isLoggedIn" class="pricing-guest-note">未登录状态暂按 0 余额展示。购买或兑换前请先登录/注册，避免换设备后余额丢失。</p>
          </header>

          <div v-if="skuError" class="pricing-alert pricing-alert--error">{{ skuError }}</div>
          <div v-else-if="loadingSkus" class="pricing-loading">正在加载套餐…</div>

          <div v-else class="pricing-panels">
            <section
              v-for="panel in ['points', 'membership']"
              :key="panel"
              class="pricing-panel"
              :class="{ 'pricing-panel--focus': activePanel === panel }"
            >
              <div class="pricing-panel__head">
                <strong>{{ panel === 'points' ? 'AI 积分充值' : '普通时间卡' }}</strong>
                <span>{{ panel === 'points' ? `${aiCostLabel} 积分 / 张` : '普通模式不限次' }}</span>
              </div>

              <div class="sku-grid" :aria-label="panel === 'points' ? 'AI 积分充值' : '普通时间卡'">
                <article
                  v-for="sku in (panel === 'points' ? pointsSkus : membershipSkus)"
                  :key="sku.sku"
                  class="sku-card"
                  :class="{ 'sku-card--featured': sku.badge === '最受欢迎' }"
                >
                  <div class="sku-card__badge-row">
                    <span class="sku-name">{{ displaySkuName(sku) }}</span>
                    <span v-if="sku.badge" class="sku-badge" :class="{ 'sku-badge--glass': sku.badge === '单价最低' }">
                      {{ sku.badge }}
                    </span>
                  </div>
                  <strong class="sku-price">{{ formatPrice(sku.amount_cny) }}</strong>
                  <p v-if="sku.category === 'points'" class="sku-main">{{ sku.points }} 积分</p>
                  <p v-else class="sku-main">{{ sku.days }} 天普通无限</p>
                  <p class="sku-subtitle">{{ sku.subtitle }}</p>
                  <p v-if="sku.category === 'points'" class="sku-math">
                    约 {{ skuAiCount(sku) }} 张 AI，充值后可生成 {{ afterBuyAiCount(sku) }} 张
                  </p>
                  <p v-else class="sku-math">
                    赠 {{ sku.gift_points }} 积分，约抵 {{ skuAiCount(sku) }} 张 AI
                  </p>
                  <button
                    class="sku-buy"
                    type="button"
                    :disabled="isCreatingOrder || isPollingOrder"
                    @click="buySku(sku)"
                  >
                    {{ selectedSku?.sku === sku.sku && isCreatingOrder ? '生成二维码…' : '选择这个套餐' }}
                  </button>
                </article>
              </div>
            </section>
          </div>

          <section v-if="currentOrder || paymentMessage || paymentError" class="payment-box" aria-live="polite">
            <div class="payment-box__text">
              <strong>{{ selectedSku ? displaySkuName(selectedSku) : '支付订单' }}</strong>
              <span v-if="orderRef">订单号 {{ orderRef }}</span>
              <span v-if="orderExpiresLabel">二维码约 {{ orderExpiresLabel }} 前有效</span>
            </div>
            <img v-if="qrUrl" class="payment-qr" :src="qrUrl" alt="支付二维码" />
            <p v-if="paymentMessage" class="payment-message">{{ paymentMessage }}</p>
            <p v-if="paymentError" class="payment-error">{{ paymentError }}</p>
            <button v-if="paymentError && selectedSku" class="payment-retry" type="button" @click="buySku(selectedSku)">
              重新生成二维码
            </button>
          </section>

          <section class="cdk-card">
            <div>
              <strong>已有兑换码？</strong>
              <span>积分 CDK / 时间卡 CDK 都可在这里兑换</span>
            </div>
            <form class="cdk-form" @submit.prevent="submitCdk">
              <input v-model="cdkCode" type="text" autocomplete="off" placeholder="输入 CDK 兑换码" />
              <button type="submit" :disabled="!canSubmitCdk">{{ cdkBusy ? '兑换中…' : '立即兑换' }}</button>
            </form>
            <p v-if="cdkMessage" class="cdk-success">{{ cdkMessage }}</p>
            <p v-else-if="cdkError" class="cdk-error">{{ cdkError }}</p>
          </section>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.pricing-backdrop {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: grid;
  place-items: center;
  background: rgba(45, 36, 30, 0.3);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  padding: clamp(12px, 3vw, 28px);
}

.pricing-modal {
  position: relative;
  width: min(100%, 1040px);
  max-height: min(860px, calc(100dvh - 24px));
  overflow-y: auto;
  overscroll-behavior: contain;
  display: grid;
  gap: 16px;
  border: 1px solid rgba(237, 228, 218, 0.92);
  border-radius: 30px;
  background:
    radial-gradient(circle at 16% 0%, rgba(255, 176, 136, 0.28), transparent 34%),
    radial-gradient(circle at 88% 10%, rgba(255, 218, 145, 0.28), transparent 30%),
    linear-gradient(145deg, rgba(255, 255, 255, 0.98), rgba(255, 247, 241, 0.98));
  box-shadow: var(--pd-shadow-modal), 0 18px 44px rgba(255, 142, 83, 0.16);
  padding: clamp(18px, 3vw, 28px);
}

.pricing-close {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 142, 83, 0.22);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  color: var(--pd-fg-2);
  cursor: pointer;
  font: inherit;
  font-size: 21px;
  font-weight: 900;
  line-height: 1;
  transition: transform 180ms var(--pd-ease-out), box-shadow 180ms var(--pd-ease-out), color 180ms var(--pd-ease-out);
}

.pricing-close:hover {
  color: var(--pd-orange);
  box-shadow: 0 10px 20px rgba(255, 142, 83, 0.14);
  transform: translateY(-1px);
}

.pricing-header {
  display: grid;
  gap: 8px;
  padding-right: 40px;
}

.pricing-kicker {
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 900;
}

.pricing-header h2 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(30px, 5vw, 44px);
  line-height: 1.12;
}

.pricing-header p {
  max-width: 760px;
  margin: 0;
  color: var(--pd-fg-2);
  font-size: 14px;
  font-weight: 800;
  line-height: 1.6;
}

.pricing-note {
  display: inline-block;
  width: fit-content;
  max-width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.58);
  border-radius: var(--pd-r-tag);
  background: rgba(255, 198, 107, 0.3);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
  padding: 6px 9px;
  color: var(--pd-fg-1) !important;
}

.pricing-balance {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.pricing-balance span,
.pricing-guest-note {
  border: 1px solid rgba(255, 142, 83, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--pd-fg-1);
  font-size: 12px;
  font-weight: 900;
  padding: 7px 10px;
}

.pricing-guest-note {
  width: fit-content;
  max-width: 100%;
  border-radius: 14px;
  color: var(--pd-orange) !important;
}

.pricing-loading,
.pricing-alert {
  border: 1px solid rgba(255, 142, 83, 0.16);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--pd-fg-2);
  font-weight: 900;
  padding: 14px;
}

.pricing-alert--error,
.payment-error,
.cdk-error {
  color: #e35151;
}

.pricing-panels {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.pricing-panel {
  min-width: 0;
  display: grid;
  gap: 12px;
  border: 1px solid rgba(237, 228, 218, 0.86);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.72);
  padding: 14px;
}

.pricing-panel--focus {
  border-color: rgba(255, 142, 83, 0.42);
  box-shadow: 0 16px 34px rgba(255, 142, 83, 0.1);
}

.pricing-panel__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.pricing-panel__head strong {
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: 24px;
}

.pricing-panel__head span {
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 900;
  text-align: right;
}

.sku-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  align-items: stretch;
}

.sku-card {
  position: relative;
  min-width: 0;
  display: grid;
  align-content: start;
  gap: 8px;
  border: 1px solid rgba(255, 142, 83, 0.16);
  border-radius: 20px;
  background: rgba(255, 250, 247, 0.92);
  padding: 12px;
  transition: transform 180ms var(--pd-ease-out), box-shadow 180ms var(--pd-ease-out), border-color 180ms var(--pd-ease-out);
}

.sku-card:hover {
  border-color: rgba(255, 142, 83, 0.5);
  box-shadow: 0 16px 32px rgba(255, 142, 83, 0.14);
  transform: translateY(-2px);
}

.sku-card--featured {
  border-color: rgba(255, 142, 83, 0.72);
  box-shadow: 0 16px 34px rgba(255, 142, 83, 0.18);
  transform: translateY(-4px);
}

.sku-card__badge-row {
  min-height: 48px;
  display: grid;
  gap: 5px;
}

.sku-name {
  color: var(--pd-fg-1);
  font-size: 15px;
  font-weight: 900;
  line-height: 1.2;
}

.sku-badge {
  width: fit-content;
  border-radius: 999px;
  background: var(--pd-gradient);
  color: #fff;
  font-size: 11px;
  font-weight: 900;
  padding: 4px 8px;
  white-space: nowrap;
}

.sku-badge--glass {
  border: 1px solid rgba(255, 255, 255, 0.56);
  border-radius: var(--pd-r-tag);
  background: rgba(255, 198, 107, 0.32);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
  color: var(--pd-fg-1);
}

.sku-price {
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(27px, 4vw, 38px);
  line-height: 1;
}

.sku-main,
.sku-subtitle,
.sku-math {
  margin: 0;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 800;
  line-height: 1.45;
}

.sku-main {
  color: var(--pd-orange);
  font-size: 14px;
  font-weight: 900;
}

.sku-buy,
.payment-retry,
.cdk-form button {
  min-height: 40px;
  border: 1px solid rgba(255, 142, 83, 0.28);
  border-radius: 999px;
  background: rgba(255, 241, 232, 0.86);
  color: var(--pd-orange);
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 900;
  transition: transform 180ms var(--pd-ease-out), box-shadow 180ms var(--pd-ease-out), border-color 180ms var(--pd-ease-out);
}

.sku-card--featured .sku-buy {
  border-color: transparent;
  background: var(--pd-gradient);
  color: #fff;
  box-shadow: var(--pd-shadow-cta);
}

.sku-buy:hover:not(:disabled),
.payment-retry:hover,
.cdk-form button:hover:not(:disabled) {
  border-color: rgba(255, 142, 83, 0.5);
  box-shadow: 0 12px 24px rgba(255, 142, 83, 0.14);
  transform: translateY(-1px);
}

.sku-buy:disabled,
.cdk-form button:disabled {
  cursor: not-allowed;
  opacity: 0.62;
  transform: none;
}

.payment-box,
.cdk-card {
  display: grid;
  gap: 10px;
  border: 1px solid rgba(255, 142, 83, 0.18);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.8);
  padding: 14px;
}

.payment-box {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
}

.payment-box__text {
  display: grid;
  gap: 3px;
}

.payment-box__text strong,
.cdk-card strong {
  color: var(--pd-fg-1);
  font-weight: 900;
}

.payment-box__text span,
.cdk-card span,
.payment-message,
.payment-error,
.cdk-success,
.cdk-error {
  margin: 0;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 800;
}

.payment-qr {
  width: 148px;
  height: 148px;
  border: 1px solid rgba(237, 228, 218, 0.9);
  border-radius: 18px;
  background: #fff;
  object-fit: contain;
  padding: 8px;
}

.payment-retry {
  width: fit-content;
  padding: 0 14px;
}

.cdk-card > div {
  display: grid;
  gap: 3px;
}

.cdk-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
}

.cdk-form input {
  min-width: 0;
  min-height: 44px;
  border: 1px solid rgba(255, 142, 83, 0.22);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--pd-fg-1);
  font: inherit;
  font-weight: 900;
  outline: none;
  padding: 0 13px;
}

.cdk-form input:focus {
  border-color: rgba(255, 142, 83, 0.64);
  box-shadow: 0 0 0 4px rgba(255, 142, 83, 0.12);
}

.cdk-form button {
  padding: 0 16px;
}

.cdk-success {
  color: #23864c;
}

.pricing-fade-enter-active,
.pricing-fade-leave-active {
  transition: opacity 180ms var(--pd-ease-out), transform 180ms var(--pd-ease-out);
}

.pricing-fade-enter-from,
.pricing-fade-leave-to {
  opacity: 0;
}

@media (max-width: 920px) {
  .pricing-panels {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .pricing-backdrop {
    align-items: end;
    padding: 10px;
  }

  .pricing-modal {
    max-height: calc(100dvh - 20px);
    border-radius: 26px;
    padding: 18px;
  }

  .pricing-header {
    padding-right: 30px;
  }

  .sku-grid {
    grid-template-columns: 1fr;
  }

  .sku-card--featured {
    transform: none;
  }

  .payment-box {
    grid-template-columns: 1fr;
  }

  .payment-qr {
    width: min(180px, 58vw);
    height: min(180px, 58vw);
    justify-self: center;
  }

  .cdk-form {
    grid-template-columns: 1fr;
  }
}
</style>
