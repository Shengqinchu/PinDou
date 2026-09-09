<script setup lang="ts">
import { onMounted,ref } from 'vue';
import { PhWechatLogo } from '@phosphor-icons/vue';
import InfoTip from './InfoTip.vue';
import { profileCopy } from '../profile';
import { commerceApi } from '../commerce';
import { say } from '../state';
import { startWechat,wechatCopy as copy } from '../wechat';
const props=defineProps<{linking?:boolean;compact?:boolean}>();
const available=ref(false),linked=ref(false),busy=ref(false),error=ref('');
const phone=/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
onMounted(async()=>{
  try{
    const options=await commerceApi<{wechat:boolean}>('/auth/options');available.value=options.wechat;
    if(props.linking&&available.value)linked.value=(await commerceApi<{linked:boolean}>('/auth/wechat/binding')).linked;
  }catch{/* Email remains usable if optional provider discovery fails. */}
});
async function start(){busy.value=true;error.value='';try{await startWechat(!!props.linking);}catch(e){error.value=(e as Error).message;busy.value=false;}}
</script>
<template>
  <div v-if="available" class="wechat-signin" :class="{'wechat-compact':compact}">
    <div v-if="linked" class="wechat-bound"><span><PhWechatLogo :size="18"/>{{say(copy.linked)}}</span><InfoTip :label="say(profileCopy.wechat_help)"><p>{{say(profileCopy.wechat_profile_help)}}</p></InfoTip></div>
    <div v-else-if="phone&&linking" class="wechat-bound"><span><PhWechatLogo :size="18"/>{{say(copy.link)}}</span><InfoTip :label="say(profileCopy.wechat_help)"><p>{{say(profileCopy.mobile_link_help)}}</p></InfoTip></div>
    <template v-else-if="phone">
      <p class="account-note">{{ say(copy.phone_email) }}</p>
    </template>
    <template v-else>
      <button type="button" :class="compact?'wechat-link text-link':'button button-secondary'" :disabled="busy" @click="start"><PhWechatLogo :size="compact?18:23" />{{ say(busy?copy.redirecting:linking?copy.link:copy.sign_in) }}</button>
      <p v-if="!compact" class="account-note">{{ say(copy.desktop_help) }}</p>
    </template>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
  </div>
</template>
