<script setup lang="ts">
import { computed,onMounted,onBeforeUnmount,ref,watch,useId } from 'vue';
import { PhArrowRight,PhArrowLeft,PhEye,PhEyeSlash,PhLink } from '@phosphor-icons/vue';
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
type Method='register'|'password'|'wechat'|'recovery';
const method=ref<Method>('password');
const tabId=useId();
const available=ref(true),email=ref(''),password=ref(''),confirmation=ref(''),code=ref(''),reveal=ref(false);
const busy=ref(false),sending=ref(false),error=ref(''),notice=ref(''),pendingWechat=ref(''),now=ref(Date.now());
const sentUntil=new Map<string,number>();let timer:ReturnType<typeof setInterval>,alive=true;
const normalizedEmail=computed(()=>email.value.trim().toLowerCase());
const emailValid=computed(()=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail.value));
const cooldown=computed(()=>Math.max(0,Math.ceil(((sentUntil.get(normalizedEmail.value)||0)-now.value)/1000)));
const createsPassword=computed(()=>method.value==='register'||method.value==='recovery');
const valid=computed(()=>emailValid.value&&password.value.length>=(createsPassword.value?6:1)&&(!createsPassword.value||password.value===confirmation.value)&&(method.value!=='recovery'||/^\d{6}$/.test(code.value)));
const activeTab=computed(()=>method.value==='recovery'?'password':method.value);
const tabs=computed(()=>[{value:'register' as const,label:copy.register},{value:'password' as const,label:copy.sign_in},...(available.value?[{value:'wechat' as const,label:copy.wechat_method}]:[])]);
function change(value:Method){if(busy.value)return;method.value=value;error.value='';notice.value='';code.value='';password.value='';confirmation.value='';reveal.value=false;}
function choose(value:Method){if(busy.value)return;if(value!=='password')pendingWechat.value='';change(value);}
function tabKey(event:KeyboardEvent,index:number){
 const next=event.key==='ArrowRight'?(index+1)%tabs.value.length:event.key==='ArrowLeft'?(index+tabs.value.length-1)%tabs.value.length:event.key==='Home'?0:event.key==='End'?tabs.value.length-1:-1;
 if(next<0||busy.value)return;event.preventDefault();choose(tabs.value[next].value);(event.currentTarget as HTMLElement).parentElement?.querySelectorAll<HTMLButtonElement>('[role=tab]')[next]?.focus();
}
function existing(state:string){pendingWechat.value=state;change('password');}
watch(accountOpen,value=>{if(!props.embedded){if(value)method.value='password';else{pendingWechat.value='';error.value='';notice.value='';code.value='';password.value='';confirmation.value='';reveal.value=false;}}});
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
  const result=await commerceApi<SignInResult>(method.value==='register'?'/auth/password-register':'/auth/password-login',{method:'POST',body:JSON.stringify({email:normalizedEmail.value,password:password.value})});
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
   <div v-if="!emailOnly" class="auth-methods" role="tablist" :aria-label="say(copy.sign_in)"><button v-for="(tab,index) in tabs" :id="tabId+'-'+tab.value" :key="tab.value" class="auth-method-choice" role="tab" type="button" :disabled="busy" :aria-selected="activeTab===tab.value" :aria-controls="tabId+'-panel'" :tabindex="activeTab===tab.value?0:-1" @keydown="tabKey($event,index)" @click="choose(tab.value)">{{say(tab.label)}}</button></div>
   <div :id="tabId+'-panel'" class="auth-method-panel" :role="emailOnly?undefined:'tabpanel'" :aria-labelledby="emailOnly?undefined:tabId+'-'+activeTab">
   <WechatQr v-if="method==='wechat'" @existing="existing" @done="emit('signedIn')"/>
   <template v-else>
    <p v-if="pendingWechat" class="account-link-notice"><PhLink/>{{say(wechatCopy.link_preserves_account)}}</p>
    <div v-if="method==='recovery'" class="auth-recovery-heading"><button class="icon-button" type="button" :aria-label="say(copy.back_password)" :disabled="busy" @click="change('password')"><PhArrowLeft/></button><LiftTitle :as="embedded?'h2':'h3'" :text="say(copy.recovery_title)"/></div>
    <form class="account-form" @submit.prevent="submit">
     <label class="field">{{say(copy.email)}}<input v-model="email" type="email" inputmode="email" autocomplete="username" maxlength="254" required :disabled="busy"/></label>
     <template v-if="method==='recovery'">
      <label class="field">{{say(copy.code)}}<span class="account-code-field"><input v-model.trim="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required :disabled="busy"/><button type="button" :disabled="sending||busy||!emailValid||cooldown>0" @click="sendCode">{{sending?say(copy.sending_code):cooldown?formatCopy(copy.resend_after,{v0:cooldown}):say(copy.send_code)}}</button></span></label>
     </template>
     <label class="field">{{say(createsPassword?copy.new_password:copy.password)}}<span class="account-password"><input v-model="password" :type="reveal?'text':'password'" :autocomplete="createsPassword?'new-password':'current-password'" :minlength="createsPassword?6:1" maxlength="128" required :disabled="busy"/><button class="icon-button" type="button" :aria-label="say(reveal?copy.hide_password:copy.show_password)" @click="reveal=!reveal"><PhEyeSlash v-if="reveal"/><PhEye v-else/></button></span></label>
     <label v-if="createsPassword" class="field">{{say(copy.confirm_password)}}<input v-model="confirmation" :type="reveal?'text':'password'" autocomplete="new-password" minlength="6" maxlength="128" required :disabled="busy"/></label>
     <p v-if="createsPassword&&confirmation&&password!==confirmation" class="form-error">{{say(copy.password_mismatch)}}</p>
     <p v-if="notice" class="account-note" role="status">{{notice}}</p><p v-if="error" class="form-error" role="alert">{{error}}</p>
     <button class="button button-primary" :disabled="busy||!valid">{{say(busy?(method==='register'?copy.registering:copy.working):method==='recovery'?copy.reset_password:method==='register'?copy.register:accountForReservation?copy.continue_reservation:copy.sign_in)}}<PhArrowRight/></button>
     <button v-if="method==='password'" type="button" class="account-recovery-link" :disabled="busy" @click="change('recovery')">{{say(copy.forgot_password)}}</button>
    </form>
   </template>
   </div>
  </template>
  <template v-else><AccountIdentity :key="accountUser.id" :email-only="emailOnly" :link-to-center="!embedded&&!emailOnly"/><CustomerWallet v-if="!emailOnly" :key="accountUser.id"/><button v-if="!emailOnly" class="text-link account-signout" type="button" @click="signOut">{{say(copy.sign_out)}}</button></template>
 </div>
 </component>
</template>
