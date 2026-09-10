<script setup lang="ts">
import LiftTitle from '../components/LiftTitle.vue';
import { onMounted,ref } from 'vue';
import AccountPanel from '../components/AccountPanel.vue';
import { accountUser,completeSignIn,refreshAccount,type SignInResult } from '../account';
import { commerceApi } from '../commerce';
import { accountReturn,wechatCopy as copy } from '../wechat';
import { say } from '../state';
import { useRoute } from 'vue-router';
const route=useRoute(),status=ref('loading'),error=ref(''),target=ref('/account'),busy=ref(false);
const state=typeof route.query.state==='string'?route.query.state:'';
async function read(){
  status.value='loading';error.value='';
  try{
    const flow=await commerceApi<{status:string;error:string;return_to:string}>('/auth/wechat/flow?state='+encodeURIComponent(state));
    target.value=accountReturn(flow.return_to);status.value=flow.status;
    if(flow.status==='ready'){
      const session=await commerceApi<SignInResult&{return_to:string}>('/auth/wechat/finish',{method:'POST',body:JSON.stringify({state})});
      completeSignIn(session);location.replace(accountReturn(session.return_to));
    }else if(flow.status==='needs_email'||flow.status==='linked'){await refreshAccount();}
    else if(flow.status==='failed')error.value=say((copy as Record<string,string[]>)[flow.error]||copy.wechat_provider_unavailable);
    else if(flow.status!=='consumed')error.value=say(copy.wechat_provider_unavailable);
  }catch(e){error.value=(e as Error).message;status.value='failed';}
}
async function bind(){
  busy.value=true;error.value='';
  try{await commerceApi('/auth/wechat/bind',{method:'POST',body:JSON.stringify({state})});status.value='linked';}
  catch(e){error.value=(e as Error).message;}finally{busy.value=false;}
}
async function create(){busy.value=true;error.value='';try{await commerceApi('/auth/wechat/create-account',{method:'POST',body:JSON.stringify({state})});await read();}catch(e){error.value=(e as Error).message;}finally{busy.value=false;}}
onMounted(read);
</script>
<template>
  <section class="container account-page wechat-return" aria-live="polite">
    <LiftTitle as="h1" :text="say(copy.title)"/>
    <p v-if="status==='loading'||status==='ready'">{{ say(copy.checking) }}</p>
    <template v-if="status==='needs_email'">
      <p class="account-note">{{ say(copy.first_link) }}</p>
      <AccountPanel v-if="!accountUser" embedded email-only />
      <button v-if="!accountUser" type="button" class="text-link" :disabled="busy" @click="create">{{say(copy.new_account)}}</button>
      <template v-else>
        <p>{{ accountUser.email }}</p><button class="button button-primary" :disabled="busy" @click="bind">{{ say(copy.confirm_link) }}</button>
        <p class="account-note">{{ say(copy.link_preserves_account) }}</p>
      </template>
    </template>
    <template v-if="status==='linked'"><p>{{ say(copy.linked) }}</p><a class="button button-primary" :href="target">{{ say(copy.continue) }}</a></template>
    <template v-if="status==='consumed'"><p>{{ say(copy.wechat_flow_used) }}</p><a class="button button-primary" :href="target">{{ say(copy.continue) }}</a></template>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <RouterLink v-if="error" class="button button-secondary" :to="{path:'/account',query:{intent:'login',return_to:target}}">{{ say(copy.retry) }}</RouterLink>
  </section>
</template>
