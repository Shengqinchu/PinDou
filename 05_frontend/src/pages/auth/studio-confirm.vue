<script setup lang="ts">
import { computed, ref } from 'vue';
import { onLoad, onUnload } from '@dcloudio/uni-app';
import copy from '../../../../05_studio/src/content/miniapp.json';
import profileCopy from '../../../../05_studio/src/content/profile.json';
import {useUserStore} from '../../store/studio-user';
import StudioShell from '../../components/StudioShell.vue';
import StudioBrand from '../../components/StudioBrand.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import { useStudioNative } from '../../utils/studio-native';
import { miniSession, studioCall, miniappPrefix, MiniappError } from '../../utils/miniapp-client';
const { language, keyboardOpen, shellStyle, t, say, changeLanguage } = useStudioNative();
const busy = ref(false), loading = ref(true), errorCode = ref(''), status = ref(''), scene = ref(''), ticket = ref('');
const details = ref<{mode:string;account:string;display_code:string}>();
let alive = true;
const done = computed(() => status.value === 'approved' || status.value === 'denied');
const terminal = computed(() => ['wechat_flow_expired','wechat_flow_used','miniapp_other_scanner','miniapp_confirmation_mismatch'].includes(errorCode.value));
const error = computed(() => t((errorCode.value in copy ? errorCode.value : 'generic_error') as keyof typeof copy));
function fail(e: unknown) {
  errorCode.value = e instanceof MiniappError ? e.code : 'generic_error';
  if (errorCode.value === 'miniapp_session_expired') details.value = undefined;
}
async function load() {
  if (busy.value) return;
  loading.value = true; errorCode.value = ''; details.value = undefined;
  try {
    if (!/^[A-Za-z0-9_-]{24}$/.test(scene.value)) throw new MiniappError('wechat_flow_expired');
    const proof = await miniSession(); if (!alive) return; ticket.value = proof.ticket;
    const result = await studioCall<{status:string;mode:string;account:string;display_code:string}>(miniappPrefix + '/scan', {scene:scene.value}, ticket.value);
    if (!alive) return;
    details.value = result;
    status.value = ['linked','ready','needs_email','consumed'].includes(result.status) ? 'approved' : result.status === 'denied' ? 'denied' : 'qr_scanned';
  } catch (e) { if (alive) fail(e); }
  finally { if (alive) loading.value = false; }
}
async function confirm(approve: boolean) {
  if (busy.value || loading.value || done.value || terminal.value || !details.value) return;
  busy.value = true; errorCode.value = '';
  try {
    const result = await studioCall<{status:string}>(miniappPrefix + '/confirm', {scene:scene.value,approve,display_code:details.value.display_code}, ticket.value);
    if (alive) status.value = result.status;
  } catch (e) { if (alive) fail(e); }
  finally { if (alive) busy.value = false; }
}
async function setupProfile(){if(busy.value)return;busy.value=true;errorCode.value='';try{const result=await studioCall<any>(miniappPrefix+'/native/sign-in',{},ticket.value);if(!alive)return;const user=useUserStore();user.token=result.token;user.userInfo=result.shared_user;uni.setStorageSync('pd_token',result.token);uni.setStorageSync('pd_user',JSON.stringify(result.shared_user));uni.redirectTo({url:'/pages/auth/studio-profile?onboard=1'});}catch(e){if(alive)fail(e);}finally{if(alive)busy.value=false;}}
function home() { uni.reLaunch({url:'/pages/studio/home'}); }
onLoad(options => { try { scene.value = decodeURIComponent(String(options?.scene || '')); } catch { scene.value = ''; } void load(); });
onUnload(() => { alive = false; ticket.value = ''; });
</script>
<template>
  <StudioShell :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" @language="changeLanguage">
    <view class="studio-native-main studio-native-confirm">
      <view v-if="done" class="studio-native-result" :class="{'studio-native-result--cancelled':status==='denied'}"><StudioGlyph :name="status==='approved'?'check':'close'" :size="32"/></view>
      <StudioBrand v-else :language="language" puppy />
      <view class="studio-native-heading"><text class="studio-native-title">{{done?t(status==='approved'?'done_title':'cancelled'):t(details?.mode==='link'?'link_title':'confirm_title')}}</text><text class="studio-native-site">{{t('site')}}</text></view>
      <text v-if="done&&status==='approved'" class="studio-native-body">{{t('done_body')}}</text>
      <template v-else-if="!done">
        <view v-if="loading" class="studio-native-status"><view class="studio-native-progress"/><text class="studio-native-body">{{t('loading')}}</text></view>
        <view v-else-if="details&&!terminal" class="studio-native-request">
          <view class="studio-native-digits" :aria-label="t('check_code').replace('{v0}',details.display_code)"><text v-for="(digit,index) in details.display_code.split('')" :key="index" class="studio-native-digit">{{digit}}</text></view>
          <text class="studio-native-body">{{t('confirm_help')}}</text>
          <view v-if="details.mode==='link'" class="studio-native-account-link"><text class="studio-native-label">{{t('link_account')}}</text><text class="studio-native-account-value">{{details.account}}</text></view>
        </view>
      </template>
      <text v-if="errorCode" class="studio-native-error" role="alert">{{error}}</text>
    </view>
    <view class="studio-native-actions"><button v-if="status==='approved'" class="studio-native-secondary" :disabled="busy" @tap="setupProfile">{{say(profileCopy.setup_title)}}</button>
      <button :hover-start-time="0" v-if="done||terminal" class="studio-native-primary" hover-class="studio-native-pressed" :hover-stay-time="220" @tap="home"><text class="studio-native-primary-label">{{t('home')}}</text><view class="studio-native-button-arrow"><StudioGlyph name="arrow" :size="18"/></view></button>
      <template v-else-if="details&&!loading">
        <button :hover-start-time="0" class="studio-native-primary" :disabled="busy" hover-class="studio-native-pressed" :hover-stay-time="220" @tap="confirm(true)"><view v-if="busy" class="studio-native-progress"/><text class="studio-native-primary-label">{{t(busy?'working':details.mode==='link'?'link':'confirm')}}</text><view v-if="!busy" class="studio-native-button-arrow"><StudioGlyph name="arrow" :size="18"/></view></button>
        <button :hover-stay-time="180" :hover-start-time="0" class="studio-native-link" :disabled="busy" hover-class="studio-native-pressed" @tap="confirm(false)">{{t('cancel')}}</button>
      </template>
      <button :hover-stay-time="180" :hover-start-time="0" v-else-if="errorCode" class="studio-native-secondary" :disabled="loading" hover-class="studio-native-pressed" @tap="load">{{t('retry')}}</button>
    </view>
  </StudioShell>
</template>
