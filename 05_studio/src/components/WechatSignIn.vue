<script setup lang="ts">
import { onMounted,ref } from 'vue';
import { PhWechatLogo } from '@phosphor-icons/vue';
import { commerceApi } from '../commerce';
import { say } from '../state';
import { startWechat,wechatCopy as copy } from '../wechat';
const props=defineProps<{linking?:boolean}>();
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
  <div v-if="available" class="wechat-signin">
    <p v-if="linked" class="account-note"><PhWechatLogo :size="22" />{{ say(copy.linked) }}</p>
    <template v-else-if="phone">
      <p class="account-note">{{ say(copy.phone_email) }}</p>
    </template>
    <template v-else>
      <button type="button" class="button button-secondary" :disabled="busy" @click="start"><PhWechatLogo :size="23" />{{ say(busy?copy.redirecting:linking?copy.link:copy.sign_in) }}</button>
      <p class="account-note">{{ say(copy.desktop_help) }}</p>
    </template>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
  </div>
</template>
