<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';

import { ApiError, createOrder, getOrder, getSkus, redeemCdk } from '../api';
import { API_BASE } from '../api/client';
import type { Order, PaymentSku, PaymentSkuCategory, PaymentSkuCatalog, PaymentSkuId } from '../api/types';
import { useAuthStore } from '../stores/auth';

type PricingReason = 'manual' | 'ai-low' | 'script-low';

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
const cdkExpanded = ref(false);
const cdkInputRef = ref<HTMLInputElement | null>(null);

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
const activeSkus = computed(() => {
  const skus = activePanel.value === 'points' ? pointsSkus.value : membershipSkus.value;
  return [...skus].sort((left, right) => skuSortRank(left) - skuSortRank(right));
});
const activePanelTitle = computed(() => activePanel.value === 'points' ? 'AI 积分' : '时间卡会员');
const activePanelSubtitle = computed(() => activePanel.value === 'points' ? `${aiCostLabel.value} 积分 / 张` : '普通模式不限次');
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
      cdkExpanded.value = props.focusCdk;
      void loadSkus().then(() => {
        selectRecommendedSku();
        if (props.focusCdk) {
          void focusCdkInput();
        }
      });
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
  return `赠 ${sku.gift_points || 0} 积分 · ≈ ${skuAiCount(sku)} 张 AI`;
}

function skuSellLine(sku: PaymentSku): string {
  return sku.subtitle || (sku.category === 'points' ? 'AI 图纸更精细' : '普通模式放心做');
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
            <h2 id="pricing-title">充值中心</h2>
            <div class="pricing-summary">
              <span>AI {{ aiCostLabel }} 积分/张，成功才扣；时间卡解锁普通不限。</span>
              <details class="pricing-info">
                <summary aria-label="查看计费说明">ⓘ</summary>
                <p>时间卡只解锁普通模式不限次；AI 仍按 {{ aiCostLabel }} 积分/张。月卡会赠送积分，相当于间接抵 AI 生成。</p>
              </details>
            </div>
            <p v-if="props.reason !== 'manual'" class="pricing-context">{{ reasonText }} 生成成功才扣，失败不扣。</p>
            <p v-if="isLoggedIn && !isUnlimitedAccount" class="pricing-wallet-line">
              当前 {{ aiBalance }} 积分 · 可生成 AI {{ aiGenerations }}{{ aiGenerationsUnit }} · {{ membershipLabel }}
            </p>
            <p v-if="!isLoggedIn" class="pricing-guest-note">未登录状态暂按 0 余额展示。购买或兑换前请先登录/注册，避免换设备后余额丢失。</p>
          </header>

          <nav class="pricing-tabs" aria-label="充值类型">
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

          <div v-if="skuError" class="pricing-alert pricing-alert--error">{{ skuError }}</div>
          <div v-else-if="loadingSkus" class="pricing-loading">正在加载套餐…</div>

          <section v-else class="pricing-panel">
            <div class="pricing-panel__head">
              <strong>{{ activePanelTitle }}</strong>
              <span>{{ activePanelSubtitle }}</span>
            </div>

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
                <p class="sku-subtitle">{{ skuSellLine(sku) }}</p>
                <p class="sku-math">{{ skuValueLine(sku) }}</p>
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

            <p v-if="activePanel === 'membership'" class="pricing-panel__fineprint">
              时间卡只影响普通模式；AI 仍按积分扣，随卡赠分会进入钱包。
            </p>
          </section>

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

          <section class="cdk-card" :class="{ 'cdk-card--open': cdkExpanded }">
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
  width: min(100%, 860px);
  max-height: min(780px, calc(100dvh - 20px));
  overflow-y: auto;
  overscroll-behavior: contain;
  display: grid;
  gap: 10px;
  border: 1px solid rgba(226, 210, 194, 0.94);
  border-radius: 26px;
  background:
    radial-gradient(circle at 16% 0%, rgba(255, 176, 136, 0.2), transparent 32%),
    radial-gradient(circle at 90% 6%, rgba(255, 218, 145, 0.18), transparent 28%),
    linear-gradient(145deg, rgba(255, 253, 250, 0.99), rgba(255, 244, 237, 0.99));
  box-shadow: var(--pd-shadow-modal), 0 20px 50px rgba(93, 66, 48, 0.16);
  padding: clamp(15px, 2.4vw, 22px);
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
  display: grid;
  gap: 7px;
  border-bottom: 1px solid rgba(237, 214, 196, 0.72);
  padding-right: 38px;
  padding-bottom: 10px;
}

.pricing-header h2 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(30px, 4.8vw, 42px);
  line-height: 1.08;
}

.pricing-summary {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: fit-content;
  max-width: 100%;
  color: #6e625a;
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
  top: calc(100% + 8px);
  right: 0;
  z-index: 2;
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
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px;
  border: 1px solid rgba(255, 142, 83, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: inset 0 2px 8px rgba(93, 66, 48, 0.04);
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
  border-color: rgba(255, 142, 83, 0.18);
  background: rgba(255, 245, 238, 0.9);
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
.payment-box,
.cdk-card {
  border: 1px solid rgba(232, 208, 188, 0.88);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.86);
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
  display: grid;
  gap: 11px;
  background:
    linear-gradient(180deg, rgba(255, 250, 246, 0.92), rgba(255, 241, 233, 0.92));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72), 0 10px 28px rgba(93, 66, 48, 0.06);
  padding: 12px;
}

.pricing-panel__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(237, 214, 196, 0.64);
  padding: 0 2px 10px;
}

.pricing-panel__head strong {
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: 24px;
  line-height: 1.1;
}

.pricing-panel__head span,
.pricing-panel__fineprint {
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 900;
  text-align: right;
  white-space: nowrap;
}

.pricing-panel__fineprint {
  border-top: 1px solid rgba(237, 214, 196, 0.64);
  margin: 0;
  color: var(--pd-fg-2);
  text-align: left;
  padding-top: 9px;
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
  min-height: 224px;
  display: grid;
  grid-template-rows: auto auto auto minmax(34px, auto) auto auto;
  gap: 8px;
  border: 1px solid rgba(232, 208, 188, 0.92);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: var(--pd-shadow-card), 0 12px 28px rgba(93, 66, 48, 0.08);
  padding: 12px;
  transition: transform 180ms var(--pd-ease-out), box-shadow 180ms var(--pd-ease-out), border-color 180ms var(--pd-ease-out), background 180ms var(--pd-ease-out);
}

.sku-card:hover {
  border-color: rgba(255, 142, 83, 0.56);
  box-shadow: var(--pd-shadow-card), 0 18px 36px rgba(255, 142, 83, 0.14);
  transform: translateY(-2px);
}

.sku-card--featured {
  z-index: 1;
  border-color: rgba(255, 142, 83, 0.86);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(255, 248, 242, 0.98));
  box-shadow: 0 20px 42px rgba(255, 142, 83, 0.24), 0 6px 14px rgba(93, 66, 48, 0.1);
  transform: translateY(-4px) scale(1.018);
}

.sku-card--featured:hover {
  box-shadow: 0 24px 48px rgba(255, 111, 143, 0.24), 0 8px 16px rgba(93, 66, 48, 0.12);
  transform: translateY(-6px) scale(1.018);
}

.sku-card--selected {
  outline: 3px solid rgba(255, 142, 83, 0.12);
}

.sku-card__top {
  min-height: 28px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.sku-name {
  min-width: 0;
  color: var(--pd-fg-1);
  font-size: 16px;
  font-weight: 900;
  line-height: 1.2;
  white-space: nowrap;
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
  border-bottom: 1px solid rgba(237, 214, 196, 0.76);
  border-radius: 14px;
  background: rgba(255, 247, 241, 0.78);
  box-shadow: inset 0 1px 4px rgba(93, 66, 48, 0.04);
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(30px, 4vw, 40px);
  line-height: 1;
  padding: 7px 8px 9px;
  white-space: nowrap;
}

.sku-main,
.sku-subtitle,
.sku-math {
  margin: 0;
  font-weight: 900;
  line-height: 1.42;
}

.sku-main {
  color: var(--pd-orange);
  font-size: 15px;
  white-space: nowrap;
}

.sku-subtitle {
  display: -webkit-box;
  overflow: hidden;
  color: #6f6259;
  font-size: 12px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.sku-math {
  color: var(--pd-fg-1);
  font-size: 13px;
  white-space: nowrap;
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

.payment-box,
.cdk-card {
  display: grid;
  gap: 10px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 10px 26px rgba(93, 66, 48, 0.06);
  padding: 12px 13px;
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
.cdk-toggle strong {
  color: var(--pd-fg-1);
  font-weight: 900;
}

.payment-box__text span,
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

.payment-qr {
  width: 136px;
  height: 136px;
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

  .pricing-panel__head span {
    white-space: normal;
  }

  .sku-grid {
    grid-template-columns: 1fr;
  }

  .sku-card,
  .sku-card--featured,
  .sku-card--featured:hover {
    min-height: auto;
    transform: none;
  }

  .sku-card {
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-rows: auto auto auto auto;
    column-gap: 12px;
  }

  .sku-card__top,
  .sku-main,
  .sku-subtitle,
  .sku-math {
    grid-column: 1 / -1;
  }

  .sku-buy {
    align-self: end;
    min-width: 88px;
    padding-inline: 14px;
  }

  .payment-box {
    grid-template-columns: 1fr;
  }

  .payment-qr {
    width: min(176px, 54vw);
    height: min(176px, 54vw);
    justify-self: center;
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

  .pricing-panel__head strong {
    font-size: 21px;
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
