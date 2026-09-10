<script setup lang="ts">
import { computed,onMounted,onBeforeUnmount,ref } from 'vue';
import { useRoute } from 'vue-router';
import { PhWechatLogo,PhArrowClockwise,PhCheck,PhUserCircle,PhLink } from '@phosphor-icons/vue';
import { commerceApi } from '../commerce';
import { completeSignIn,type SignInResult } from '../account';
import { accountReturn,wechatCopy as copy } from '../wechat';
import { say } from '../state';
import { wechatQrImage } from '../wechat-qr-image';
const props=withDefaults(defineProps<{linking?:boolean}>(),{linking:false});
const emit=defineEmits<{done:[];existing:[state:string]}>();
const route=useRoute(),state=ref(''),source=ref(''),status=ref('loading'),error=ref(''),busy=ref(false);
let alive=true,version=0,timer:ReturnType<typeof setTimeout>|undefined,expires=0;
const statusText=computed(()=>say(status.value==='qr_scanned'?copy.scanned:status.value==='loading'?copy.loading_qr:status.value==='qr_exchanging'?copy.checking:copy.sign_in));
function schedule(){clearTimeout(timer);if(alive)timer=setTimeout(()=>void poll(),1800);}
async function finish(){
 const result=await commerceApi<SignInResult>('/auth/wechat/finish',{method:'POST',body:JSON.stringify({state:state.value})});
 if(alive){completeSignIn(result);emit('done');}
}
async function poll(){
 if(!alive||!['qr_pending','qr_scanned','qr_exchanging'].includes(status.value))return;
 if(Date.now()>expires){status.value='failed';error.value=say(copy.wechat_flow_expired);return;}
 if(document.hidden){schedule();return;}
 const current=version;
 try{
  const result=await commerceApi<{status:string;error?:string}>('/auth/wechat/qr/poll',{method:'POST',body:JSON.stringify({state:state.value})});
  if(!alive||current!==version)return;
  status.value=result.status;error.value='';
  if(result.status==='ready'){await finish();return;}
  if(result.status==='linked'){emit('done');return;}
  if(result.status==='failed'){error.value=say((copy as Record<string,string[]>)[result.error||'']||copy.wechat_provider_unavailable);return;}
  if(['qr_pending','qr_scanned','qr_exchanging'].includes(result.status))schedule();
 }catch(e){if(alive&&current===version){error.value=(e as Error).message;schedule();}}
}
async function start(){
 const current=++version;clearTimeout(timer);status.value='loading';error.value='';source.value='';state.value='';
 try{
  const returnTo=accountReturn(route.query.return_to,route.path==='/account'?'/account':route.fullPath);
  const result=await commerceApi<{state:string;image:string;logo?:string;expires_in:number}>('/auth/wechat/qr/start',{method:'POST',body:JSON.stringify({mode:props.linking?'link':'login',return_to:returnTo})});
  if(!alive||current!==version)return;
  expires=Date.now()+result.expires_in*1000;
  const image=await wechatQrImage(result.image,result.logo);
  if(!alive||current!==version)return;
  state.value=result.state;source.value=image;status.value='qr_pending';schedule();
 }catch(e){if(alive&&current===version){status.value='failed';error.value=(e as Error).message;}}
}
async function create(){
 if(busy.value)return;busy.value=true;error.value='';
 try{await commerceApi('/auth/wechat/create-account',{method:'POST',body:JSON.stringify({state:state.value})});if(alive)await finish();}
 catch(e){if(alive)error.value=(e as Error).message;}finally{busy.value=false;}
}
function resume(){if(!document.hidden){clearTimeout(timer);void poll();}}
onMounted(()=>{void start();document.addEventListener('visibilitychange',resume);});
onBeforeUnmount(()=>{alive=false;++version;clearTimeout(timer);document.removeEventListener('visibilitychange',resume);});
</script>
<template>
 <section class="wechat-qr" :aria-label="say(copy.title)">
  <template v-if="status==='needs_email'">
   <PhCheck class="wechat-verified-icon" :size="36"/>
   <p class="wechat-qr-title">{{say(copy.authorized)}}</p>
   <div class="wechat-account-choices"><button type="button" class="auth-method-choice" :disabled="busy" @click="emit('existing',state)"><PhLink/>{{say(copy.existing_account)}}</button><button type="button" class="auth-method-choice" :disabled="busy" @click="create"><PhUserCircle/>{{say(busy?copy.checking:copy.new_account)}}</button></div>
  </template>
  <template v-else>
   <div class="wechat-qr-window" :class="{'is-loading':status==='loading'}" :aria-busy="status==='loading'">
    <img v-if="source&&status==='qr_pending'" :src="source" :alt="say(copy.qr_alt)" width="240" height="240" referrerpolicy="no-referrer" @error="status='failed';error=say(copy.wechat_provider_unavailable)"/>
    <div v-else-if="status==='failed'" class="wechat-qr-placeholder"><button type="button" class="icon-button" :aria-label="say(copy.refresh_qr)" @click="start"><PhArrowClockwise :size="30"/></button></div>
    <div v-else class="wechat-qr-placeholder"><PhCheck v-if="status==='qr_scanned'" :size="44"/><PhWechatLogo v-else :size="44" weight="light"/></div>
   </div>
   <p class="wechat-qr-title" role="status">{{status==='failed'?say(copy.refresh_qr):statusText}}</p>
  </template>
  <p v-if="error" role="alert" class="form-error">{{error}}</p>
 </section>
</template>
