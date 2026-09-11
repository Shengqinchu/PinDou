<script setup lang="ts">
import { computed, ref,watch } from 'vue';
import { onShow, onUnload } from '@dcloudio/uni-app';
import accountCopy from '../../../../05_studio/src/content/account.json';
import walletCopy from '../../../../05_studio/src/content/wallet.json';
import bookingCopy from '../../../../05_studio/src/content/booking-profile.json';
import visitCopy from '../../../../05_studio/src/content/pages-Visit.json';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import StudioLegalLinks from '../../components/StudioLegalLinks.vue';
import { useStudioNative } from '../../utils/studio-native';
import { MiniappError } from '../../utils/miniapp-client';
import {peekStudioSnapshot,readStudioCached} from '../../utils/studio-cache';
import { useUserStore } from '../../store/user';
import profileCopy from '../../../../05_studio/src/content/profile.json';
type Profile = {nickname:string;email:string;avatar?:string};
type Wallet = {account:{minutes:number;points:number};booking_profile:{name:string;contact_method:string;contact:string;complete:boolean}};
const user = useUserStore();
const { language, keyboardOpen, shellStyle, say, t, changeLanguage, website } = useStudioNative();
const profile = ref<Profile>(), wallet = ref<Wallet>(), busy = ref(false), failed = ref(false), avatarFailed = ref(false);
let sequence = 0;
const name = computed(() => profile.value?.nickname || profile.value?.email || user.userInfo?.nickname || user.userInfo?.email || '—');
const hours = computed(() => wallet.value ? say(walletCopy.whole_hours).replace('{v0}',String(Math.round(wallet.value.account.minutes / 60 * 100) / 100)) : '—');
const contactLabel = computed(() => say(({wechat:visitCopy.wechat_2941d2,phone:visitCopy.phone_ac7a62,email:accountCopy.email,other:visitCopy.another_way_f489b4} as Record<string,string[]>)[wallet.value?.booking_profile?.contact_method || 'wechat'] || bookingCopy.contact));
const avatar = computed(() => {
  const value = profile.value?.avatar || '';
  return value.startsWith('/') ? 'https://pindoupuppy.com' + value : /^https:\/\//.test(value) ? value : '';
});
async function refresh(force=false) {
  if (busy.value) return;
  if (!user.token) { uni.redirectTo({url:'/pages/auth/studio-login'}); return; }
  const token = user.token, current = ++sequence;
  failed.value=false;
  const cachedProfile=peekStudioSnapshot<{user:Profile}>('/auth/me',token),cachedWallet=peekStudioSnapshot<Wallet>('/auth/wallet',token);
  if(cachedProfile){if(cachedProfile.data.user.avatar!==profile.value?.avatar)avatarFailed.value=false;profile.value=cachedProfile.data.user;}
  if(cachedWallet)wallet.value=cachedWallet.data;
  if(!force&&cachedProfile&&cachedWallet&&cachedProfile.age<30000&&cachedWallet.age<30000)return;
  busy.value = true; failed.value = false;
  const results = await Promise.allSettled([
    readStudioCached<{user:Profile}>('/auth/me',token,30000,force), readStudioCached<Wallet>('/auth/wallet',token,30000,force),
  ]);
  if (current !== sequence || token !== user.token) return;
  if (results.some(result => result.status === 'rejected' && result.reason instanceof MiniappError && result.reason.status === 401)) { logout(); return; }
  if (results[0].status === 'fulfilled') {
    const next = results[0].value.user;
    if (next.avatar !== profile.value?.avatar) avatarFailed.value = false;
    profile.value = {nickname:next.nickname,email:next.email,avatar:next.avatar};
  }
  if (results[1].status === 'fulfilled') {
    const next = results[1].value;
    wallet.value = {account:{minutes:next.account.minutes,points:next.account.points},booking_profile:next.booking_profile};
  }
  failed.value = results.some(result => result.status === 'rejected'); busy.value = false;
}
function logout() { ++sequence; user.logout(); profile.value = undefined; wallet.value = undefined; uni.reLaunch({url:'/pages/auth/studio-login'}); }
function patterns() { uni.navigateTo({url:'/pages/upload/upload'}); }
function visit() { uni.navigateTo({url:'/pages/studio/visit'}); }
function reservations() { uni.navigateTo({url:'/pages/studio/reservations'}); }
function edit() { uni.navigateTo({url:'/pages/auth/studio-profile'}); }
watch(()=>user.token,()=>{sequence++;profile.value=undefined;wallet.value=undefined;busy.value=false;failed.value=false;});
onShow(() => void refresh());
onUnload(() => { ++sequence; });
</script>
<template>
  <StudioShell id="studio-shell" fitted :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" nav="account" @language="changeLanguage">
    <view class="studio-native-main studio-account">
      <view class="studio-native-section-head"><text class="studio-native-title">{{say(accountCopy.account)}}</text><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-eye" :disabled="busy" :aria-label="say(walletCopy.refresh)" hover-class="studio-native-pressed" @tap="refresh(true)"><view v-if="busy" class="studio-native-progress"/><StudioGlyph v-else name="refresh" :size="21"/></button></view>
      <view class="studio-native-profile">
        <button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-avatar-edit" :aria-label="say(profileCopy.edit)" @tap="edit"><image v-if="avatar&&!avatarFailed" class="studio-native-avatar" :src="avatar" mode="aspectFill" @error="avatarFailed=true"/><view v-else class="studio-native-avatar"><StudioGlyph name="user" :size="28"/></view></button>
        <view class="studio-native-profile-text"><text class="studio-native-name">{{name}}</text><text v-if="profile?.email&&profile.email!==name" class="studio-native-body">{{profile.email}}</text><text class="studio-native-label">{{say(accountCopy.signed_in)}}</text></view>
        <button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-link studio-profile-edit" @tap="edit">{{say(profileCopy.edit)}}</button>
      </view>
      <text v-if="failed" class="studio-native-error" role="alert">{{t('generic_error')}}</text>
      <view v-if="busy&&!wallet" class="studio-native-status"><view class="studio-native-progress"/><text class="studio-native-body">{{say(walletCopy.loading)}}</text></view>
      <view class="studio-native-balances">
        <view class="studio-native-balance"><text class="studio-native-label">{{say(walletCopy.remaining_time)}}</text><text class="studio-native-balance-value">{{hours}}</text></view>
        <view class="studio-native-balance"><text class="studio-native-label">{{say(walletCopy.remaining_points)}}</text><text class="studio-native-balance-value">{{wallet?wallet.account.points:'—'}}</text></view>
      </view>
      <view v-if="wallet" class="studio-native-section">
        <view class="studio-native-section-head"><text class="studio-native-subtitle">{{say(bookingCopy.title)}}</text><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-link" @tap="edit">{{say(bookingCopy.edit)}}</button></view>
        <view class="studio-native-definition">
          <template v-if="wallet.booking_profile?.complete">
            <view class="studio-native-definition-row"><text class="studio-native-label">{{say(bookingCopy.name)}}</text><text class="studio-native-account-value">{{wallet.booking_profile.name}}</text></view>
            <view class="studio-native-definition-row"><text class="studio-native-label">{{contactLabel}}</text><text class="studio-native-account-value" selectable>{{wallet.booking_profile.contact}}</text></view>
          </template>
          <text v-else class="studio-native-body">{{say(bookingCopy.empty)}}</text>
        </view>
      </view>
      <view class="studio-native-menu"><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-menu-row" hover-class="studio-native-pressed" @tap="visit"><StudioGlyph name="calendar"/><text class="studio-native-menu-label">{{say(visitCopy.come_make_something_f834ec)}}</text><StudioGlyph name="arrow" :size="18"/></button><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-menu-row" hover-class="studio-native-pressed" @tap="patterns"><StudioGlyph name="grid"/><text class="studio-native-menu-label">{{say(accountCopy.pattern_tool)}}</text><StudioGlyph name="arrow" :size="18"/></button></view>
      <view class="studio-account-end"><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-link" hover-class="studio-native-pressed" @tap="logout">{{say(accountCopy.sign_out)}}</button><StudioLegalLinks :language="language"/></view>
    </view>
  </StudioShell>
</template>

<style scoped>
.studio-account-end{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}
</style>
