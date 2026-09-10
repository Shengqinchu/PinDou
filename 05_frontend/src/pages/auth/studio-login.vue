<script setup lang="ts">
import { computed,ref } from 'vue';
import { onLoad,onUnload } from '@dcloudio/uni-app';
import copy from '../../../../05_studio/src/content/miniapp.json';
import { miniSession,studioCall,miniappPrefix,MiniappError,type SharedSession } from '../../utils/miniapp-client';
import { useUserStore } from '../../store/user';
const user=useUserStore();
const language=ref(uni.getStorageSync('pd_studio_language')||(/^en/i.test(uni.getSystemInfoSync().language||'')?'en':'zh'));
const t=(key:keyof typeof copy)=>copy[key][language.value==='en'?1:0];
const email=ref(''),password=ref(''),ticket=ref(''),linked=ref(false),loading=ref(false),busy=ref(false),error=ref('');let alive=true;
const valid=computed(()=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())&&password.value.length>0);
function fail(e:unknown){if(e instanceof MiniappError&&e.code==='miniapp_session_expired')ticket.value='';error.value=e instanceof MiniappError?t((e.code in copy?e.code:'generic_error') as keyof typeof copy):t('generic_error');}
async function prepare(){loading.value=true;error.value='';try{const result=await miniSession();if(alive){ticket.value=result.ticket;linked.value=result.linked;}}catch(e){if(alive)fail(e);}finally{if(alive)loading.value=false;}}
function complete(result:SharedSession){if(!alive)return;user.token=result.token;user.userInfo=result.shared_user;uni.setStorageSync('pd_token',result.token);uni.setStorageSync('pd_user',JSON.stringify(result.shared_user));password.value='';if(getCurrentPages().length>1)uni.navigateBack({delta:1});else uni.switchTab({url:'/pages/user/me'});}
async function signIn(){if(busy.value||!valid.value||!ticket.value)return;busy.value=true;error.value='';try{const result=await studioCall<SharedSession>('/auth/password-login',{email:email.value.trim().toLowerCase(),password:password.value});await studioCall(miniappPrefix+'/native/bind',{},ticket.value,result.token);complete(result);}catch(e){if(alive)fail(e);}finally{if(alive)busy.value=false;}}
async function wechat(){if(busy.value||!ticket.value)return;busy.value=true;error.value='';try{complete(await studioCall<SharedSession>(miniappPrefix+(linked.value?'/native/sign-in':'/native/create'),{},ticket.value));}catch(e){if(alive)fail(e);}finally{if(alive)busy.value=false;}}
function changeLanguage(){language.value=language.value==='zh'?'en':'zh';uni.setStorageSync('pd_studio_language',language.value);}
function recover(){uni.showModal({title:t('forgot'),content:t('recovery_help'),showCancel:false});}
function website(){uni.setClipboardData({data:'https://pindoupuppy.com/account?wechat_provider=miniapp'});}
onLoad(()=>{void prepare();});onUnload(()=>{alive=false;ticket.value='';password.value='';});
</script>
<template>
 <view class="studio-native">
  <view class="studio-native-top"><image class="studio-native-logo" :src="language==='en'?'/static/studio/logo-en.jpg':'/static/studio/logo-zh.jpg'" mode="aspectFit"/><button class="studio-native-language" @tap="changeLanguage">{{language==='zh'?'English':'中文'}}</button></view>
  <view class="studio-native-main studio-native-login">
   <text class="studio-native-title">{{t('native_title')}}</text><text class="studio-native-body">{{t('native_intro')}}</text>
   <view class="studio-native-field"><text>{{t('email')}}</text><input v-model="email" type="text" :maxlength="254" :disabled="busy" :placeholder="t('email')"/></view>
   <view class="studio-native-field"><text>{{t('password')}}</text><input v-model="password" :password="true" :maxlength="128" :disabled="busy" :placeholder="t('password')"/></view>
   <text v-if="error" class="studio-native-error">{{error}}</text>
   <button v-if="!ticket&&error" class="studio-native-secondary" :disabled="loading" @tap="prepare">{{t('retry')}}</button>
   <button class="studio-native-primary" :disabled="busy||loading||!valid||!ticket" @tap="signIn">{{t(busy?'working':'password_login')}}</button>
   <button class="studio-native-link" :disabled="busy" @tap="recover">{{t('forgot')}}</button>
   <view class="studio-native-divider"/>
   <button class="studio-native-secondary" :disabled="busy||loading||!ticket" @tap="wechat">{{t(linked?'wechat_login':'wechat_create')}}</button>
   <text class="studio-native-body studio-native-small">{{t('website_account')}}</text><button class="studio-native-link" @tap="website">{{t('visit_website')}}</button>
  </view>
 </view>
</template>
<style src="../../static/styles/studio-auth.css"></style>
