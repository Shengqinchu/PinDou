<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';

import { ApiError } from '../api';
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

let toastTimer: number | undefined;

const isLoggedIn = computed(() => auth.isLoggedIn);
const user = computed(() => auth.user);
const displayName = computed(() => auth.displayName);
const emailLabel = computed(() => user.value?.email || '邮箱未绑定');
const avatarSrc = computed(() => avatarFailed.value ? DEFAULT_AVATAR : user.value?.avatar || DEFAULT_AVATAR);
const isUnlimitedAccount = computed(() => Boolean(user.value?.is_unlimited_account));
const aiCost = computed(() => Number(user.value?.ai_generation_cost_points || 0));
const aiPoints = computed(() => Number(user.value?.ai_points_balance ?? user.value?.paid_credits ?? 0));
const normalTrialRemaining = computed(() => Number(user.value?.normal_trial_remaining ?? user.value?.free_credits_remaining ?? 0));
const aiPointsLabel = computed(() => isUnlimitedAccount.value ? '不限' : `${aiPoints.value} 分`);
const aiGenerationsLabel = computed(() => {
  if (isUnlimitedAccount.value) {
    return '不限';
  }
  if (!aiCost.value) {
    return '同步中';
  }
  return `${Math.floor(aiPoints.value / aiCost.value)} 张`;
});
const membershipExpiresAt = computed(() => user.value?.membership_expires_at || user.value?.monthly_card_expires_at || null);
const membershipActive = computed(() => {
  if (!membershipExpiresAt.value) {
    return false;
  }
  const expiresAt = Date.parse(membershipExpiresAt.value);
  return Number.isFinite(expiresAt) && expiresAt > Date.now();
});
const normalEntitlementLabel = computed(() => {
  if (isUnlimitedAccount.value) {
    return '不限';
  }
  if (membershipActive.value && membershipExpiresAt.value) {
    return `会员至 ${formatMonthDay(membershipExpiresAt.value)}`;
  }
  return `${normalTrialRemaining.value} 次`;
});
const lowBalanceHint = computed(() => {
  if (isUnlimitedAccount.value || !aiCost.value || aiPoints.value >= aiCost.value) {
    return '';
  }
  const shortfall = Math.max(0, aiCost.value - aiPoints.value);
  return `差 ${shortfall} 积分，充值后就能继续生成 AI 图纸。`;
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
  if (auth.isLoggedIn && (!auth.user || auth.user.ai_generation_cost_points == null)) {
    void refreshProfile();
  }
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick);
  window.removeEventListener('keydown', handleKeydown);
  clearToastTimer();
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

function toggleMenu(): void {
  if (!auth.isLoggedIn) {
    void router.push('/login');
    return;
  }
  menuOpen.value = !menuOpen.value;
  if (menuOpen.value && !auth.user) {
    void refreshProfile();
  }
}

async function refreshProfile(): Promise<void> {
  profileLoading.value = true;
  try {
    await auth.refreshProfile();
  } catch (_error) {
    showToast('资料暂时加载失败，稍后刷新即可。');
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
  await router.push('/login');
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

function formatMonthDay(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return `${date.getMonth() + 1}/${date.getDate()}`;
}
</script>

<template>
  <div class="account-menu" ref="rootRef">
    <RouterLink class="nav-link account-works-link" to="/works">作品集</RouterLink>

    <button
      v-if="isLoggedIn"
      class="credit-chip"
      type="button"
      title="当前可用额度"
      @click="toggleMenu"
    >
      <span aria-hidden="true">🫘</span>
      <strong>AI {{ aiPointsLabel }}</strong>
    </button>

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
      <section v-if="menuOpen && isLoggedIn" class="account-dropdown" role="menu" aria-label="账户菜单">
        <div class="account-identity">
          <img class="account-identity__avatar" :src="avatarSrc" alt="" @error="avatarFailed = true" />
          <div>
            <strong>{{ displayName }}</strong>
            <span>{{ emailLabel }}</span>
          </div>
        </div>

        <div class="account-credit-card">
          <div class="account-credit-card__head">
            <strong>我的钱包</strong>
            <span v-if="profileLoading">同步中</span>
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
          <p v-if="lowBalanceHint" class="account-low-hint">{{ lowBalanceHint }}</p>
          <div class="account-credit-actions">
            <button class="account-credit-action--primary" type="button" @click="openPricing('points')">充值 / 开通会员</button>
            <button class="account-credit-action--secondary" type="button" @click="openCdkPricing">兑换 CDK</button>
          </div>
        </div>

        <div class="account-menu-list">
          <button type="button" role="menuitem" @click="openEditor">编辑资料</button>
          <button type="button" role="menuitem" @click="goWorks">我的作品</button>
          <button class="account-menu-list__danger" type="button" role="menuitem" @click="logout">退出登录</button>
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

.credit-chip,
.account-trigger,
.account-login,
.account-dropdown button,
.profile-dialog button,
.preset-avatar {
  cursor: pointer;
}

.credit-chip,
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

.credit-chip {
  gap: 5px;
  padding: 0 12px;
  color: var(--pd-orange);
  box-shadow: inset 0 -1px 0 rgba(255, 142, 83, 0.12);
}

.credit-chip strong {
  white-space: nowrap;
}

.account-trigger {
  gap: 8px;
  padding: 0 11px 0 6px;
}

.credit-chip:hover,
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

.account-credit-actions {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(96px, 0.75fr);
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

  .credit-chip {
    min-height: 36px;
    padding: 0 9px;
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
  .account-trigger__name {
    display: none;
  }
}

@media (max-width: 430px) {
  .credit-chip strong {
    display: none;
  }

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
