<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';

import { ApiError, createOrder, getOrder, getSkus, redeemCdk } from '../api';
import { API_BASE } from '../api/client';
import type { Order, PaymentSku, PaymentSkuCategory, PaymentSkuCatalog, PaymentSkuId } from '../api/types';
import { useAuthStore } from '../stores/auth';

type PricingReason = 'manual' | 'ai-low' | 'script-low';
type PaymentView = 'catalog' | 'payment' | 'success';

const props = withDefaults(defineProps<{
  open: boolean;
  initialPanel?: PaymentSkuCategory;
  focusCdk?: boolean;
  reason?: PricingReason;
}>(), {
  initialPanel: 'points',
  focusCdk: false,
  reason: 'manual'
});

const emit = defineEmits<{
  close: [];
  success: [];
}>();

const SKU_DISPLAY_NAMES: Partial<Record<PaymentSkuId, string>> = {
  points_trial_099: '体验包',
  points_standard_990: '标准包',
  points_value_2990: '超值包',
  membership_week_990: '周卡',
  membership_month_1990: '月卡',
  membership_season_4990: '季卡'
};

const SKU_DISPLAY_ORDER: Partial<Record<PaymentSkuId, number>> = {
  points_trial_099: 10,
  points_standard_990: 20,
  points_value_2990: 30,
  membership_week_990: 10,
  membership_month_1990: 20,
  membership_season_4990: 30
};

const PAYMENT_QR_TTL_MS = 5 * 60 * 1000;

const auth = useAuthStore();
const activePanel = ref<PaymentSkuCategory>(props.initialPanel);
const catalog = ref<PaymentSkuCatalog | null>(null);
const loadingSkus = ref(false);
const skuError = ref('');
const selectedSku = ref<PaymentSku | null>(null);
const currentOrder = ref<Order | null>(null);
const paymentView = ref<PaymentView>('catalog');
const paymentMessage = ref('');
const paymentError = ref('');
const isCreatingOrder = ref(false);
const isPollingOrder = ref(false);
const cdkCode = ref('');
const cdkMessage = ref('');
const cdkError = ref('');
const cdkBusy = ref(false);
const cdkExpanded = ref(false);
const cdkInputRef = ref<HTMLInputElement | null>(null);

let pollTimer: number | undefined;
let countdownTimer: number | undefined;
let autoCloseTimer: number | undefined;
let pollDeadline = 0;
const nowTick = ref(Date.now());

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
const activeSkus = computed(() => {
  const skus = activePanel.value === 'points' ? pointsSkus.value : membershipSkus.value;
  return [...skus].sort((left, right) => skuSortRank(left) - skuSortRank(right));
});
const activePanelTitle = computed(() => activePanel.value === 'points' ? 'AI 积分' : '时间卡会员');
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
const orderCountdown = computed(() => {
  if (paymentView.value !== 'payment' || pollDeadline <= 0) {
    return '';
  }
  return formatDuration(pollDeadline - nowTick.value);
});
const isPaymentExpired = computed(() => paymentView.value === 'payment' && pollDeadline > 0 && nowTick.value >= pollDeadline);
const paymentResultText = computed(() => {
  if (!selectedSku.value) {
    return '权益已到账';
  }
  if (selectedSku.value.category === 'points') {
    return `+${selectedSku.value.points || 0} 积分已到账`;
  }
  const gift = selectedSku.value.gift_points ? `，赠 ${selectedSku.value.gift_points} 积分已到账` : '';
  return `已开通 ${displaySkuName(selectedSku.value)}${gift}`;
});
const canSubmitCdk = computed(() => Boolean(cdkCode.value.trim()) && !cdkBusy.value);

watch(
  () => props.open,
  (open) => {
    if (open) {
      activePanel.value = props.initialPanel;
      resetPaymentState();
      cdkExpanded.value = props.focusCdk;
      void loadSkus().then(() => {
        selectRecommendedSku();
        if (props.focusCdk) {
          void focusCdkInput();
        }
      });
    } else {
      stopPolling();
      clearAutoCloseTimer();
    }
  },
  { immediate: true }
);

watch(
  () => props.initialPanel,
  (panel) => {
    activePanel.value = panel;
    selectRecommendedSku();
  }
);

watch(
  () => props.focusCdk,
  (focusCdk) => {
    if (props.open && focusCdk) {
      cdkExpanded.value = true;
      void focusCdkInput();
    }
  }
);

onBeforeUnmount(() => {
  stopPolling();
  clearAutoCloseTimer();
});

async function loadSkus(): Promise<void> {
  if (catalog.value) {
    selectRecommendedSku();
    return;
  }
  if (loadingSkus.value) {
    return;
  }
  loadingSkus.value = true;
  skuError.value = '';
  try {
    catalog.value = await getSkus();
    selectRecommendedSku();
  } catch (error) {
    skuError.value = readErrorMessage(error, '套餐暂时加载失败，请稍后重试。');
  } finally {
    loadingSkus.value = false;
  }
}

function close(): void {
  stopPolling();
  clearAutoCloseTimer();
  emit('close');
}

function selectPanel(panel: PaymentSkuCategory): void {
  if (activePanel.value === panel) {
    return;
  }
  activePanel.value = panel;
  resetPaymentState();
  selectRecommendedSku();
}

function selectRecommendedSku(): void {
  if (!catalog.value || currentOrder.value) {
    return;
  }
  const skus = activePanel.value === 'points' ? pointsSkus.value : membershipSkus.value;
  const currentSku = selectedSku.value;
  if (currentSku && currentSku.category === activePanel.value) {
    return;
  }
  selectedSku.value = skus.find((sku) => isRecommendedSku(sku)) || skus[0] || null;
}

function isRecommendedSku(sku: PaymentSku): boolean {
  return sku.badge === '最受欢迎' || sku.sku_id === 'points_standard_990' || sku.sku_id === 'membership_month_1990';
}

async function focusCdkInput(): Promise<void> {
  await nextTick();
  cdkInputRef.value?.focus();
}

async function buySku(sku: PaymentSku): Promise<void> {
  cdkError.value = '';
  cdkMessage.value = '';
  clearAutoCloseTimer();
  if (!isLoggedIn.value) {
    paymentError.value = '请先登录/注册后购买，避免换设备后余额丢失。';
    paymentView.value = 'catalog';
    return;
  }
  stopPolling();
  selectedSku.value = sku;
  currentOrder.value = null;
  paymentError.value = '';
  paymentMessage.value = '正在生成支付二维码…';
  paymentView.value = 'payment';
  isCreatingOrder.value = true;
  try {
    const order = await createOrder({ sku_id: sku.sku_id as PaymentSkuId });
    currentOrder.value = order;
    paymentMessage.value = '';
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
  cdkBusy.value = true;
  try {
    const result = await redeemCdk(code, { auth: isLoggedIn.value });
    if (isLoggedIn.value) {
      await refreshProfileAfterPayment();
    }
    cdkCode.value = '';
    cdkMessage.value = result.cdk_type === 'membership' || result.cdk_type === 'monthly_card'
      ? (isLoggedIn.value ? '时间卡兑换成功，会员权益已刷新。' : '时间卡已兑换到本设备。')
      : (isLoggedIn.value ? '积分兑换成功，余额已刷新。' : '积分已兑换到本设备。');
    emit('success');
  } catch (error) {
    cdkError.value = readErrorMessage(error, '兑换失败，请检查兑换码。');
  } finally {
    cdkBusy.value = false;
  }
}

function startPolling(): void {
  if (!orderRef.value) {
    paymentError.value = '订单创建成功但缺少支付信息，请重新打开支付页。';
    return;
  }
  isPollingOrder.value = true;
  pollDeadline = paymentDeadline();
  startCountdown();
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
    paymentError.value = '二维码已过期。若已付款，请保留支付截图，联系客服补单。';
    paymentMessage.value = '';
    return;
  }
  try {
    const result = await getOrder(orderRef.value);
    if (result.status === 'paid_confirmed' || result.status === 'paid') {
      stopPolling();
      paymentError.value = '';
      const refreshed = await refreshProfileAfterPayment();
      paymentMessage.value = refreshed ? paymentResultText.value : '支付成功，资料刷新失败，请手动刷新页面。';
      paymentView.value = 'success';
      emit('success');
      scheduleAutoClose();
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

async function refreshProfileAfterPayment(): Promise<boolean> {
  try {
    await auth.refreshProfile();
    return true;
  } catch (_error) {
    paymentMessage.value = '权益已处理，资料刷新失败时请手动刷新页面。';
    return false;
  }
}

function stopPolling(): void {
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = undefined;
  }
  if (countdownTimer) {
    window.clearInterval(countdownTimer);
    countdownTimer = undefined;
  }
  isPollingOrder.value = false;
}

function resetPaymentState(): void {
  selectedSku.value = null;
  currentOrder.value = null;
  paymentView.value = 'catalog';
  paymentMessage.value = '';
  paymentError.value = '';
  cdkMessage.value = '';
  cdkError.value = '';
  isCreatingOrder.value = false;
  isPollingOrder.value = false;
  clearAutoCloseTimer();
}

function returnToCatalog(): void {
  stopPolling();
  clearAutoCloseTimer();
  currentOrder.value = null;
  paymentMessage.value = '';
  paymentError.value = '';
  paymentView.value = 'catalog';
  isCreatingOrder.value = false;
  selectRecommendedSku();
}

function startCountdown(): void {
  nowTick.value = Date.now();
  if (countdownTimer) {
    window.clearInterval(countdownTimer);
  }
  countdownTimer = window.setInterval(() => {
    nowTick.value = Date.now();
  }, 1000);
}

function scheduleAutoClose(): void {
  clearAutoCloseTimer();
  autoCloseTimer = window.setTimeout(() => {
    close();
  }, 1200);
}

function clearAutoCloseTimer(): void {
  if (autoCloseTimer) {
    window.clearTimeout(autoCloseTimer);
    autoCloseTimer = undefined;
  }
}

function displaySkuName(sku: PaymentSku): string {
  if (SKU_DISPLAY_NAMES[sku.sku_id]) {
    return SKU_DISPLAY_NAMES[sku.sku_id]!;
  }
  return sku.title
    .replace(/^PinDou\s*/, '')
    .replace('积分包', '包')
    .replace('普通图纸', '');
}

function skuSortRank(sku: PaymentSku): number {
  return SKU_DISPLAY_ORDER[sku.sku_id] ?? 999;
}

function skuAiCount(sku: PaymentSku): number {
  if (!aiCost.value) {
    return 0;
  }
  return Math.floor(Number(sku.points || sku.gift_points || 0) / aiCost.value);
}

function skuCoreLine(sku: PaymentSku): string {
  if (sku.category === 'points') {
    return `${sku.points || 0} 积分`;
  }
  return `${sku.days || 0} 天普通无限`;
}

function skuValueLine(sku: PaymentSku): string {
  if (sku.category === 'points') {
    return `≈ ${skuAiCount(sku)} 张 AI`;
  }
  return `赠 ${sku.gift_points || 0} 积分`;
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
  const expiresAt = parseOrderExpiresAt(currentOrder.value?.expires_at || '');
  if (Number.isFinite(expiresAt) && expiresAt - Date.now() > 1000) {
    return expiresAt;
  }
  return Date.now() + PAYMENT_QR_TTL_MS;
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

function formatDuration(milliseconds: number): string {
  const totalSeconds = Math.max(0, Math.ceil(milliseconds / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

function parseOrderExpiresAt(value: string): number {
  const raw = value.trim();
  if (!raw) {
    return NaN;
  }
  const normalized = raw
    .replace(' ', 'T')
    .replace(/(\.\d{3})\d+/, '$1');
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(normalized);
  const candidates = hasTimezone ? [normalized] : [`${normalized}Z`, normalized];
  for (const candidate of candidates) {
    const parsed = Date.parse(candidate);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return NaN;
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
            <h2 id="pricing-title">充值中心</h2>
            <div class="pricing-summary">
              <span>支付成功后自动到账。</span>
              <details class="pricing-info">
                <summary aria-label="查看计费说明">ⓘ</summary>
                <p>AI 按 {{ aiCostLabel }} 积分/张计费，成功才扣；时间卡只解锁普通模式不限次，赠送积分可用于 AI。</p>
              </details>
            </div>
            <p v-if="props.reason !== 'manual'" class="pricing-context">{{ reasonText }} 生成成功才扣，失败不扣。</p>
            <p v-if="isLoggedIn && !isUnlimitedAccount" class="pricing-wallet-line">
              当前 {{ aiBalance }} 积分 · 可生成 AI {{ aiGenerations }}{{ aiGenerationsUnit }} · {{ membershipLabel }}
            </p>
            <p v-if="!isLoggedIn" class="pricing-guest-note">CDK 可直接兑换到本设备；充值请先登录/注册，避免换设备后余额丢失。</p>
          </header>

          <nav v-if="paymentView === 'catalog'" class="pricing-tabs" aria-label="充值类型">
            <button
              type="button"
              :class="{ 'pricing-tab--active': activePanel === 'points' }"
              @click="selectPanel('points')"
            >
              AI 积分
            </button>
            <button
              type="button"
              :class="{ 'pricing-tab--active': activePanel === 'membership' }"
              @click="selectPanel('membership')"
            >
              时间卡会员
            </button>
          </nav>

          <div v-if="paymentView === 'catalog' && skuError" class="pricing-alert pricing-alert--error">{{ skuError }}</div>
          <div v-else-if="paymentView === 'catalog' && loadingSkus" class="pricing-loading">正在加载套餐…</div>
          <div v-if="paymentView === 'catalog' && !skuError && !loadingSkus && paymentError" class="pricing-alert pricing-alert--error">{{ paymentError }}</div>

          <section v-if="paymentView === 'catalog' && !skuError && !loadingSkus" class="pricing-panel">
            <div class="sku-grid" :aria-label="activePanelTitle">
              <article
                v-for="sku in activeSkus"
                :key="sku.sku"
                class="sku-card"
                :class="{
                  'sku-card--featured': isRecommendedSku(sku),
                  'sku-card--selected': selectedSku?.sku === sku.sku
                }"
              >
                <div class="sku-card__top">
                  <span class="sku-name">{{ displaySkuName(sku) }}</span>
                  <span v-if="sku.badge" class="sku-badge" :class="{ 'sku-badge--glass': sku.badge === '单价最低' }">
                    {{ sku.badge }}
                  </span>
                </div>
                <strong class="sku-price">{{ formatPrice(sku.amount_cny) }}</strong>
                <p class="sku-main">{{ skuCoreLine(sku) }}</p>
                <p :class="sku.category === 'membership' ? 'sku-gift' : 'sku-math'">{{ skuValueLine(sku) }}</p>
                <button
                  class="sku-buy"
                  type="button"
                  :disabled="isCreatingOrder || isPollingOrder"
                  @click="buySku(sku)"
                >
                  {{ selectedSku?.sku === sku.sku && isCreatingOrder ? '生成二维码…' : '选择' }}
                </button>
              </article>
            </div>

          </section>

          <section v-else-if="paymentView !== 'catalog'" class="payment-view" :class="{ 'payment-view--success': paymentView === 'success' }" aria-live="polite">
            <template v-if="paymentView === 'success'">
              <div class="payment-success-mark" aria-hidden="true">✓</div>
              <h3>支付成功</h3>
              <p>{{ paymentMessage || paymentResultText }}</p>
              <span>钱包正在刷新，稍后自动关闭</span>
            </template>

            <template v-else>
              <div class="payment-view__summary">
                <strong>{{ selectedSku ? displaySkuName(selectedSku) : '支付订单' }}</strong>
                <em v-if="selectedSku">{{ formatPrice(selectedSku.amount_cny) }}</em>
              </div>

              <div class="wechat-pay-card">
                <div class="wechat-pay-card__head">
                  <span class="wechat-pay-card__icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" focusable="false">
                      <path d="M8.2 9.4c-2.8 0-5 1.7-5 3.9 0 1.2.7 2.3 1.8 3l-.5 1.8 2.1-1a6.6 6.6 0 0 0 1.6.2c2.8 0 5-1.7 5-3.9s-2.2-4-5-4Z" />
                      <path d="M12.6 5.8c4.5 0 8.2 2.8 8.2 6.3 0 1.8-1 3.5-2.7 4.6l.8 2.7-3.1-1.5a10.6 10.6 0 0 1-3.2.5c-.9 0-1.8-.1-2.6-.3" />
                      <path d="M6.9 12.8h.01M9.6 12.8h.01M10.1 9.5h.01M14.3 9.5h.01" />
                    </svg>
                  </span>
                  <strong>微信扫码支付</strong>
                </div>
                <div class="payment-qr-frame">
                  <img v-if="qrUrl" class="payment-qr" :src="qrUrl" alt="支付二维码" />
                  <div v-else class="payment-qr-placeholder">
                    {{ isCreatingOrder ? '生成中…' : '暂无二维码' }}
                  </div>
                </div>
              </div>

              <p v-if="orderCountdown && !paymentError && !isPaymentExpired" class="payment-countdown">二维码 {{ orderCountdown }} 内有效</p>
              <p v-else-if="isPaymentExpired && !paymentError" class="payment-error">二维码已过期。</p>
              <p v-if="paymentMessage" class="payment-message">{{ paymentMessage }}</p>
              <p v-if="paymentError" class="payment-error">{{ paymentError }}</p>

              <div class="payment-actions">
                <button class="payment-back" type="button" :disabled="isCreatingOrder" @click="returnToCatalog">返回</button>
                <button v-if="paymentError && selectedSku" class="payment-retry" type="button" @click="buySku(selectedSku)">
                  重新生成
                </button>
              </div>
            </template>
          </section>

          <section v-if="paymentView === 'catalog'" class="cdk-card" :class="{ 'cdk-card--open': cdkExpanded }">
            <button class="cdk-toggle" type="button" @click="cdkExpanded = !cdkExpanded">
              <span>有兑换码？</span>
              <strong>{{ cdkExpanded ? '收起' : '展开兑换' }}</strong>
            </button>
            <form v-if="cdkExpanded" class="cdk-form" @submit.prevent="submitCdk">
              <input ref="cdkInputRef" v-model="cdkCode" type="text" autocomplete="off" placeholder="输入 CDK 兑换码" />
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
  padding: clamp(10px, 2.4vw, 24px);
}

.pricing-modal {
  position: relative;
  width: min(100%, 760px);
  max-height: min(720px, 85dvh);
  overflow: hidden;
  overscroll-behavior: contain;
  display: grid;
  gap: 9px;
  border: 1px solid rgba(255, 177, 128, 0.42);
  border-radius: 26px;
  background:
    radial-gradient(circle at 12% 4%, rgba(255, 231, 209, 0.92), transparent 34%),
    radial-gradient(circle at 92% 18%, rgba(255, 226, 235, 0.82), transparent 32%),
    linear-gradient(155deg, #fff7f0 0%, #ffece1 48%, #fff6ed 100%);
  box-shadow: 0 30px 74px rgba(143, 75, 44, 0.2), 0 10px 26px rgba(255, 142, 83, 0.14);
  padding: clamp(14px, 2vw, 20px);
}

.pricing-close {
  position: absolute;
  top: 13px;
  right: 13px;
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 142, 83, 0.22);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
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
  position: relative;
  z-index: 5;
  display: grid;
  gap: 6px;
  border-bottom: 1px solid rgba(255, 177, 128, 0.22);
  padding-right: 38px;
  padding-bottom: 9px;
}

.pricing-header h2 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(28px, 4.4vw, 38px);
  line-height: 1.08;
}

.pricing-summary {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: fit-content;
  max-width: 100%;
  color: #61666d;
  font-size: 13px;
  font-weight: 900;
  line-height: 1.45;
}

.pricing-summary > span {
  min-width: 0;
}

.pricing-info {
  position: relative;
  flex: 0 0 auto;
  z-index: 40;
}

.pricing-info summary {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 142, 83, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--pd-orange);
  cursor: pointer;
  font-size: 13px;
  font-weight: 900;
  list-style: none;
}

.pricing-info summary::-webkit-details-marker {
  display: none;
}

.pricing-info p {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  z-index: 60;
  width: min(300px, calc(100vw - 48px));
  margin: 0;
  border: 1px solid rgba(255, 142, 83, 0.18);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 16px 34px rgba(45, 45, 45, 0.13);
  color: var(--pd-fg-1);
  font-size: 12px;
  font-weight: 800;
  line-height: 1.5;
  padding: 10px 12px;
}

.pricing-context,
.pricing-wallet-line,
.pricing-guest-note {
  margin: 0;
  font-size: 12px;
  font-weight: 900;
  line-height: 1.5;
}

.pricing-context,
.pricing-guest-note {
  width: fit-content;
  max-width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.58);
  border-radius: var(--pd-r-tag);
  background: rgba(255, 198, 107, 0.3);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
  color: var(--pd-fg-1);
  padding: 6px 9px;
}

.pricing-wallet-line {
  color: var(--pd-fg-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pricing-guest-note {
  color: var(--pd-orange);
}

.pricing-tabs {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px;
  border: 1px solid rgba(255, 177, 128, 0.32);
  border-radius: 999px;
  background: rgba(255, 250, 245, 0.82);
  box-shadow: inset 0 1px 3px rgba(143, 75, 44, 0.05);
  padding: 5px;
}

.pricing-tabs button {
  position: relative;
  z-index: 1;
  min-width: 0;
  min-height: 42px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: #51463f;
  cursor: pointer;
  font: inherit;
  font-size: clamp(14px, 3.5vw, 16px);
  font-weight: 900;
  white-space: nowrap;
  transition: transform 180ms var(--pd-ease-out), box-shadow 180ms var(--pd-ease-out), color 180ms var(--pd-ease-out), background 180ms var(--pd-ease-out), border-color 180ms var(--pd-ease-out);
}

.pricing-tabs button:hover:not(.pricing-tab--active) {
  border-color: rgba(255, 142, 83, 0.24);
  background: #fff;
  color: #241f1a;
  transform: translateY(-1px);
}

.pricing-tabs .pricing-tab--active,
.pricing-tabs .pricing-tab--active:hover,
.pricing-tabs .pricing-tab--active:focus-visible {
  z-index: 2;
  border-color: rgba(255, 142, 83, 0.26);
  background: var(--pd-gradient);
  color: #fff !important;
  font-weight: 900;
  text-shadow: 0 1px 1px rgba(137, 61, 31, 0.22);
  box-shadow: 0 10px 22px rgba(255, 110, 112, 0.24);
}

.pricing-loading,
.pricing-alert,
.pricing-panel,
.payment-view,
.cdk-card {
  border: 1px solid rgba(255, 177, 128, 0.28);
  border-radius: 22px;
  background: #fff;
}

.pricing-loading,
.pricing-alert {
  color: var(--pd-fg-2);
  font-weight: 900;
  padding: 14px;
}

.pricing-alert--error,
.payment-error,
.cdk-error {
  color: #e35151;
}

.pricing-panel {
  min-width: 0;
  max-height: min(390px, calc(85dvh - 210px));
  display: grid;
  gap: 10px;
  background:
    linear-gradient(180deg, rgba(255, 247, 239, 0.94), rgba(255, 235, 224, 0.72));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82), 0 10px 28px rgba(255, 142, 83, 0.07);
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 18px 14px;
}

.sku-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.12fr) minmax(0, 0.9fr);
  gap: 12px;
  align-items: center;
}

.sku-card {
  position: relative;
  min-width: 0;
  min-height: 250px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  border: 1px solid rgba(255, 177, 128, 0.26);
  border-radius: 24px;
  background: linear-gradient(180deg, #fff 0%, #fff9f4 100%);
  box-shadow: 0 14px 30px rgba(143, 75, 44, 0.1), 0 6px 16px rgba(255, 142, 83, 0.08);
  text-align: center;
  padding: 18px 14px;
  transition: transform 180ms var(--pd-ease-out), box-shadow 180ms var(--pd-ease-out), border-color 180ms var(--pd-ease-out), background 180ms var(--pd-ease-out);
}

.sku-card:hover {
  border-color: rgba(255, 142, 83, 0.56);
  box-shadow: 0 18px 38px rgba(143, 75, 44, 0.14), 0 10px 22px rgba(255, 142, 83, 0.14);
  transform: translateY(-2px);
}

.sku-card--featured {
  z-index: 1;
  border-color: rgba(255, 142, 83, 0.86);
  min-height: 302px;
  border-width: 2px;
  background:
    radial-gradient(circle at 50% 0%, rgba(255, 230, 198, 0.88), transparent 38%),
    linear-gradient(180deg, #fff 0%, #fff5ed 100%);
  box-shadow: 0 26px 54px rgba(143, 75, 44, 0.18), 0 12px 30px rgba(255, 142, 83, 0.24);
  transform: translateY(-4px) scale(1.035);
}

.sku-card--featured:hover {
  box-shadow: 0 30px 62px rgba(143, 75, 44, 0.2), 0 14px 34px rgba(255, 111, 143, 0.22);
  transform: translateY(-7px) scale(1.035);
}

.sku-card--selected {
  outline: 3px solid rgba(255, 142, 83, 0.12);
}

.sku-card__top {
  min-height: 44px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 7px;
}

.sku-name {
  min-width: 0;
  color: var(--pd-fg-1);
  font-size: 17px;
  font-weight: 900;
  line-height: 1.2;
  white-space: nowrap;
}

.sku-card--featured .sku-name {
  font-size: 19px;
}

.sku-badge {
  flex: 0 0 auto;
  width: fit-content;
  border: 1px solid rgba(255, 255, 255, 0.62);
  border-radius: var(--pd-r-tag);
  background: rgba(255, 198, 107, 0.36);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
  color: var(--pd-fg-1);
  font-size: 11px;
  font-weight: 900;
  line-height: 1;
  padding: 5px 8px;
  white-space: nowrap;
}

.sku-badge--glass {
  background: rgba(255, 198, 107, 0.42);
}

.sku-price {
  display: block;
  min-height: 44px;
  color: var(--pd-orange);
  font-family: var(--pd-font-display);
  font-size: clamp(31px, 3.9vw, 39px);
  line-height: 1;
  padding: 6px 0 2px;
  white-space: nowrap;
}

.sku-card--featured .sku-price {
  font-size: clamp(34px, 4.4vw, 44px);
}

.sku-main,
.sku-math,
.sku-gift {
  margin: 0;
  font-weight: 900;
  line-height: 1.42;
  white-space: nowrap;
}

.sku-main {
  min-height: 28px;
  color: var(--pd-fg-1);
  font-size: 17px;
  letter-spacing: 0;
}

.sku-math {
  min-height: 22px;
  color: var(--pd-fg-2);
  font-size: 13px;
}

.sku-gift {
  width: fit-content;
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.64);
  border-radius: var(--pd-r-tag);
  background: rgba(255, 198, 107, 0.34);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
  color: var(--pd-fg-2);
  font-size: 12px;
  padding: 3px 9px;
}

.sku-buy,
.payment-retry,
.cdk-form button {
  min-height: 42px;
  border: 1px solid rgba(218, 111, 65, 0.48);
  border-radius: 999px;
  background: rgba(255, 249, 245, 0.98);
  color: #d86131;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 900;
  transition: transform 180ms var(--pd-ease-out), box-shadow 180ms var(--pd-ease-out), border-color 180ms var(--pd-ease-out), background 180ms var(--pd-ease-out);
}

.sku-card--featured .sku-buy,
.sku-card--selected .sku-buy {
  border-color: transparent;
  background: var(--pd-gradient);
  color: #fff;
  box-shadow: var(--pd-shadow-cta);
}

.sku-buy {
  width: 100%;
  margin-top: auto;
}

.sku-buy:hover:not(:disabled),
.payment-retry:hover,
.cdk-form button:hover:not(:disabled),
.cdk-toggle:hover {
  border-color: rgba(255, 142, 83, 0.54);
  box-shadow: 0 12px 24px rgba(255, 142, 83, 0.14);
  transform: translateY(-1px);
}

.sku-buy:disabled,
.cdk-form button:disabled {
  cursor: not-allowed;
  opacity: 0.62;
  transform: none;
}

.cdk-card {
  display: grid;
  gap: 10px;
  background: #fff;
  box-shadow: 0 8px 22px rgba(45, 45, 45, 0.07);
  padding: 12px 13px;
}

.payment-view {
  width: min(100%, 520px);
  justify-self: center;
  min-height: 0;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(45, 45, 45, 0.1);
  overflow: hidden;
  padding: clamp(15px, 2.6vw, 22px);
}

.payment-view__summary {
  display: grid;
  justify-items: center;
  gap: 6px;
  text-align: center;
}

.payment-view__summary strong,
.payment-view--success h3,
.cdk-toggle strong {
  color: var(--pd-fg-1);
  font-weight: 900;
}

.payment-view__summary em {
  color: var(--pd-orange);
  font-family: var(--pd-font-display);
  font-size: 30px;
  font-style: normal;
  font-weight: 900;
  line-height: 1;
}

.wechat-pay-card {
  width: min(292px, 76vw);
  display: grid;
  justify-items: center;
  gap: 12px;
  border: 1px solid rgba(224, 226, 230, 0.98);
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(45, 45, 45, 0.1);
  padding: 15px 14px 16px;
}

.wechat-pay-card__head {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 999px;
  background: rgba(7, 193, 96, 0.1);
  color: #07c160;
  font-size: 13px;
  font-weight: 900;
  padding: 4px 10px;
}

.wechat-pay-card__icon {
  width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
}

.wechat-pay-card__icon svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.9;
}

.payment-qr-frame {
  width: min(214px, 58vw);
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  border: 1px solid rgba(223, 223, 223, 0.92);
  border-radius: 16px;
  background: #fff;
  box-shadow: inset 0 0 0 8px #fff;
  padding: 12px;
}

.payment-qr-placeholder {
  display: grid;
  place-items: center;
  color: var(--pd-orange);
  font-weight: 900;
}

.payment-countdown,
.payment-message,
.payment-error,
.cdk-success,
.cdk-error,
.cdk-toggle span {
  margin: 0;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 800;
}

.payment-countdown {
  border-radius: 999px;
  background: rgba(7, 193, 96, 0.1);
  color: #087b42;
  padding: 5px 10px;
}

.payment-qr {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.payment-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.payment-back,
.payment-retry {
  min-height: 42px;
  border: 1px solid rgba(218, 111, 65, 0.4);
  border-radius: 999px;
  background: rgba(255, 249, 245, 0.96);
  color: #d86131;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 900;
  padding: 0 16px;
  transition: transform 180ms var(--pd-ease-out), box-shadow 180ms var(--pd-ease-out), border-color 180ms var(--pd-ease-out);
}

.payment-back:hover:not(:disabled),
.payment-retry:hover:not(:disabled) {
  border-color: rgba(255, 142, 83, 0.54);
  box-shadow: 0 12px 24px rgba(255, 142, 83, 0.14);
  transform: translateY(-1px);
}

.payment-back:disabled {
  cursor: not-allowed;
  opacity: 0.62;
}

.payment-retry {
  background: var(--pd-gradient);
  color: #fff;
}

.payment-success-mark {
  width: 76px;
  height: 76px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: linear-gradient(135deg, #ffa16f 0%, #ff6f8f 100%);
  color: #fff;
  font-size: 42px;
  font-weight: 900;
  box-shadow: var(--pd-shadow-cta);
}

.payment-view--success h3,
.payment-view--success p,
.payment-view--success span {
  margin: 0;
  text-align: center;
}

.cdk-toggle {
  min-height: 38px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid transparent;
  border-radius: 16px;
  background: transparent;
  cursor: pointer;
  font: inherit;
  padding: 0;
  transition: transform 180ms var(--pd-ease-out), box-shadow 180ms var(--pd-ease-out), border-color 180ms var(--pd-ease-out), background 180ms var(--pd-ease-out);
}

.cdk-card--open .cdk-toggle {
  border-color: rgba(255, 142, 83, 0.16);
  background: rgba(255, 248, 242, 0.72);
  padding: 0 10px;
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
  background: rgba(255, 255, 255, 0.92);
  color: var(--pd-fg-1);
  font: inherit;
  font-size: 16px;
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

@media (max-width: 720px) {
  .pricing-backdrop {
    align-items: end;
    padding: 9px;
  }

  .pricing-modal {
    width: 100%;
    max-height: calc(100dvh - 18px);
    border-radius: 24px;
    gap: 11px;
    padding: 16px;
  }

  .pricing-header {
    padding-right: 32px;
  }

  .pricing-summary {
    display: flex;
    align-items: flex-start;
  }

  .pricing-wallet-line {
    white-space: normal;
  }

  .pricing-panel {
    max-height: calc(100dvh - 255px);
    padding: 13px;
  }

  .sku-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .sku-card,
  .sku-card--featured,
  .sku-card--featured:hover {
    min-height: 218px;
    transform: none;
  }

  .sku-card--featured {
    min-height: 238px;
  }

  .sku-buy {
    min-width: 0;
    padding-inline: 14px;
  }

  .payment-view {
    padding: 14px;
  }

  .payment-qr-frame {
    width: min(204px, 58vw);
  }
}

@media (max-width: 420px) {
  .pricing-modal {
    padding: 14px;
  }

  .pricing-header h2 {
    font-size: 30px;
  }

  .pricing-tabs button {
    min-height: 40px;
    font-size: 14px;
  }

  .pricing-panel {
    padding: 12px;
  }

  .payment-view {
    padding: 12px;
  }

  .payment-qr-frame {
    width: min(184px, 60vw);
    border-radius: 20px;
  }

  .sku-card {
    padding: 12px;
  }

  .sku-price {
    font-size: 31px;
  }

  .cdk-form {
    grid-template-columns: 1fr;
  }
}
</style>
