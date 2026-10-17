<script setup lang="ts">
defineOptions({options:{styleIsolation:'shared',virtualHost:true}});
import { computed, ref,watch } from 'vue';
import {onViewShow as onShow,onViewUnload as onUnload} from '../../utils/studio-view-lifecycle';
import accountCopy from '../../../../05_studio/src/content/account.json';
import walletCopy from '../../../../05_studio/src/content/wallet.json';
import bookingCopy from '../../../../05_studio/src/content/booking-profile.json';
import visitCopy from '../../../../05_studio/src/content/pages-Visit.json';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import StudioLegalLinks from '../../components/StudioLegalLinks.vue';
import { useStudioNative } from '../../utils/studio-native';
import { MiniappError } from '../../utils/miniapp-client';
import {pressTo,pressNavigate} from '../../utils/press';
import {peekStudioSnapshot,readStudioCached} from '../../utils/studio-cache';
import { useUserStore } from '../../store/studio-user';
import profileCopy from '../../../../05_studio/src/content/profile.json';
import ownerCopy from '../../../../05_studio/src/content/owner-wechat.json';
import workbenchCopy from '../../../../05_studio/src/content/workbench.json';
import noticeCopy from '../../../../05_studio/src/content/customer-notifications.json';
function notices(){pressTo('/pages/studio/notifications');}
type Profile = {nickname:string;email:string;avatar?:string;is_admin?:boolean;customer_code?:string};
type Wallet = {account:{minutes:number;points:number};booking_profile:{name:string;contact_method:string;contact:string;complete:boolean}};
const user = useUserStore();
const { language, keyboardOpen, shellStyle, say, t, changeLanguage, website } = useStudioNative();
const profile = ref<Profile>(), wallet = ref<Wallet>(), busy = ref(false), failed = ref(false), avatarFailed = ref(false);
const isOwner=ref(false),pageReset=ref(0),pointsHelpOpen=ref(false);
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
  const cachedOwner=peekStudioSnapshot<{bound:boolean}>('/auth/owner-notifications',token);
  if(cachedOwner)isOwner.value=cachedOwner.data.bound;
  if(cachedProfile){if(cachedProfile.data.user.avatar!==profile.value?.avatar)avatarFailed.value=false;profile.value=cachedProfile.data.user;}
  if(cachedWallet)wallet.value=cachedWallet.data;
  if(!force&&cachedProfile&&cachedWallet&&cachedOwner&&cachedProfile.age<30000&&cachedWallet.age<30000&&cachedOwner.age<30000)return;
  busy.value = true; failed.value = false;
  const valid=()=>current===sequence&&token===user.token;
  const rejected=(error:unknown,critical=true)=>{if(!valid())return;if(error instanceof MiniappError&&error.status===401){logout();return;}if(critical)failed.value=true;else isOwner.value=false;};
  // Render each completed section immediately. Owner-alert metadata must not
  // keep the profile, balance and administrator entry behind its request.
  const core=Promise.allSettled([
    readStudioCached<{user:Profile}>('/auth/me',token,30000,force).then(value=>{if(!valid())return;const next=value.user;if(next.avatar!==profile.value?.avatar)avatarFailed.value=false;profile.value=next;}).catch(e=>rejected(e)),
    readStudioCached<Wallet>('/auth/wallet',token,30000,force).then(value=>{if(valid())wallet.value={account:{minutes:value.account.minutes,points:value.account.points},booking_profile:value.booking_profile};}).catch(e=>rejected(e)),
  ]).finally(()=>{if(valid())busy.value=false;});
  const owner=readStudioCached<{bound:boolean}>('/auth/owner-notifications',token,30000,force).then(value=>{if(valid())isOwner.value=value.bound;}).catch(e=>rejected(e,false));
  await Promise.allSettled([core,owner]);
}
function logout() { ++sequence; user.logout(); profile.value = undefined; wallet.value = undefined; uni.reLaunch({url:'/pages/auth/studio-login'}); }
function visit() { pressTo('/pages/studio/visit'); }
function reservations() { pressNavigate('/pages/studio/reservations'); }
function edit() { pressTo('/pages/auth/studio-profile'); }
function ownerAlerts(){pressTo('/pages/studio/owner');}
function openWorkbench(){uni.navigateTo({url:'/pages/studio/manage'});}
watch(()=>user.token,()=>{sequence++;profile.value=undefined;wallet.value=undefined;isOwner.value=false;busy.value=false;failed.value=false;pointsHelpOpen.value=false;});
onShow(() => { pageReset.value++; void refresh(); });
onUnload(() => { ++sequence; });
</script>
<template>
  <StudioShell id="studio-account-pane" fitted embedded :reset-key="pageReset" :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle">
    <view class="studio-native-main studio-account">
      <view class="studio-native-section-head"><text class="studio-native-title">{{say(accountCopy.account)}}</text><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-eye" :disabled="busy" :aria-label="say(walletCopy.refresh)" hover-class="studio-native-pressed" @tap="refresh(true)"><view v-if="busy" class="studio-native-progress"/><StudioGlyph v-else name="refresh" :size="21"/></button></view>
      <view class="studio-native-profile">
        <button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-avatar-edit" :aria-label="say(profileCopy.edit)" @tap="edit"><image v-if="avatar&&!avatarFailed" class="studio-native-avatar" :src="avatar" mode="aspectFill" @error="avatarFailed=true"/><view v-else class="studio-native-avatar"><StudioGlyph name="user" :size="28"/></view></button>
        <view class="studio-native-profile-text"><text class="studio-native-name">{{name}}</text><text v-if="profile?.email&&profile.email!==name" class="studio-native-body">{{profile.email}}</text><text class="studio-native-label">{{say(profile?.is_admin?workbenchCopy.admin:accountCopy.signed_in)}}</text></view>
        <button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-link studio-profile-edit" @tap="edit">{{say(profileCopy.edit)}}</button>
      </view>
      <button v-if="profile?.is_admin" class="studio-native-menu-row" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="openWorkbench"><StudioGlyph name="grid"/><text class="studio-native-menu-label">{{say(workbenchCopy.entry)}}</text><StudioGlyph name="arrow" :size="18"/></button>
      <text v-if="failed" class="studio-native-error" role="alert">{{t('generic_error')}}</text>
      <view v-if="busy&&!wallet" class="studio-native-status"><view class="studio-native-progress"/><text class="studio-native-body">{{say(walletCopy.loading)}}</text></view>
      <view class="studio-native-balances">
        <view class="studio-native-balance"><text class="studio-native-label">{{say(walletCopy.remaining_time)}}</text><text class="studio-native-balance-value">{{hours}}</text></view>
        <view class="studio-native-balance"><view class="studio-points-label"><text class="studio-native-label">{{say(walletCopy.remaining_points)}}</text><button class="studio-native-eye studio-points-info" :aria-label="say(profileCopy.points_help)" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="pointsHelpOpen=true"><StudioGlyph name="info" :size="16"/></button></view><text class="studio-native-balance-value">{{wallet?wallet.account.points:'—'}}</text></view>
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
      <view class="studio-native-menu"><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-menu-row" hover-class="studio-native-pressed" @tap="visit"><StudioGlyph name="calendar"/><text class="studio-native-menu-label">{{say(visitCopy.come_make_something_f834ec)}}</text><StudioGlyph name="arrow" :size="18"/></button></view>
      <button v-if="isOwner" class="studio-native-menu-row" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="ownerAlerts"><StudioGlyph name="calendar"/><text class="studio-native-menu-label">{{say(ownerCopy.page_title)}}</text><StudioGlyph name="arrow" :size="18"/></button>

      <button hover-class="studio-native-pressed" :hover-start-time="0" :hover-stay-time="180" class="studio-native-menu-row" @tap="notices"><StudioGlyph name="info"/><text class="studio-native-menu-label">{{say(noticeCopy.title)}}</text><StudioGlyph name="arrow" :size="18"/></button>
      <view class="studio-account-end"><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-link" hover-class="studio-native-pressed" @tap="logout">{{say(accountCopy.sign_out)}}</button><StudioLegalLinks :language="language"/></view>
    </view>
    <template #overlay><view v-if="pointsHelpOpen" class="studio-modal" role="dialog" aria-modal="true" :aria-label="say(profileCopy.points_help)" @tap="pointsHelpOpen=false" @touchmove.stop.prevent>
      <view class="studio-modal-panel studio-points-help" @tap.stop @touchmove.stop>
        <view class="studio-native-section-head"><text class="studio-native-subtitle">{{say(profileCopy.points_help)}}</text><button class="studio-native-eye" :aria-label="say(walletCopy.close)" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="pointsHelpOpen=false"><StudioGlyph name="close"/></button></view>
        <text class="studio-native-body">{{say(walletCopy.rules)}}</text><text class="studio-native-body">{{say(walletCopy.redeem_rule)}}</text><text class="studio-native-body">{{say(walletCopy.promotion_rule)}}</text><text class="studio-native-body">{{say(walletCopy.earn_rule)}}</text><text class="studio-native-body">{{say(walletCopy.patch_points_rule)}}</text>
      </view>
    </view></template>
  </StudioShell>
</template>

<style scoped>
.studio-account-end{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}
.studio-points-label{display:flex;align-items:center;justify-content:center;position:relative;padding-right:22px}
.studio-native .studio-points-info{position:absolute;right:-11px;top:calc(50% - 22px);width:44px;height:44px}
</style>
