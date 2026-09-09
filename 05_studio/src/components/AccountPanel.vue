<script setup lang="ts">
import { computed,onBeforeUnmount,ref,watch } from "vue";
import { PhArrowRight,PhEye,PhEyeSlash,PhUserCircle } from "@phosphor-icons/vue";
import SlideOver from "./SlideOver.vue";
import CustomerWallet from './CustomerWallet.vue';
import { accountCopy as copy,accountUser,accountOpen,accountForReservation,closeAccount,completeSignIn,signOut,type SignInResult } from "../account";
import { commerceApi } from "../commerce";
import { say,formatCopy } from "../state";
import WechatSignIn from './WechatSignIn.vue';
const props=defineProps<{embedded?:boolean;emailOnly?:boolean}>();
const emit=defineEmits<{signedIn:[]}>();
const method=ref<"code"|"password">("code");
const email=ref("");const code=ref("");const password=ref("");const confirmation=ref("");
const setPassword=ref(false);const reveal=ref(false);const busy=ref(false);const sending=ref(false);
const error=ref("");const sent=ref(false);const now=ref(Date.now());const nextSend=ref<Record<string,number>>({});
const normalizedEmail=computed(()=>email.value.trim().toLowerCase());
const cooldown=computed(()=>Math.max(0,Math.ceil(((nextSend.value[normalizedEmail.value]||0)-now.value)/1000)));
const validEmail=computed(()=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail.value));
const working=computed(()=>busy.value||sending.value);
const timer=setInterval(()=>now.value=Date.now(),1000);
onBeforeUnmount(()=>clearInterval(timer));
watch(method,()=>{error.value="";password.value="";confirmation.value="";reveal.value=false;});
watch(email,()=>{sent.value=false;error.value="";code.value="";});
watch(accountOpen,value=>{if(!value){password.value="";confirmation.value="";code.value="";error.value="";reveal.value=false;}});
async function sendCode(){
  if(!validEmail.value||cooldown.value||working.value)return;
  sending.value=true;error.value="";const target=normalizedEmail.value;
  try{
    const result=await commerceApi<{cooldown_seconds:number}>("/auth/send-code",{method:"POST",body:JSON.stringify({email:target})});
    nextSend.value[target]=Date.now()+result.cooldown_seconds*1000;now.value=Date.now();sent.value=target===normalizedEmail.value;
  }catch(e){error.value=(e as Error).message;}
  finally{sending.value=false;}
}
async function login(){
  if(working.value)return;
  error.value="";
  if(method.value==="code"&&setPassword.value&&password.value!==confirmation.value){error.value=say(copy.password_mismatch);return;}
  busy.value=true;
  try{
    const path=method.value==="password"?"password-login":setPassword.value?"register":"code-login";
    const body={email:normalizedEmail.value,...(method.value==="code"?{code:code.value.trim()}:{}),...(method.value==="password"||setPassword.value?{password:password.value}:{})};
    const result=await commerceApi<SignInResult>("/auth/"+path,{method:"POST",body:JSON.stringify(body)});
    password.value="";confirmation.value="";code.value="";completeSignIn(result);emit('signedIn');
  }catch(e){error.value=(e as Error).message;}
  finally{busy.value=false;}
}
</script>
<template>
  <component :is="props.embedded?'section':SlideOver" :model-value="props.embedded||accountOpen" @update:model-value="(value:boolean)=>{if(!value)closeAccount()}" :busy="working"
    :title="say(accountUser?copy.account:accountForReservation?copy.reservation_title:copy.title)">
    <section v-if="accountUser" class="account-content">
      <div class="account-identity"><PhUserCircle :size="42" weight="light" /><div><span class="fine-print">{{ say(copy.signed_in) }}</span><strong>{{ accountUser.nickname||accountUser.email }}</strong><p v-if="accountUser.nickname">{{ accountUser.email }}</p></div></div>
      <WechatSignIn v-if="!emailOnly" :key="accountUser.id" linking />
      <CustomerWallet v-if="!emailOnly&&(accountOpen||embedded)" :key="accountUser.id"/>
      <a v-if="!emailOnly" class="button button-secondary" href="/upload">{{ say(copy.pattern_tool) }}<PhArrowRight /></a>
      <RouterLink v-if="!embedded&&!emailOnly" class="text-link" to="/account" @click="closeAccount">{{ say(copy.account_center) }}</RouterLink>
      <RouterLink class="button button-primary" to="/visit" @click="closeAccount">{{ say(copy.book_a_visit) }}<PhArrowRight /></RouterLink>
      <button type="button" class="text-link account-signout" @click="signOut">{{ say(copy.sign_out) }}</button>
    </section>
    <div v-else class="account-content">
      <p class="account-note">{{ say(copy.shared_account) }}</p>
      <p v-if="accountForReservation" class="account-draft-note">{{ say(copy.draft_saved) }}</p>
      <WechatSignIn v-if="!emailOnly&&(accountOpen||embedded)" />
      <div class="account-methods" role="group" :aria-label="say(copy.sign_in)">
        <button type="button" class="language-button" :aria-pressed="method==='code'" :disabled="working" @click="method='code'">{{ say(copy.code_method) }}</button>
        <button type="button" class="language-button" :aria-pressed="method==='password'" :disabled="working" @click="method='password'">{{ say(copy.password_method) }}</button>
      </div>
      <form class="account-form" @submit.prevent="login">
        <label class="field">{{ say(copy.email) }}<input v-model="email" type="email" inputmode="email" autocomplete="username" autocapitalize="none" :spellcheck="false" maxlength="255" required :disabled="working" /></label>
        <template v-if="method==='code'">
          <label class="field">{{ say(copy.code) }}<input v-model="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" minlength="6" maxlength="6" required :disabled="working" /></label>
          <button type="button" class="button button-secondary account-send" :disabled="!validEmail||!!cooldown||working" @click="sendCode">{{ sending?say(copy.sending_code):cooldown?formatCopy(copy.resend_after,{v0:cooldown}):say(copy.send_code) }}</button>
          <p v-if="sent" class="account-note" role="status">{{ say(copy.code_sent) }}</p>
          <label class="account-check"><input v-model="setPassword" type="checkbox" :disabled="working" />{{ say(copy.set_password) }}</label>
        </template>
        <template v-if="method==='password'||setPassword">
          <label class="field">{{ say(method==='password'?copy.password:copy.new_password) }}
            <span class="account-password"><input v-model="password" :type="reveal?'text':'password'" :autocomplete="method==='password'?'current-password':'new-password'" :minlength="method==='password'?1:6" maxlength="128" required :disabled="working" /><button type="button" class="icon-button" :aria-label="say(reveal?copy.hide_password:copy.show_password)" :aria-pressed="reveal" @click="reveal=!reveal"><PhEyeSlash v-if="reveal" :size="20" /><PhEye v-else :size="20" /></button></span>
          </label>
          <label v-if="method==='code'" class="field">{{ say(copy.confirm_password) }}<input v-model="confirmation" :type="reveal?'text':'password'" autocomplete="new-password" minlength="6" maxlength="128" required :disabled="working" /></label>
        </template>
        <button v-if="method==='password'" type="button" class="text-link" :disabled="working" @click="method='code'">{{ say(copy.forgot_password) }}</button>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="button button-primary" :disabled="working||!validEmail">{{ busy?say(copy.working):accountForReservation?say(copy.continue_reservation):say(method==='password'?copy.sign_in:copy.continue) }}<PhArrowRight /></button>
      </form>
    </div>
  </component>
</template>
