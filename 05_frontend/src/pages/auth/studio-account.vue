<script setup lang="ts">
import { computed, ref } from 'vue';
import { onShow, onUnload } from '@dcloudio/uni-app';
import accountCopy from '../../../../05_studio/src/content/account.json';
import walletCopy from '../../../../05_studio/src/content/wallet.json';
import bookingCopy from '../../../../05_studio/src/content/booking-profile.json';
import visitCopy from '../../../../05_studio/src/content/pages-Visit.json';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import { useStudioNative } from '../../utils/studio-native';
import { studioRead, MiniappError } from '../../utils/miniapp-client';
import { useUserStore } from '../../store/user';
type Profile = {nickname:string;email:string;avatar?:string};
type Wallet = {account:{minutes:number;points:number};booking_profile:{name:string;contact_method:string;contact:string;complete:boolean}};
const user = useUserStore();
const { language, keyboardOpen, shellStyle, say, t, changeLanguage, website } = useStudioNative();
const profile = ref<Profile>(), wallet = ref<Wallet>(), busy = ref(false), failed = ref(false), avatarFailed = ref(false);
let sequence = 0;
const name = computed(() => profile.value?.nickname || profile.value?.email || user.userInfo?.nickname || user.userInfo?.email || say(accountCopy.default_name));
const hours = computed(() => wallet.value ? say(walletCopy.whole_hours).replace('{v0}',String(Math.round(wallet.value.account.minutes / 60 * 100) / 100)) : '—');
const contactLabel = computed(() => say(({wechat:visitCopy.wechat_2941d2,phone:visitCopy.phone_ac7a62,email:accountCopy.email,other:visitCopy.another_way_f489b4} as Record<string,string[]>)[wallet.value?.booking_profile?.contact_method || 'wechat'] || bookingCopy.contact));
const avatar = computed(() => {
  const value = profile.value?.avatar || '';
  return value.startsWith('/') ? 'https://pindoupuppy.com' + value : /^https:\/\//.test(value) ? value : '';
});
async function refresh() {
  if (busy.value) return;
  if (!user.token) { uni.redirectTo({url:'/pages/auth/studio-login'}); return; }
  const token = user.token, current = ++sequence;
  busy.value = true; failed.value = false;
  const results = await Promise.allSettled([
    studioRead<{user:Profile}>('/auth/me',token), studioRead<Wallet>('/auth/wallet',token),
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
onShow(() => void refresh());
onUnload(() => { ++sequence; });
</script>
<template>
  <StudioShell :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" @language="changeLanguage">
    <view class="studio-native-main">
      <view class="studio-native-section-head"><text class="studio-native-title">{{say(accountCopy.account)}}</text><button class="studio-native-eye" :disabled="busy" :aria-label="say(walletCopy.refresh)" hover-class="studio-native-pressed" @tap="refresh"><view v-if="busy" class="studio-native-progress"/><StudioGlyph v-else name="refresh" :size="21"/></button></view>
      <view class="studio-native-profile">
        <image v-if="avatar&&!avatarFailed" class="studio-native-avatar" :src="avatar" mode="aspectFill" @error="avatarFailed=true"/>
        <view v-else class="studio-native-avatar"><StudioGlyph name="user" :size="30"/></view>
        <view class="studio-native-profile-text"><text class="studio-native-name">{{name}}</text><text v-if="profile?.email&&profile.email!==name" class="studio-native-body">{{profile.email}}</text><text class="studio-native-label">{{say(accountCopy.signed_in)}}</text></view>
      </view>
      <text v-if="failed" class="studio-native-error" role="alert">{{t('generic_error')}}</text>
      <view v-if="busy&&!wallet" class="studio-native-status"><view class="studio-native-progress"/><text class="studio-native-body">{{say(walletCopy.loading)}}</text></view>
      <view class="studio-native-balances">
        <view class="studio-native-balance"><text class="studio-native-label">{{say(walletCopy.remaining_time)}}</text><text class="studio-native-balance-value">{{hours}}</text></view>
        <view class="studio-native-balance"><text class="studio-native-label">{{say(walletCopy.remaining_points)}}</text><text class="studio-native-balance-value">{{wallet?wallet.account.points:'—'}}</text></view>
      </view>
      <view v-if="wallet" class="studio-native-section">
        <text class="studio-native-subtitle">{{say(bookingCopy.title)}}</text>
        <view class="studio-native-definition">
          <template v-if="wallet.booking_profile?.complete">
            <view class="studio-native-definition-row"><text class="studio-native-label">{{say(bookingCopy.name)}}</text><text class="studio-native-account-value">{{wallet.booking_profile.name}}</text></view>
            <view class="studio-native-definition-row"><text class="studio-native-label">{{contactLabel}}</text><text class="studio-native-account-value" selectable>{{wallet.booking_profile.contact}}</text></view>
          </template>
          <text v-else class="studio-native-body">{{say(bookingCopy.empty)}}</text>
        </view>
      </view>
      <view class="studio-native-menu"><button class="studio-native-menu-row" hover-class="studio-native-pressed" @tap="patterns"><StudioGlyph name="grid"/><text class="studio-native-menu-label">{{say(accountCopy.pattern_tool)}}</text><StudioGlyph name="arrow" :size="18"/></button><button class="studio-native-menu-row" hover-class="studio-native-pressed" @tap="website"><StudioGlyph name="copy"/><text class="studio-native-menu-label">{{t('visit_website')}}</text><StudioGlyph name="arrow" :size="18"/></button></view>
      <button class="studio-native-link" hover-class="studio-native-pressed" @tap="logout">{{say(accountCopy.sign_out)}}</button>
    </view>
    <view class="studio-native-footer"><text class="studio-native-site">pindoupuppy.com</text></view>
  </StudioShell>
</template>
