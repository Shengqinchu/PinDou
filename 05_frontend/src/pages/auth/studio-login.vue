<script setup lang="ts">
import { computed, ref } from 'vue';
import { onLoad, onUnload } from '@dcloudio/uni-app';
import copy from '../../../../05_studio/src/content/miniapp.json';
import accountCopy from '../../../../05_studio/src/content/account.json';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import StudioLegalLinks from '../../components/StudioLegalLinks.vue';
import { useStudioNative } from '../../utils/studio-native';
import { miniSession, studioCall, miniappPrefix, MiniappError, type SharedSession } from '../../utils/miniapp-client';
import { useUserStore } from '../../store/user';
import { studioWords } from '../../utils/studio-content';
import {askWechatNotifications,loadNotifications,saveNotifications} from '../../utils/customer-notifications';
const user = useUserStore();
const { language, keyboardOpen, shellStyle, say, t, changeLanguage, website } = useStudioNative();
type Method = 'register' | 'password' | 'wechat';
const method = ref<Method>('password');
const email = ref(''), password = ref(''), confirmation = ref(''), ticket = ref('');
const linked = ref(false), loading = ref(false), busy = ref(false), reveal = ref(false), focus = ref(''), errorCode = ref('');
let alive = true, proofExpires = 0;
const tabs = computed(() => [
  { value: 'register' as Method, label: say(accountCopy.register) },
  { value: 'password' as Method, label: say(accountCopy.sign_in) },
  { value: 'wechat' as Method, label: say(accountCopy.wechat_method) },
]);
const valid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()) &&
  password.value.length >= (method.value === 'register' ? 6 : 1) &&
  (method.value !== 'register' || password.value === confirmation.value));
const error = computed(() => say(({ ...accountCopy, ...copy } as Record<string,string[]>)[errorCode.value] || copy.generic_error));
function fail(e: unknown) { errorCode.value = e instanceof MiniappError ? e.code : 'generic_error'; if (errorCode.value === 'miniapp_session_expired') proofExpires = 0; }
async function prepare() {
  if (loading.value) return false;
  if (ticket.value && Date.now() < proofExpires) return true;
  loading.value = true; errorCode.value = '';
  try {
    const proof = await miniSession();
    if (!alive) return false;
    ticket.value = proof.ticket; linked.value = proof.linked;
    proofExpires = Date.now() + proof.expires_in * 1000 - 5000;
    return true;
  } catch (e) { if (alive) fail(e); return false; }
  finally { if (alive) loading.value = false; }
}
function choose(value: Method) {
  if (busy.value) return;
  uni.hideKeyboard(); method.value = value; errorCode.value = ''; reveal.value = false;
  if (value === 'wechat') void prepare();
}
async function complete(result: SharedSession,requestWechat=false) {
  if (!alive) return;
  user.token = result.token; user.userInfo = result.shared_user;
  uni.setStorageSync('pd_token', result.token); uni.setStorageSync('pd_user', JSON.stringify(result.shared_user));
  password.value = ''; confirmation.value = '';
  try{await loadNotifications(result.token);await saveNotifications(result.token);}catch{}
  if(requestWechat)await askWechatNotifications(result.token,language.value);
  if(!alive||user.token!==result.token)return;
  const previous = getCurrentPages().slice(-2)[0]?.route || '';
  if (getCurrentPages().length > 1 && !/pages\/(auth|index|user)\//.test(previous)) uni.navigateBack({ delta: 1 });
  else uni.redirectTo({ url: '/pages/studio/home' });
}
async function signIn() {
  if (busy.value || !valid.value) return;
  busy.value = true; errorCode.value = ''; uni.hideKeyboard();
  try {
    if (!await prepare() || !alive) return;
    // A connected WeChat cannot be assigned to a second account. Reject before
    // registering, so a UI retry does not leave an unintended spare account.
    if (method.value === 'register' && linked.value) throw new MiniappError('wechat_binding_conflict');
    const result = await studioCall<SharedSession>(method.value === 'register' ? '/auth/password-register' : '/auth/password-login',
      { email: email.value.trim().toLowerCase(), password: password.value });
    if (!alive) return;
    await studioCall(miniappPrefix + '/native/bind', {}, ticket.value, result.token);
    await complete(result,method.value==='register');
  } catch (e) { if (alive) fail(e); }
  finally { if (alive) busy.value = false; }
}
async function wechat() {
  if (busy.value || loading.value || !ticket.value || errorCode.value) return;
  busy.value = true; errorCode.value = '';
  try {
    if (!await prepare() || !alive) return;
    await complete(await studioCall<SharedSession>(miniappPrefix + (linked.value ? '/native/sign-in' : '/native/create'), {}, ticket.value),true);
  } catch (e) { if (alive) fail(e); }
  finally { if (alive) busy.value = false; }
}
function recover() { uni.showModal({ title: t('forgot'), content: t('recovery_help'), showCancel: false }); }
function home() { uni.reLaunch({url:'/pages/studio/home'}); }
onLoad(() => { if (user.token) uni.redirectTo({ url: '/pages/studio/home' }); });
onUnload(() => { alive = false; ticket.value = ''; password.value = ''; confirmation.value = ''; });
</script>
<template>
  <StudioShell :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" @language="changeLanguage">
    <view class="studio-native-main">
      <view class="studio-native-heading"><text class="studio-native-title">{{t('native_title')}}</text><text class="studio-native-body">{{t('native_intro')}}</text></view>
      <view class="studio-native-tabs" role="tablist" :aria-label="say(accountCopy.sign_in)">
        <button :hover-stay-time="180" :hover-start-time="0" v-for="tab in tabs" :key="tab.value" :id="'method-'+tab.value" class="studio-native-tab" :class="{'studio-native-tab--active':method===tab.value}" role="tab" :aria-selected="method===tab.value" :disabled="busy" hover-class="studio-native-pressed" @tap="choose(tab.value)">{{tab.label}}</button>
      </view>
      <view v-if="method!=='wechat'" class="studio-native-form" role="tabpanel" :aria-labelledby="'method-'+method">
        <label class="studio-native-field" for="studio-email"><text>{{t('email')}}</text><view class="studio-native-input" :class="{'studio-native-input--focused':focus==='email'}"><input id="studio-email" v-model="email" type="text" :maxlength="254" :disabled="busy" confirm-type="next" :cursor-spacing="24" :adjust-position="true" :aria-label="t('email')" @focus="focus='email'" @blur="focus=''" @confirm="focus='password'" /></view></label>
        <label class="studio-native-field" for="studio-password"><text>{{method==='register'?say(accountCopy.new_password):t('password')}}</text><view class="studio-native-input" :class="{'studio-native-input--focused':focus==='password'}"><input id="studio-password" v-model="password" :password="!reveal" :maxlength="128" :disabled="busy" :focus="focus==='password'" :confirm-type="method==='register'?'next':'done'" :cursor-spacing="80" :adjust-position="true" :aria-label="t('password')" @focus="focus='password'" @blur="focus=''" @confirm="method==='register'?focus='confirmation':signIn()" /><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-eye" hover-class="studio-native-pressed" :disabled="busy" :aria-label="say(reveal?accountCopy.hide_password:accountCopy.show_password)" @tap="reveal=!reveal"><StudioGlyph :name="reveal?'hidden':'eye'" :size="20" /></button></view></label>
        <label v-if="method==='register'" class="studio-native-field" for="studio-confirm-password"><text>{{say(accountCopy.confirm_password)}}</text><view class="studio-native-input" :class="{'studio-native-input--focused':focus==='confirmation'}"><input id="studio-confirm-password" v-model="confirmation" :password="!reveal" :maxlength="128" :disabled="busy" :focus="focus==='confirmation'" confirm-type="done" :cursor-spacing="80" :adjust-position="true" :aria-label="say(accountCopy.confirm_password)" @focus="focus='confirmation'" @blur="focus=''" @confirm="signIn" /></view></label>
        <text v-if="method==='register'&&confirmation&&confirmation!==password" class="studio-native-error" role="alert">{{say(accountCopy.password_mismatch)}}</text>
        <text v-if="errorCode" class="studio-native-error" role="alert">{{error}}</text>
        <button :hover-start-time="0" class="studio-native-primary" :disabled="busy||!valid" hover-class="studio-native-pressed" :hover-stay-time="220" @tap="signIn"><view v-if="busy" class="studio-native-progress"/><text class="studio-native-primary-label">{{busy?say(method==='register'?accountCopy.registering:accountCopy.working):method==='register'?say(accountCopy.register):t('password_login')}}</text><view v-if="!busy" class="studio-native-button-arrow"><StudioGlyph name="arrow" :size="18"/></view></button>
        <button :hover-stay-time="180" :hover-start-time="0" v-if="method==='password'" class="studio-native-link" :disabled="busy" hover-class="studio-native-pressed" @tap="recover">{{t('forgot')}}</button>
      </view>
      <view v-else class="studio-native-wechat" role="tabpanel" aria-labelledby="method-wechat">
        <view class="studio-native-wechat-icon"><StudioGlyph name="wechat" :size="36"/></view>
        <view v-if="loading" class="studio-native-status"><view class="studio-native-progress"/><text class="studio-native-body">{{t('loading')}}</text></view>
        <text v-if="errorCode" class="studio-native-error" role="alert">{{error}}</text>
        <button :hover-stay-time="180" :hover-start-time="0" v-if="errorCode" class="studio-native-secondary" :disabled="loading||busy" hover-class="studio-native-pressed" @tap="proofExpires=0;prepare()">{{t('retry')}}</button>
        <button :hover-start-time="0" v-else-if="!loading" class="studio-native-primary" :disabled="busy||!ticket" hover-class="studio-native-pressed" :hover-stay-time="220" @tap="wechat"><view v-if="busy" class="studio-native-progress"/><text>{{t(busy?'working':linked?'wechat_login':'wechat_create')}}</text></button>
        <text class="studio-native-body studio-native-small">{{t('website_account')}}</text>
      </view>
    </view>
    <view class="studio-native-footer"><text class="studio-native-site">pindoupuppy.com</text><view class="studio-login-links"><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-link" hover-class="studio-native-pressed" @tap="home"><StudioGlyph name="home" :size="16"/>{{say(studioWords('app','home_76c92b'))}}</button><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-link" hover-class="studio-native-pressed" @tap="website"><StudioGlyph name="copy" :size="16"/>{{t('visit_website')}}</button></view></view>
    <StudioLegalLinks :language="language"/>
  </StudioShell>
</template>
