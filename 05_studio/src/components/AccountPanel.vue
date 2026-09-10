<script setup lang="ts">
import { computed,onMounted,onBeforeUnmount,ref,watch } from 'vue';
import { PhArrowRight,PhArrowLeft,PhEye,PhEyeSlash,PhWechatLogo,PhKey,PhLink } from '@phosphor-icons/vue';
import { accountCopy as copy,accountOpen,closeAccount,accountUser,accountForReservation,completeSignIn,signOut,type SignInResult } from '../account';
import { say,formatCopy } from '../state';
import { commerceApi } from '../commerce';
import { wechatCopy } from '../wechat';
import AccountIdentity from './AccountIdentity.vue';
import CustomerWallet from './CustomerWallet.vue';
import WechatQr from './WechatQr.vue';
import SlideOver from './SlideOver.vue';
import LiftTitle from './LiftTitle.vue';
const props=defineProps<{embedded?:boolean;emailOnly?:boolean}>();
const emit=defineEmits<{signedIn:[]}>();
const method=ref<'wechat'|'password'|'recovery'>(props.emailOnly||/Android|iPhone|iPod/i.test(navigator.userAgent)?'password':'wechat');
const available=ref(true),email=ref(''),password=ref(''),confirmation=ref(''),code=ref(''),reveal=ref(false);
const busy=ref(false),sending=ref(false),error=ref(''),notice=ref(''),pendingWechat=ref(''),now=ref(Date.now());
const sentUntil=new Map<string,number>();let timer:ReturnType<typeof setInterval>,alive=true;
const normalizedEmail=computed(()=>email.value.trim().toLowerCase());
const emailValid=computed(()=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail.value));
const cooldown=computed(()=>Math.max(0,Math.ceil(((sentUntil.get(normalizedEmail.value)||0)-now.value)/1000)));
const valid=computed(()=>emailValid.value&&password.value.length>=(method.value==='recovery'?6:1)&&(method.value!=='recovery'||/^\d{6}$/.test(code.value)&&password.value===confirmation.value));
function change(value:'wechat'|'password'|'recovery'){if(busy.value)return;method.value=value;error.value='';notice.value='';code.value='';password.value='';confirmation.value='';reveal.value=false;}
function existing(state:string){pendingWechat.value=state;change('password');}
watch(accountOpen,value=>{if(!value&&!props.embedded){pendingWechat.value='';error.value='';notice.value='';code.value='';password.value='';confirmation.value='';reveal.value=false;}});
async function sendCode(){
 if(sending.value||cooldown.value||!emailValid.value)return;
 sending.value=true;error.value='';const destination=normalizedEmail.value;
 try{
  const result=await commerceApi<{cooldown_seconds:number}>('/auth/recovery/send-code',{method:'POST',body:JSON.stringify({email:destination})});
  sentUntil.set(destination,Date.now()+Math.max(60,result.cooldown_seconds)*1000);now.value=Date.now();notice.value=say(copy.recovery_sent);
 }catch(e){error.value=(e as Error).message;}finally{sending.value=false;}
}
async function submit(){
 if(busy.value||!valid.value)return;busy.value=true;error.value='';notice.value='';
 try{
  if(method.value==='recovery'){
   await commerceApi('/auth/recovery/reset-password',{method:'POST',body:JSON.stringify({email:normalizedEmail.value,code:code.value,password:password.value})});
   if(alive){method.value='password';password.value='';confirmation.value='';code.value='';reveal.value=false;notice.value=say(copy.recovery_done);}return;
  }
  const result=await commerceApi<SignInResult>('/auth/password-login',{method:'POST',body:JSON.stringify({email:normalizedEmail.value,password:password.value})});
  if(pendingWechat.value)await commerceApi('/auth/wechat/bind',{method:'POST',headers:{Authorization:'Bearer '+result.token},body:JSON.stringify({state:pendingWechat.value})});
  if(alive){pendingWechat.value='';completeSignIn(result);emit('signedIn');}
 }catch(e){if(alive)error.value=(e as Error).message;}finally{busy.value=false;}
}
onMounted(()=>{timer=setInterval(()=>now.value=Date.now(),1000);void commerceApi<{wechat:boolean}>('/auth/options').then(result=>{if(alive){available.value=result.wechat;if(!result.wechat&&method.value==='wechat')method.value='password';}}).catch(()=>{available.value=false;if(method.value==='wechat')method.value='password';});});
onBeforeUnmount(()=>{alive=false;clearInterval(timer);});
</script>
<template>
 <component :is="embedded?'div':SlideOver" v-bind="embedded?{}:{modelValue:accountOpen,title:say(accountUser?copy.account:accountForReservation?copy.reservation_title:copy.title),busy}" @update:model-value="(value:boolean)=>{if(!value)closeAccount();}">
 <div v-if="embedded||accountOpen" class="account-content" :class="{'account-auth':!accountUser}">
  <template v-if="!accountUser">
   <p v-if="accountForReservation" class="account-draft-note">{{say(copy.draft_saved)}}</p>
   <div v-if="!emailOnly" class="auth-methods" :aria-label="say(copy.sign_in)"><button v-if="available" class="auth-method-choice" type="button" :disabled="busy" :aria-pressed="method==='wechat'" @click="pendingWechat='';change('wechat')"><PhWechatLogo/><span>{{say(copy.wechat_method)}}</span></button><button class="auth-method-choice" type="button" :disabled="busy" :aria-pressed="method!=='wechat'" @click="change('password')"><PhKey/><span>{{say(copy.password_method)}}</span></button></div>
   <WechatQr v-if="method==='wechat'" @existing="existing" @done="emit('signedIn')"/>
   <template v-else>
    <p v-if="pendingWechat" class="account-link-notice"><PhLink/>{{say(wechatCopy.link_preserves_account)}}</p>
    <div v-if="method==='recovery'" class="auth-recovery-heading"><button class="icon-button" type="button" :aria-label="say(copy.back_password)" :disabled="busy" @click="change('password')"><PhArrowLeft/></button><LiftTitle :as="embedded?'h2':'h3'" :text="say(copy.recovery_title)"/></div>
    <form class="account-form" @submit.prevent="submit">
     <label class="field">{{say(copy.email)}}<input v-model="email" type="email" inputmode="email" autocomplete="username" maxlength="254" required :disabled="busy"/></label>
     <template v-if="method==='recovery'">
      <label class="field">{{say(copy.code)}}<span class="account-code-field"><input v-model.trim="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required :disabled="busy"/><button type="button" :disabled="sending||busy||!emailValid||cooldown>0" @click="sendCode">{{sending?say(copy.sending_code):cooldown?formatCopy(copy.resend_after,{v0:cooldown}):say(copy.send_code)}}</button></span></label>
     </template>
     <label class="field">{{say(method==='recovery'?copy.new_password:copy.password)}}<span class="account-password"><input v-model="password" :type="reveal?'text':'password'" :autocomplete="method==='recovery'?'new-password':'current-password'" :minlength="method==='recovery'?6:1" maxlength="128" required :disabled="busy"/><button class="icon-button" type="button" :aria-label="say(reveal?copy.hide_password:copy.show_password)" @click="reveal=!reveal"><PhEyeSlash v-if="reveal"/><PhEye v-else/></button></span></label>
     <label v-if="method==='recovery'" class="field">{{say(copy.confirm_password)}}<input v-model="confirmation" :type="reveal?'text':'password'" autocomplete="new-password" minlength="6" maxlength="128" required :disabled="busy"/></label>
     <p v-if="method==='recovery'&&confirmation&&password!==confirmation" class="form-error">{{say(copy.password_mismatch)}}</p>
     <p v-if="notice" class="account-note" role="status">{{notice}}</p><p v-if="error" class="form-error" role="alert">{{error}}</p>
     <button class="button button-primary" :disabled="busy||!valid">{{say(busy?copy.working:method==='recovery'?copy.reset_password:accountForReservation?copy.continue_reservation:copy.sign_in)}}<PhArrowRight/></button>
     <button v-if="method==='password'" type="button" class="account-recovery-link" :disabled="busy" @click="change('recovery')">{{say(copy.forgot_password)}}</button>
    </form>
   </template>
  </template>
  <template v-else><AccountIdentity :email-only="emailOnly" :link-to-center="!embedded"/><CustomerWallet v-if="!emailOnly"/><button v-if="!emailOnly" class="text-link account-signout" type="button" @click="signOut">{{say(copy.sign_out)}}</button></template>
 </div>
 </component>
</template>
