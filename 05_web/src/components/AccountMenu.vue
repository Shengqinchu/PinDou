<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';

import { ApiError, getWalletProfile } from '../api';
import PricingModal from './PricingModal.vue';
import styleCartoonAvatar from '../assets/brand/style-cartoon.png';
import stylePetAvatar from '../assets/brand/style-pet.png';
import stylePortraitAvatar from '../assets/brand/style-portrait.png';
import type { PaymentSkuCategory } from '../api/types';
import type { User } from '../api/types';
import { useAuthStore } from '../stores/auth';

const DEFAULT_AVATAR = '/brand/logo.png';
const AVATAR_MAX_BYTES = 2 * 1024 * 1024;
const NICKNAME_MAX = 20;
const ACCEPTED_AVATAR_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);
const SENSITIVE_WORDS = ['傻逼', '死妈', 'fuck', 'shit', 'admin', 'root', '官方', '客服', '管理员'];
const PRESET_AVATARS = [
  { label: '双吉', url: DEFAULT_AVATAR },
  { label: '萌宠', url: stylePetAvatar },
  { label: '人像', url: stylePortraitAvatar },
  { label: '卡通', url: styleCartoonAvatar }
] as const;

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const rootRef = ref<HTMLElement | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);
const menuOpen = ref(false);
const editOpen = ref(false);
const pricingOpen = ref(false);
const pricingPanel = ref<PaymentSkuCategory>('points');
const pricingFocusCdk = ref(false);
const draftNickname = ref('');
const originalNickname = ref('');
const originalAvatar = ref('');
const selectedPresetAvatar = ref('');
const localPreviewUrl = ref('');
const avatarFile = ref<File | null>(null);
const formError = ref('');
const toastMessage = ref('');
const saving = ref(false);
const profileLoading = ref(false);
const avatarFailed = ref(false);
const walletProfile = ref<User | null>(null);

let toastTimer: number | undefined;
let clockTimer: number | undefined;
const nowTick = ref(Date.now());
const ONE_MINUTE_MS = 60 * 1000;
const ONE_HOUR_MS = 60 * ONE_MINUTE_MS;
const ONE_DAY_MS = 24 * ONE_HOUR_MS;

const isLoggedIn = computed(() => auth.isLoggedIn);
const user = computed(() => auth.user);
const walletUser = computed(() => user.value || walletProfile.value);
const displayName = computed(() => auth.displayName);
const emailLabel = computed(() => user.value?.email || '邮箱未绑定');
const avatarSrc = computed(() => avatarFailed.value ? DEFAULT_AVATAR : user.value?.avatar || DEFAULT_AVATAR);
const walletAvatarSrc = computed(() => isLoggedIn.value ? avatarSrc.value : DEFAULT_AVATAR);
const walletIdentityName = computed(() => isLoggedIn.value ? displayName.value : '设备钱包');
const walletIdentityNote = computed(() => isLoggedIn.value ? emailLabel.value : '兑换 CDK 可直接用，注册后永久保存。');
const isUnlimitedAccount = computed(() => Boolean(walletUser.value?.is_unlimited_account));
const aiCost = computed(() => Number(walletUser.value?.ai_generation_cost_points || 0));
const aiPoints = computed(() => Number(walletUser.value?.ai_points_balance ?? walletUser.value?.paid_credits ?? 0));
const normalTrialRemaining = computed(() => Number(walletUser.value?.normal_trial_remaining ?? walletUser.value?.free_credits_remaining ?? 0));
const aiPointsLabel = computed(() => isUnlimitedAccount.value ? '不限' : formatInteger(aiPoints.value));
const aiGenerationsLabel = computed(() => {
  if (isUnlimitedAccount.value) {
    return '不限';
  }
  if (!aiCost.value) {
    return '同步中';
  }
  return `${Math.floor(aiPoints.value / aiCost.value)} 张`;
});
const membershipExpiresAt = computed(() => walletUser.value?.membership_expires_at || walletUser.value?.monthly_card_expires_at || null);
const membershipExpiresTime = computed(() => {
  if (!membershipExpiresAt.value) {
    return 0;
  }
  const expiresAt = Date.parse(membershipExpiresAt.value);
  return Number.isFinite(expiresAt) ? expiresAt : 0;
});
const membershipRemainingMs = computed(() => Math.max(0, membershipExpiresTime.value - nowTick.value));
const membershipActive = computed(() => {
  return membershipExpiresTime.value > nowTick.value;
});
const membershipUrgent = computed(() => membershipActive.value && membershipRemainingMs.value < ONE_DAY_MS);
const membershipRemainingText = computed(() => formatMembershipRemaining(membershipRemainingMs.value));
const membershipFullLabel = computed(() => {
  if (!membershipActive.value || !membershipExpiresAt.value) {
    return '';
  }
  return `时间卡会员 · 至 ${formatDateTime(membershipExpiresAt.value)}（${membershipRemainingText.value}）`;
});
const normalEntitlementLabel = computed(() => {
  if (isUnlimitedAccount.value) {
    return '不限';
  }
  if (membershipActive.value) {
    return membershipRemainingText.value;
  }
  if (normalTrialRemaining.value > 0) {
    return `${normalTrialRemaining.value} 次`;
  }
  return '未开通';
});
const normalPillLabel = computed(() => {
  if (isUnlimitedAccount.value) {
    return '普通 · 不限';
  }
  if (membershipActive.value) {
    return `会员 · ${membershipRemainingText.value}`;
  }
  if (normalTrialRemaining.value > 0) {
    return `普通 · 剩 ${normalTrialRemaining.value} 次`;
  }
  return '普通 · 未开通';
});
const navNormalLabel = computed(() => {
  if (isUnlimitedAccount.value) {
    return '不限';
  }
  if (membershipActive.value) {
    return membershipRemainingText.value;
  }
  if (normalTrialRemaining.value > 0) {
    return `剩 ${normalTrialRemaining.value} 次`;
  }
  return '未开通';
});
const navNormalShortLabel = computed(() => {
  if (isUnlimitedAccount.value) {
    return '不限';
  }
  if (membershipActive.value) {
    return membershipUrgent.value ? membershipRemainingText.value : '会员';
  }
  if (normalTrialRemaining.value > 0) {
    return `${normalTrialRemaining.value}次`;
  }
  return '未开通';
});
const membershipActionLabel = computed(() => membershipActive.value ? '续费' : '开通时间卡');
const membershipStatusTone = computed(() => membershipUrgent.value ? 'urgent' : membershipActive.value ? 'active' : 'idle');
const normalWalletLabel = computed(() => {
  if (isUnlimitedAccount.value) {
    return '普通模式不限次';
  }
  if (membershipActive.value) {
    return membershipFullLabel.value;
  }
  if (normalTrialRemaining.value > 0) {
    return `普通模式 · 剩 ${normalTrialRemaining.value} 次`;
  }
  return '普通模式 · 未开通';
});
const walletHint = computed(() => {
  if (isLoggedIn.value) {
    return '账号钱包';
  }
  return aiPoints.value > 0 || normalTrialRemaining.value > 0 || membershipActive.value
    ? '设备余额'
    : '可兑换 CDK';
});
const lowBalanceHint = computed(() => {
  if (isUnlimitedAccount.value || !aiCost.value || aiPoints.value >= aiCost.value) {
    return '';
  }
  const shortfall = Math.max(0, aiCost.value - aiPoints.value);
  return isLoggedIn.value
    ? `差 ${shortfall} 积分，充值后就能继续生成 AI 图纸。`
    : `差 ${shortfall} 积分，兑换 CDK 或注册领积分后继续。`;
});
const nicknameCount = computed(() => [...draftNickname.value.trim()].length);
const normalizedNickname = computed(() => normalizeNickname(draftNickname.value));
const nicknameError = computed(() => validateNickname(draftNickname.value));
const currentEditAvatar = computed(() => localPreviewUrl.value || selectedPresetAvatar.value || originalAvatar.value || DEFAULT_AVATAR);
const avatarBusy = computed(() => Boolean(avatarFile.value) && saving.value);
const hasEditChanges = computed(() => {
  return normalizedNickname.value !== originalNickname.value ||
    Boolean(avatarFile.value) ||
    Boolean(selectedPresetAvatar.value && selectedPresetAvatar.value !== originalAvatar.value);
});
const saveDisabled = computed(() => saving.value || Boolean(nicknameError.value) || !hasEditChanges.value);

onMounted(() => {
  document.addEventListener('click', handleDocumentClick);
  window.addEventListener('keydown', handleKeydown);
  clockTimer = window.setInterval(() => {
    nowTick.value = Date.now();
  }, ONE_MINUTE_MS);
  void refreshWalletContext({ silent: true });
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick);
  window.removeEventListener('keydown', handleKeydown);
  clearToastTimer();
  if (clockTimer !== undefined) {
    window.clearInterval(clockTimer);
    clockTimer = undefined;
  }
  revokeLocalPreview();
});

watch(
  () => route.fullPath,
  () => {
    menuOpen.value = false;
  }
);

watch(
  () => user.value?.avatar,
  () => {
    avatarFailed.value = false;
  }
);

watch(
  () => auth.isLoggedIn,
  () => {
    walletProfile.value = null;
    void refreshWalletContext({ silent: true });
  }
);

function openAccountCentre(): void { window.location.assign('/account'); }

function toggleMenu(): void {
  menuOpen.value = !menuOpen.value;
  if (menuOpen.value) {
    void refreshWalletContext();
  }
}

async function refreshWalletContext(options: { silent?: boolean } = {}): Promise<void> {
  profileLoading.value = true;
  try {
    if (auth.isLoggedIn) {
      await auth.refreshProfile();
      walletProfile.value = null;
    } else {
      walletProfile.value = await getWalletProfile();
    }
  } catch (_error) {
    if (!options.silent) {
      showToast('钱包暂时同步失败，稍后刷新即可。');
    }
  } finally {
    profileLoading.value = false;
  }
}

function openEditor(): void {
  if (!auth.user) {
    return;
  }
  originalNickname.value = normalizeNickname(auth.user.nickname || auth.displayName);
  originalAvatar.value = auth.user.avatar || '';
  draftNickname.value = originalNickname.value;
  selectedPresetAvatar.value = '';
  formError.value = '';
  editOpen.value = true;
  menuOpen.value = false;
  revokeLocalPreview();
  avatarFile.value = null;
}

function closeEditor(): void {
  if (saving.value) {
    return;
  }
  editOpen.value = false;
  formError.value = '';
  revokeLocalPreview();
  avatarFile.value = null;
}

function choosePreset(url: string): void {
  selectedPresetAvatar.value = url;
  avatarFile.value = null;
  formError.value = '';
  revokeLocalPreview();
}

function openFilePicker(): void {
  fileInputRef.value?.click();
}

function handleAvatarFile(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) {
    return;
  }
  if (!ACCEPTED_AVATAR_TYPES.has(file.type)) {
    formError.value = '头像仅支持 JPG、PNG 或 WEBP 图片。';
    return;
  }
  if (file.size > AVATAR_MAX_BYTES) {
    formError.value = '头像图片不能超过 2MB。';
    return;
  }
  revokeLocalPreview();
  localPreviewUrl.value = URL.createObjectURL(file);
  avatarFile.value = file;
  selectedPresetAvatar.value = '';
  formError.value = '保存后会上传并裁成正方形头像。';
}

async function saveProfile(): Promise<void> {
  if (!auth.user || saveDisabled.value) {
    return;
  }
  const previousUser: User = { ...auth.user };
  const nickname = normalizedNickname.value;
  const optimisticAvatar = localPreviewUrl.value || selectedPresetAvatar.value || previousUser.avatar || '';
  auth.applyUser({ ...previousUser, nickname, avatar: optimisticAvatar }, false);

  saving.value = true;
  formError.value = '';
  try {
    const payload: { nickname?: string; avatar_url?: string } = {};
    if (nickname !== originalNickname.value) {
      payload.nickname = nickname;
    }
    if (!avatarFile.value && selectedPresetAvatar.value && selectedPresetAvatar.value !== originalAvatar.value) {
      payload.avatar_url = selectedPresetAvatar.value;
    }
    if (Object.keys(payload).length) {
      await auth.updateProfile(payload);
    }
    if (avatarFile.value) {
      await auth.uploadAvatar(avatarFile.value);
    }
    await auth.refreshProfile();
    showToast('资料已更新。');
    editOpen.value = false;
    revokeLocalPreview();
    avatarFile.value = null;
  } catch (error) {
    auth.rollbackUser(previousUser);
    formError.value = readErrorMessage(error, '资料保存失败，请稍后再试。');
  } finally {
    saving.value = false;
  }
}

async function logout(): Promise<void> {
  menuOpen.value = false;
  auth.logout();
  walletProfile.value = null;
  void refreshWalletContext({ silent: true });
  await router.push('/login');
}

function goLogin(): void {
  menuOpen.value = false;
  void router.push('/login');
}

function goWorks(): void {
  menuOpen.value = false;
  void router.push('/works');
}

function openPricing(panel: PaymentSkuCategory, focusCdk = false): void {
  pricingPanel.value = panel;
  pricingFocusCdk.value = focusCdk;
  pricingOpen.value = true;
  menuOpen.value = false;
}

function openCdkPricing(): void {
  openPricing('points', true);
}

function closePricing(): void {
  pricingOpen.value = false;
  pricingFocusCdk.value = false;
}

function handlePricingSuccess(): void {
  showToast('钱包已刷新。');
  void refreshWalletContext({ silent: true });
}

function handleDocumentClick(event: MouseEvent): void {
  if (!menuOpen.value) {
    return;
  }
  const target = event.target as Node | null;
  if (target && rootRef.value?.contains(target)) {
    return;
  }
  menuOpen.value = false;
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Escape') {
    return;
  }
  if (editOpen.value) {
    closeEditor();
    return;
  }
  menuOpen.value = false;
}

function showToast(message: string): void {
  toastMessage.value = message;
  clearToastTimer();
  toastTimer = window.setTimeout(() => {
    toastMessage.value = '';
  }, 2600);
}

function clearToastTimer(): void {
  if (toastTimer) {
    window.clearTimeout(toastTimer);
    toastTimer = undefined;
  }
}

function revokeLocalPreview(): void {
  if (localPreviewUrl.value) {
    URL.revokeObjectURL(localPreviewUrl.value);
    localPreviewUrl.value = '';
  }
}

function normalizeNickname(value: string): string {
  return value.trim().replace(/\s+/g, ' ');
}

function validateNickname(value: string): string {
  const normalized = normalizeNickname(value);
  if (!normalized) {
    return '昵称不能为空。';
  }
  if ([...normalized].length > NICKNAME_MAX) {
    return '昵称最多 20 个字符。';
  }
  const lowered = normalized.toLowerCase();
  if (SENSITIVE_WORDS.some((word) => lowered.includes(word))) {
    return '这个昵称暂时不能使用，请换一个更友好的名字。';
  }
  return '';
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

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hour = String(date.getHours()).padStart(2, '0');
  const minute = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day} ${hour}:${minute}`;
}

function formatMembershipRemaining(ms: number): string {
  const safeMs = Math.max(0, ms);
  if (safeMs >= ONE_DAY_MS) {
    return `剩 ${Math.ceil(safeMs / ONE_DAY_MS)} 天`;
  }
  if (safeMs >= ONE_HOUR_MS) {
    const totalMinutes = Math.max(1, Math.ceil(safeMs / ONE_MINUTE_MS));
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return minutes > 0 ? `剩 ${hours} 小时 ${minutes} 分` : `剩 ${hours} 小时`;
  }
  return `剩 ${Math.max(1, Math.ceil(safeMs / ONE_MINUTE_MS))} 分钟`;
}

function formatInteger(value: number): string {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 }).format(Math.max(0, Math.floor(value)));
}
</script>

<template>
  <div class="account-menu" ref="rootRef">
    <RouterLink class="nav-link account-works-link" to="/works">作品集</RouterLink>

    <div
      class="wallet-pill"
      :class="{
        'wallet-pill--open': menuOpen,
        'wallet-pill--guest': !isLoggedIn,
        'wallet-pill--urgent': membershipUrgent
      }"
      role="group"
      aria-label="钱包额度"
    >
      <button
        class="wallet-pill__main"
        type="button"
        :aria-expanded="menuOpen"
        aria-haspopup="menu"
        :title="`AI ${aiPointsLabel} 积分，${normalPillLabel}`"
        @click="toggleMenu"
      >
        <span class="wallet-pill__ai-segment">
          <span class="wallet-pill__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" focusable="false">
              <path d="M12 3.8 13.8 9l5.2 1.8-5.2 1.8L12 17.8l-1.8-5.2L5 10.8 10.2 9 12 3.8Z" />
              <path d="M18.2 15.8 19 18l2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2Z" />
            </svg>
          </span>
          <span class="wallet-pill__ai">
            <span class="wallet-pill__mode wallet-pill__mode--ai">AI</span>
            <strong>{{ aiPointsLabel }}</strong>
            <em>积分</em>
          </span>
        </span>
        <span class="wallet-pill__divider" aria-hidden="true"></span>
        <span class="wallet-pill__normal" :class="`wallet-pill__normal--${membershipStatusTone}`">
          <span class="wallet-pill__normal-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" focusable="false">
              <path d="M5 5h14v14H5z" />
              <path d="M9.7 5v14M14.3 5v14M5 9.7h14M5 14.3h14" />
            </svg>
          </span>
          <span class="wallet-pill__normal-copy">
            <span class="wallet-pill__mode wallet-pill__mode--normal">普通</span>
            <span class="wallet-pill__normal-value wallet-pill__normal-value--full">{{ navNormalLabel }}</span>
            <span class="wallet-pill__normal-value wallet-pill__normal-value--short">{{ navNormalShortLabel }}</span>
          </span>
        </span>
      </button>
    </div>

    <button
      v-if="isLoggedIn"
      class="account-trigger"
      :class="{ 'account-trigger--open': menuOpen }"
      type="button"
      :aria-expanded="menuOpen"
      aria-haspopup="menu"
      @click="toggleMenu"
    >
      <img class="account-avatar" :src="avatarSrc" alt="" @error="avatarFailed = true" />
      <span class="account-trigger__name">{{ displayName }}</span>
      <span class="account-trigger__arrow" aria-hidden="true">⌄</span>
    </button>

    <RouterLink v-else class="account-login" to="/login">登录</RouterLink>

    <Transition name="account-pop">
      <section v-if="menuOpen" class="account-dropdown" role="menu" aria-label="账户菜单">
        <div class="account-identity">
          <img class="account-identity__avatar" :src="walletAvatarSrc" alt="" @error="avatarFailed = true" />
          <div>
            <strong>{{ walletIdentityName }}</strong>
            <span>{{ walletIdentityNote }}</span>
          </div>
        </div>

        <div class="account-credit-card">
          <div class="account-credit-card__head">
            <strong>我的钱包</strong>
            <span v-if="profileLoading">同步中</span>
            <span v-else>{{ walletHint }}</span>
          </div>
          <div class="account-credit-grid">
            <div>
              <span>AI 积分</span>
              <strong>{{ aiPointsLabel }}</strong>
            </div>
            <div>
              <span>可生成 AI</span>
              <strong>{{ aiGenerationsLabel }}</strong>
            </div>
            <div>
              <span>普通权益</span>
              <strong>{{ normalEntitlementLabel }}</strong>
            </div>
          </div>
          <div
            class="account-membership-line"
            :class="{ 'account-membership-line--urgent': membershipUrgent }"
          >
            <span>{{ normalWalletLabel }}</span>
            <button
              type="button"
              :class="{ 'account-membership-renew--urgent': membershipUrgent }"
              @click="openPricing('membership')"
            >
              {{ membershipActionLabel }}
            </button>
          </div>
          <p v-if="lowBalanceHint" class="account-low-hint">{{ lowBalanceHint }}</p>
          <div class="account-credit-actions">
            <button class="account-credit-action--primary" type="button" @click="openPricing('points')">充值</button>
            <button class="account-credit-action--secondary" type="button" @click="openCdkPricing">兑换 CDK</button>
            <button
              class="account-credit-action--secondary"
              :class="{ 'account-credit-action--urgent': membershipUrgent }"
              type="button"
              @click="openPricing('membership')"
            >
              {{ membershipActionLabel }}
            </button>
          </div>
        </div>

        <div class="account-menu-list">
          <button type="button" role="menuitem" @click="openAccountCentre">账号中心 · 时长与积分</button>
          <template v-if="isLoggedIn">
            <button type="button" role="menuitem" @click="openEditor">编辑资料</button>
            <button type="button" role="menuitem" @click="goWorks">我的作品</button>
            <button class="account-menu-list__danger" type="button" role="menuitem" @click="logout">退出登录</button>
          </template>
          <template v-else>
            <button type="button" role="menuitem" @click="goLogin">注册 / 登录，永久保存</button>
            <button type="button" role="menuitem" @click="goWorks">查看设备作品</button>
          </template>
        </div>
      </section>
    </Transition>

    <Teleport to="body">
      <Transition name="account-fade">
        <div v-if="editOpen" class="profile-modal" role="presentation" @click.self="closeEditor">
          <section class="profile-dialog" role="dialog" aria-modal="true" aria-label="编辑资料">
            <button class="profile-dialog__close" type="button" aria-label="关闭" @click="closeEditor">×</button>
            <span class="profile-dialog__kicker">账户资料</span>
            <h2>编辑你的 PinDou 名片</h2>

            <div class="avatar-editor">
              <img class="avatar-editor__preview" :src="currentEditAvatar" alt="当前头像预览" />
              <div class="avatar-editor__actions">
                <button class="avatar-upload-button" type="button" :disabled="saving" @click="openFilePicker">
                  {{ avatarBusy ? '上传中…' : '上传图片' }}
                </button>
                <span>JPG / PNG / WEBP，最大 2MB</span>
                <input
                  ref="fileInputRef"
                  class="sr-only"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  @change="handleAvatarFile"
                />
              </div>
            </div>

            <div class="preset-row" aria-label="预设头像">
              <button
                v-for="preset in PRESET_AVATARS"
                :key="preset.url"
                type="button"
                class="preset-avatar"
                :class="{ 'preset-avatar--active': selectedPresetAvatar === preset.url && !avatarFile }"
                :disabled="saving"
                @click="choosePreset(preset.url)"
              >
                <img :src="preset.url" :alt="preset.label" />
                <span>{{ preset.label }}</span>
              </button>
            </div>

            <label class="profile-field">
              <span>
                <strong>昵称</strong>
                <em>{{ nicknameCount }}/20</em>
              </span>
              <input
                v-model="draftNickname"
                type="text"
                autocomplete="nickname"
                :disabled="saving"
                placeholder="给自己起个暖暖的名字"
              />
            </label>

            <p v-if="nicknameError" class="profile-error">{{ nicknameError }}</p>
            <p v-else-if="formError" class="profile-note" :class="{ 'profile-note--error': !formError.includes('保存后') }">
              {{ formError }}
            </p>

            <div class="profile-actions">
              <button class="profile-cancel" type="button" :disabled="saving" @click="closeEditor">取消</button>
              <button class="profile-save" type="button" :disabled="saveDisabled" @click="saveProfile">
                {{ saving ? '保存中…' : '保存' }}
              </button>
            </div>
          </section>
        </div>
      </Transition>

      <Transition name="account-fade">
        <div v-if="toastMessage" class="account-toast" role="status">{{ toastMessage }}</div>
      </Transition>

      <PricingModal
        :open="pricingOpen"
        :initial-panel="pricingPanel"
        :focus-cdk="pricingFocusCdk"
        reason="manual"
        @close="closePricing"
        @success="handlePricingSuccess"
      />
    </Teleport>
  </div>
</template>

<style scoped>
.account-menu {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.account-works-link {
  flex: 0 0 auto;
}

.wallet-pill__main,
.account-trigger,
.account-login,
.account-dropdown button,
.profile-dialog button,
.preset-avatar {
  cursor: pointer;
}

.account-trigger,
.account-login {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 142, 83, 0.26);
  border-radius: 999px;
  background: rgba(255, 247, 240, 0.9);
  color: var(--pd-fg-1);
  font: inherit;
  font-weight: 900;
  text-decoration: none;
  transition:
    border-color 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.wallet-pill {
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  gap: 0;
  border: 1px solid rgba(255, 142, 83, 0.34);
  border-radius: 999px;
  background:
    linear-gradient(135deg, rgba(255, 249, 233, 0.96), rgba(255, 232, 216, 0.92)),
    rgba(255, 246, 239, 0.96);
  box-shadow:
    0 10px 22px rgba(255, 142, 83, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.82);
  padding: 2px;
  transition:
    border-color 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.wallet-pill:hover,
.wallet-pill--open {
  border-color: rgba(255, 142, 83, 0.62);
  background:
    linear-gradient(135deg, rgba(255, 252, 241, 0.98), rgba(255, 236, 224, 0.96)),
    #fff8f1;
  box-shadow:
    0 14px 28px rgba(255, 142, 83, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
  transform: translateY(-1px);
}

.wallet-pill--urgent {
  border-color: rgba(255, 91, 91, 0.46);
  background:
    linear-gradient(135deg, rgba(255, 247, 232, 0.98), rgba(255, 224, 216, 0.96)),
    rgba(255, 241, 234, 0.96);
  box-shadow:
    0 12px 28px rgba(255, 91, 91, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.wallet-pill__main {
  border: 0;
  font: inherit;
}

.wallet-pill__main {
  min-width: 0;
  min-height: 30px;
  display: inline-flex;
  align-items: center;
  gap: 13px;
  border-radius: 999px;
  background: transparent;
  color: var(--pd-fg-1);
  cursor: pointer;
  line-height: 1;
  padding: 0 17px 0 11px;
}

.wallet-pill__ai-segment,
.wallet-pill__normal {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  line-height: 1;
}

.wallet-pill__ai-segment {
  gap: 7px;
}

.wallet-pill__icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  color: var(--pd-orange);
}

.wallet-pill__icon svg {
  width: 16px;
  height: 16px;
  display: block;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
}

.wallet-pill__ai {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  line-height: 1;
  white-space: nowrap;
}

.wallet-pill__mode {
  display: inline-flex;
  align-items: center;
  line-height: 1;
  font-size: 12px;
  font-weight: 950;
  white-space: nowrap;
}

.wallet-pill__mode--ai {
  color: var(--pd-orange);
}

.wallet-pill__mode--normal {
  color: var(--pd-fg-2);
}

.wallet-pill__ai strong {
  color: var(--pd-fg-1);
  font-size: 16px;
  font-weight: 950;
  line-height: 1;
}

.wallet-pill__ai em {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-style: normal;
  font-weight: 900;
  line-height: 1;
}

.wallet-pill__divider {
  width: 1px;
  height: 16px;
  flex: 0 0 auto;
  background: rgba(255, 142, 83, 0.28);
  margin-inline: 2px;
}

.wallet-pill__normal {
  gap: 6px;
  color: var(--pd-fg-1);
  font-size: 12px;
  font-weight: 950;
  white-space: nowrap;
}

.wallet-pill__normal-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  color: var(--pd-fg-2);
}

.wallet-pill__normal--urgent,
.wallet-pill__normal--urgent .wallet-pill__mode--normal,
.wallet-pill__normal--urgent .wallet-pill__normal-value,
.wallet-pill__normal--urgent .wallet-pill__normal-icon {
  color: #d9503f;
}

.wallet-pill__normal-icon svg {
  width: 15px;
  height: 15px;
  display: block;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.wallet-pill__normal-copy {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  line-height: 1;
  white-space: nowrap;
}

.wallet-pill__normal-value {
  color: var(--pd-fg-1);
  font-size: 12px;
  font-weight: 950;
  line-height: 1;
}

.wallet-pill__normal-value--short {
  display: none;
}

.account-trigger {
  gap: 8px;
  padding: 0 11px 0 6px;
}

.account-trigger:hover,
.account-trigger--open,
.account-login:hover {
  border-color: rgba(255, 142, 83, 0.56);
  background: #fff;
  box-shadow: 0 14px 28px rgba(255, 142, 83, 0.15);
  transform: translateY(-1px);
}

.account-avatar {
  width: 31px;
  height: 31px;
  display: block;
  border-radius: 999px;
  object-fit: cover;
  background: #fff7ef;
  box-shadow: inset 0 0 0 1px rgba(237, 228, 218, 0.78);
}

.account-trigger__name {
  max-width: 108px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-trigger__arrow {
  color: var(--pd-orange);
  font-size: 17px;
  line-height: 1;
  transition: transform 180ms var(--pd-ease-out);
}

.account-trigger--open .account-trigger__arrow {
  transform: rotate(180deg);
}

.account-login {
  padding: 0 16px;
  white-space: nowrap;
}

.account-dropdown {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  z-index: 40;
  width: min(360px, calc(100vw - 24px));
  display: grid;
  gap: 12px;
  border: 1px solid rgba(237, 228, 218, 0.9);
  border-radius: 24px;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.995), rgba(255, 246, 239, 0.99)),
    #fffaf7;
  box-shadow: 0 24px 56px rgba(45, 45, 45, 0.13), 0 14px 34px rgba(255, 142, 83, 0.13);
  padding: 14px;
}

.account-identity {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  border-radius: 18px;
  background: rgba(255, 249, 245, 0.8);
  padding: 10px;
}

.account-identity__avatar {
  width: 52px;
  height: 52px;
  display: block;
  border-radius: 18px;
  object-fit: cover;
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(237, 228, 218, 0.8);
}

.account-identity strong,
.account-identity span {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-identity strong {
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: 18px;
  font-weight: 900;
}

.account-identity span {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 800;
}

.account-credit-card {
  display: grid;
  gap: 10px;
  border: 1px solid rgba(255, 142, 83, 0.16);
  border-radius: 18px;
  background: rgba(255, 246, 239, 0.72);
  padding: 12px;
}

.account-credit-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.account-credit-card__head strong {
  color: var(--pd-fg-1);
  font-weight: 900;
}

.account-credit-card__head span {
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 900;
}

.account-credit-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.account-credit-grid div {
  min-width: 0;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
  padding: 9px 8px;
}

.account-credit-grid span,
.account-credit-grid strong {
  display: block;
  text-align: center;
}

.account-credit-grid span {
  color: var(--pd-fg-2);
  font-size: 11px;
  font-weight: 900;
}

.account-credit-grid strong {
  color: var(--pd-fg-1);
  font-size: 14px;
  font-weight: 900;
  white-space: nowrap;
}

.account-low-hint {
  margin: 0;
  border: 1px solid rgba(255, 255, 255, 0.56);
  border-radius: var(--pd-r-tag);
  background: rgba(255, 198, 107, 0.3);
  color: var(--pd-fg-1);
  font-size: 12px;
  font-weight: 900;
  line-height: 1.45;
  padding: 7px 9px;
}

.account-membership-line {
  min-height: 38px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  border: 1px solid rgba(255, 198, 107, 0.28);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 900;
  line-height: 1.35;
  padding: 7px 8px 7px 10px;
}

.account-membership-line span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-membership-line button {
  min-height: 28px;
  border: 1px solid rgba(255, 142, 83, 0.28);
  border-radius: 999px;
  background: rgba(255, 247, 240, 0.9);
  color: var(--pd-orange);
  font: inherit;
  font-size: 12px;
  font-weight: 950;
  padding: 0 10px;
  white-space: nowrap;
}

.account-membership-line--urgent {
  border-color: rgba(255, 91, 91, 0.28);
  background: rgba(255, 236, 230, 0.74);
  color: #c74738;
}

.account-membership-renew--urgent,
.account-credit-action--urgent {
  border-color: rgba(255, 91, 91, 0.38) !important;
  background: linear-gradient(135deg, #ff9f6e 0%, #ff5f6f 100%) !important;
  color: #fff !important;
  box-shadow: 0 12px 24px rgba(255, 91, 91, 0.18);
}

.account-credit-actions {
  display: grid;
  grid-template-columns: 1fr 1fr 1.08fr;
  gap: 8px;
}

.account-credit-actions button,
.account-menu-list button {
  min-height: 38px;
  border: 1px solid rgba(255, 142, 83, 0.2);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.8);
  color: var(--pd-fg-1);
  font: inherit;
  font-weight: 900;
  transition:
    border-color 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    color 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.account-credit-actions button {
  color: var(--pd-orange);
  padding-inline: 8px;
  white-space: nowrap;
}

.account-credit-action--primary {
  border-color: rgba(255, 142, 83, 0.38) !important;
  background: linear-gradient(135deg, #ffa16f 0%, #ff6f8f 100%) !important;
  color: #fff !important;
  box-shadow: 0 12px 24px rgba(255, 111, 143, 0.18);
}

.account-credit-action--secondary {
  background: rgba(255, 255, 255, 0.82);
}

.account-menu-list {
  display: grid;
  gap: 8px;
}

.account-menu-list button {
  width: 100%;
  text-align: left;
  padding: 0 12px;
}

.account-credit-actions button:hover,
.account-menu-list button:hover {
  border-color: rgba(255, 142, 83, 0.48);
  background: #fff;
  box-shadow: 0 12px 24px rgba(255, 142, 83, 0.13);
  transform: translateY(-1px);
}

.account-credit-action--primary:hover {
  border-color: rgba(255, 142, 83, 0.56) !important;
  background: linear-gradient(135deg, #ffad7e 0%, #ff6389 100%) !important;
  box-shadow: 0 16px 30px rgba(255, 111, 143, 0.24) !important;
}

.account-menu-list__danger {
  color: #e35151 !important;
}

.profile-modal {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  background: rgba(45, 36, 30, 0.28);
  backdrop-filter: blur(8px);
  padding: 18px;
}

.profile-dialog {
  position: relative;
  width: min(100%, 500px);
  max-height: min(720px, calc(100dvh - 36px));
  overflow-y: auto;
  overscroll-behavior: contain;
  display: grid;
  gap: 14px;
  border: 1px solid rgba(237, 228, 218, 0.9);
  border-radius: 28px;
  background:
    linear-gradient(145deg, #fff, #fff4ec),
    #fffaf7;
  box-shadow: var(--pd-shadow-modal), 0 18px 44px rgba(255, 142, 83, 0.18);
  padding: 24px;
}

.profile-dialog__close {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 142, 83, 0.22);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--pd-fg-2);
  font: inherit;
  font-size: 20px;
  font-weight: 900;
  line-height: 1;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    color 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.profile-dialog__close:hover {
  border-color: rgba(255, 142, 83, 0.5);
  box-shadow: 0 10px 20px rgba(255, 142, 83, 0.14);
  color: var(--pd-orange);
  transform: translateY(-1px);
}

.profile-dialog__kicker {
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 900;
}

.profile-dialog h2 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-display);
  font-size: clamp(26px, 4vw, 36px);
  line-height: 1.1;
}

.avatar-editor {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 14px;
  align-items: center;
}

.avatar-editor__preview {
  width: 96px;
  height: 96px;
  display: block;
  border: 1px solid rgba(237, 228, 218, 0.9);
  border-radius: 28px;
  object-fit: cover;
  background: #fff;
  box-shadow: 0 12px 26px rgba(255, 142, 83, 0.12);
}

.avatar-editor__actions {
  display: grid;
  gap: 8px;
  justify-items: start;
}

.avatar-editor__actions span,
.profile-field em,
.profile-note,
.profile-error {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
}

.avatar-upload-button,
.profile-cancel,
.profile-save {
  min-height: 42px;
  border-radius: 999px;
  font: inherit;
  font-weight: 900;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    filter 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.avatar-upload-button {
  border: 1px solid rgba(255, 142, 83, 0.28);
  background: rgba(255, 241, 232, 0.9);
  color: var(--pd-orange);
  padding: 0 18px;
}

.avatar-upload-button:hover:not(:disabled),
.profile-cancel:hover:not(:disabled),
.profile-save:hover:not(:disabled),
.preset-avatar:hover:not(:disabled) {
  border-color: rgba(255, 142, 83, 0.52);
  box-shadow: 0 12px 24px rgba(255, 142, 83, 0.14);
  filter: brightness(1.02);
  transform: translateY(-1px);
}

.preset-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 9px;
}

.preset-avatar {
  min-width: 0;
  display: grid;
  justify-items: center;
  gap: 5px;
  border: 1px solid rgba(237, 228, 218, 0.86);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--pd-fg-2);
  font: inherit;
  font-size: 12px;
  font-weight: 900;
  padding: 8px 5px;
  transition:
    border-color 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    color 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.preset-avatar img {
  width: 44px;
  height: 44px;
  display: block;
  object-fit: contain;
}

.preset-avatar--active {
  border-color: transparent;
  background: var(--pd-gradient-warm);
  color: #fff;
  box-shadow: var(--pd-shadow-cta);
}

.profile-field {
  display: grid;
  gap: 8px;
}

.profile-field > span {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.profile-field strong {
  color: var(--pd-fg-1);
  font-weight: 900;
}

.profile-field input {
  width: 100%;
  min-width: 0;
  height: 48px;
  border: 1px solid rgba(255, 142, 83, 0.28);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--pd-fg-1);
  font: inherit;
  font-size: 16px;
  font-weight: 900;
  outline: none;
  padding: 0 14px;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out);
}

.profile-field input:focus {
  border-color: rgba(255, 142, 83, 0.72);
  box-shadow: 0 0 0 4px rgba(255, 142, 83, 0.12);
}

.profile-error,
.profile-note--error {
  color: #e35151;
}

.profile-note {
  margin: -2px 0 0;
}

.profile-error {
  margin: -2px 0 0;
}

.profile-actions {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 10px;
}

.profile-cancel {
  border: 1px solid rgba(255, 142, 83, 0.24);
  background: rgba(255, 241, 232, 0.7);
  color: var(--pd-orange);
}

.profile-save {
  border: 1px solid transparent;
  background: var(--pd-gradient);
  color: #fff;
  box-shadow: var(--pd-shadow-cta);
}

.profile-save:disabled,
.profile-cancel:disabled,
.avatar-upload-button:disabled,
.preset-avatar:disabled {
  cursor: not-allowed;
  filter: grayscale(0.15);
  opacity: 0.68;
  transform: none;
}

.account-toast {
  position: fixed;
  top: 76px;
  right: clamp(14px, 4vw, 72px);
  z-index: 80;
  max-width: min(360px, calc(100vw - 28px));
  border: 1px solid rgba(255, 142, 83, 0.26);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 18px 40px rgba(45, 45, 45, 0.12), 0 10px 20px rgba(255, 142, 83, 0.12);
  color: var(--pd-fg-1);
  font-size: 13px;
  font-weight: 900;
  padding: 10px 14px;
}

.account-pop-enter-active,
.account-pop-leave-active,
.account-fade-enter-active,
.account-fade-leave-active {
  transition:
    opacity 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.account-pop-enter-from,
.account-pop-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.98);
}

.account-fade-enter-from,
.account-fade-leave-to {
  opacity: 0;
}

@media (max-width: 720px) {
  .account-menu {
    gap: 6px;
  }

  .wallet-pill {
    min-height: 36px;
    padding: 2px;
  }

  .wallet-pill__main {
    min-height: 30px;
    gap: 8px;
    padding-inline: 8px 10px;
  }

  .wallet-pill__icon {
    width: 16px;
    height: 16px;
  }

  .wallet-pill__ai strong {
    font-size: 14px;
  }

  .account-trigger {
    min-height: 36px;
    padding-right: 8px;
  }

  .account-avatar {
    width: 28px;
    height: 28px;
  }

  .account-trigger__name {
    max-width: 74px;
  }

  .account-dropdown {
    position: fixed;
    top: 70px;
    left: 12px;
    right: 12px;
    width: auto;
    max-height: calc(100dvh - 86px);
    overflow-y: auto;
    background: #fffaf7;
    box-shadow: 0 24px 56px rgba(45, 45, 45, 0.18), 0 12px 28px rgba(255, 142, 83, 0.18);
  }
}

@media (max-width: 520px) {
  .wallet-pill__main {
    gap: 6px;
    padding-inline: 8px;
  }

  .wallet-pill__ai-segment,
  .wallet-pill__normal {
    gap: 0;
  }

  .wallet-pill__ai,
  .wallet-pill__normal-copy {
    gap: 4px;
  }

  .wallet-pill__icon,
  .wallet-pill__normal-icon,
  .wallet-pill__ai em {
    display: none;
  }

  .wallet-pill__mode,
  .wallet-pill__normal-value {
    font-size: 11px;
  }

  .wallet-pill__divider {
    margin-inline: 0;
  }

  .wallet-pill__normal-value--full {
    display: none;
  }

  .wallet-pill__normal-value--short {
    display: inline-flex;
  }

  .account-trigger__name {
    display: none;
  }
}

@media (max-width: 430px) {
  .account-works-link {
    padding-inline: 10px;
  }

  .account-credit-grid {
    grid-template-columns: 1fr;
  }

  .account-credit-actions {
    display: grid;
    grid-template-columns: 1fr;
  }

  .profile-modal {
    place-items: end center;
    padding: 10px;
  }

  .profile-dialog {
    width: 100%;
    max-height: calc(100dvh - 20px);
    background: #fffaf7;
    border-radius: 24px;
    padding: 20px;
  }

  .avatar-editor {
    grid-template-columns: 78px minmax(0, 1fr);
  }

  .avatar-editor__preview {
    width: 78px;
    height: 78px;
    border-radius: 22px;
  }

  .preset-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
