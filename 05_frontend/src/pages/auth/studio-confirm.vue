<script setup lang="ts">
import { computed,ref } from 'vue';
import { onLoad,onUnload } from '@dcloudio/uni-app';
import copy from '../../../../05_studio/src/content/miniapp.json';
import { miniSession,studioCall,miniappPrefix,MiniappError } from '../../utils/miniapp-client';
const language=ref(uni.getStorageSync('pd_studio_language')||(/^en/i.test(uni.getSystemInfoSync().language||'')?'en':'zh'));
const t=(key:keyof typeof copy)=>copy[key][language.value==='en'?1:0];
const busy=ref(false),loading=ref(true),error=ref(''),status=ref(''),scene=ref(''),ticket=ref('');
const details=ref<{mode:string;account:string;display_code:string}>();let alive=true;
const done=computed(()=>status.value==='approved'||status.value==='denied');
function fail(e:unknown){error.value=e instanceof MiniappError?t((e.code in copy?e.code:'generic_error') as keyof typeof copy):t('generic_error');}
async function load(){loading.value=true;error.value='';try{if(!/^[A-Za-z0-9_-]{24}$/.test(scene.value))throw new MiniappError('wechat_flow_expired');const proof=await miniSession();if(!alive)return;ticket.value=proof.ticket;const result=await studioCall<{status:string;mode:string;account:string;display_code:string}>(miniappPrefix+'/scan',{scene:scene.value},ticket.value);if(!alive)return;details.value=result;status.value=['linked','ready','needs_email','consumed'].includes(result.status)?'approved':result.status==='denied'?'denied':'qr_scanned';}catch(e){if(alive)fail(e);}finally{if(alive)loading.value=false;}}
async function confirm(approve:boolean){if(busy.value||!details.value)return;busy.value=true;error.value='';try{const result=await studioCall<{status:string}>(miniappPrefix+'/confirm',{scene:scene.value,approve,display_code:details.value.display_code},ticket.value);if(alive)status.value=result.status;}catch(e){if(alive)fail(e);}finally{if(alive)busy.value=false;}}
function changeLanguage(){language.value=language.value==='zh'?'en':'zh';uni.setStorageSync('pd_studio_language',language.value);}
function home(){uni.reLaunch({url:'/pages/auth/studio-login'});}
onLoad(options=>{try{scene.value=decodeURIComponent(String(options?.scene||''));}catch{scene.value='';}void load();});
onUnload(()=>{alive=false;ticket.value='';});
</script>
<template>
 <view class="studio-native">
  <view class="studio-native-top"><image class="studio-native-logo" :src="language==='en'?'/static/studio/logo-en.jpg':'/static/studio/logo-zh.jpg'" mode="aspectFit"/><button class="studio-native-language" @tap="changeLanguage">{{language==='zh'?'English':'中文'}}</button></view>
  <view class="studio-native-main">
   <image class="studio-native-puppy" src="/static/studio/puppy.png" mode="aspectFit"/>
   <text class="studio-native-title">{{done?t(status==='approved'?'done_title':'cancelled'):t(details?.mode==='link'?'link_title':'confirm_title')}}</text>
   <text v-if="done&&status==='approved'" class="studio-native-body">{{t('done_body')}}</text>
   <template v-else-if="!done">
    <text class="studio-native-site">{{t('site')}}</text>
    <text v-if="loading" class="studio-native-body">{{t('loading')}}</text>
    <view v-if="details&&!loading" class="studio-native-request"><text class="studio-native-code">{{details.display_code}}</text><text class="studio-native-body">{{t('confirm_help')}}</text><text v-if="details.mode==='link'" class="studio-native-body">{{t('link_account')}} · {{details.account}}</text></view>
   </template>
   <text v-if="error" class="studio-native-error">{{error}}</text>
  </view>
  <view class="studio-native-actions">
   <button v-if="done" class="studio-native-primary" @tap="home">{{t('home')}}</button>
   <template v-else-if="details&&!loading"><button class="studio-native-primary" :disabled="busy" @tap="confirm(true)">{{t(busy?'working':details.mode==='link'?'link':'confirm')}}</button><button class="studio-native-secondary" :disabled="busy" @tap="confirm(false)">{{t('cancel')}}</button></template>
   <button v-else-if="error" class="studio-native-primary" :disabled="loading" @tap="load">{{t('retry')}}</button>
  </view>
 </view>
</template>
<style src="../../static/styles/studio-auth.css"></style>
