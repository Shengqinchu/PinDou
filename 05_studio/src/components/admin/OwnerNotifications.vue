<script setup lang="ts">
import { computed,onBeforeUnmount,onMounted,ref,watch } from 'vue';
import { PhWechatLogo,PhArrowSquareOut,PhArrowClockwise } from '@phosphor-icons/vue';
import SlideOver from '../SlideOver.vue';
import ToggleSwitch from '../ToggleSwitch.vue';
import { useDesk } from '../../admin';
import { CommerceError } from '../../commerce';
import { contentModule } from '../../content-store';
import { say,formatCopy,locale } from '../../state';
import defaults from '../../content/owner-notifications.json';
const copy=contentModule('owner-notifications',defaults) as Record<string,string[]>;
type Activity={id:string;kind:string;reservation_id:string;state:string;error:string;created_at:number;attempts:number};
type Settings={version:number;enabled:boolean;configured:boolean;daily_limit:number;language:string;used:number;items:Activity[]};
const {request}=useDesk();
const open=ref(false),busy=ref(false),loading=ref(false),error=ref(''),notice=ref(''),sendkey=ref('');
const saved=ref<Settings>(),enabled=ref(false),dailyLimit=ref(5),language=ref('zh');
const draftVersion=ref(0);
const statusText=computed(()=>say(!saved.value?.configured?copy.not_configured:saved.value.enabled?copy.configured:copy.paused));
const dirty=computed(()=>!!sendkey.value||enabled.value!==!!saved.value?.enabled||dailyLimit.value!==saved.value?.daily_limit||language.value!==saved.value?.language);
let timer:ReturnType<typeof setInterval>|undefined,testId='';
function fail(e:unknown){error.value=say(copy[e instanceof CommerceError?e.code||'generic_error':'generic_error']||copy.generic_error);}
async function load(reset=false){if(loading.value)return;loading.value=true;try{saved.value=await request<Settings>('/manage/owner-notifications');if(reset){enabled.value=!!saved.value.enabled;dailyLimit.value=saved.value.daily_limit;language.value=saved.value.language;draftVersion.value=saved.value.version;}}catch(e){fail(e);}finally{loading.value=false;}}
async function show(){open.value=true;error.value='';notice.value='';await load(true);}
async function save(){if(busy.value||!saved.value)return;busy.value=true;error.value='';notice.value='';try{saved.value=await request<Settings>('/manage/owner-notifications',{method:'PUT',body:JSON.stringify({version:draftVersion.value,enabled:enabled.value,daily_limit:dailyLimit.value,language:language.value,...(sendkey.value.trim()?{sendkey:sendkey.value.trim()}:{})})});draftVersion.value=saved.value.version;sendkey.value='';testId='';notice.value=say(copy.saved);}catch(e){fail(e);}finally{busy.value=false;}}
async function test(){if(busy.value)return;busy.value=true;error.value='';notice.value='';testId ||= crypto.randomUUID();try{await request('/manage/owner-notifications/test',{method:'POST',body:JSON.stringify({request_id:testId})});testId='';notice.value=say(copy.test_queued);await load();}catch(e){fail(e);}finally{busy.value=false;}}
async function retry(id:string){if(busy.value)return;busy.value=true;error.value='';try{await request('/manage/owner-notifications/'+id+'/retry',{method:'POST'});await load();}catch(e){fail(e);}finally{busy.value=false;}}
function date(value:number){return new Intl.DateTimeFormat(locale.value==='zh'?'zh-CN':'en-CA',{timeZone:'America/Toronto',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(value*1000);}
onMounted(()=>{void load(true);timer=setInterval(()=>{if(open.value&&!document.hidden&&!busy.value)void load();},5000);});
onBeforeUnmount(()=>{clearInterval(timer);sendkey.value='';});
watch(open,value=>{if(!value)sendkey.value='';});
</script>
<template>
 <button type="button" class="desk-link owner-notifications-open" @click="show"><PhWechatLogo/>{{say(copy.open)}}</button>
 <SlideOver v-model="open" :title="say(copy.title)" :busy="busy">
  <div class="owner-notifications">
   <p>{{say(copy.intro)}}</p><p class="owner-notification-status" role="status">{{statusText}}</p>
   <p v-if="loading&&!saved">{{say(copy.loading)}}</p>
   <form v-if="saved" @submit.prevent="save">
    <a class="text-link" href="https://sct.ftqq.com/" target="_blank" rel="noopener noreferrer">{{say(copy.get_key)}} <PhArrowSquareOut/></a>
    <label>{{say(copy.key)}}<input v-model="sendkey" type="password" autocomplete="off" autocapitalize="none" :spellcheck="false" maxlength="200" :disabled="busy" :aria-label="say(copy.key)"/></label>
    <p class="form-help">{{say(copy.key_help)}}</p>
    <div class="owner-notification-toggle"><span>{{say(copy.enabled)}}</span><ToggleSwitch v-model="enabled" :label="say(copy.enabled)" :disabled="busy"/></div>
    <fieldset :disabled="busy"><legend>{{say(copy.quota)}}</legend><label class="owner-quota-option"><input v-model="dailyLimit" type="radio" :value="5" name="owner-alert-quota"/>{{say(copy.free)}}</label><label class="owner-quota-option"><input v-model="dailyLimit" type="radio" :value="1000" name="owner-alert-quota"/>{{say(copy.member)}}</label></fieldset>
    <p class="form-help">{{say(copy.quota_help)}}</p>
    <fieldset :disabled="busy"><legend>{{say(copy.language)}}</legend><label class="owner-quota-option"><input v-model="language" type="radio" value="zh" name="owner-alert-language"/>{{say(copy.zh)}}</label><label class="owner-quota-option"><input v-model="language" type="radio" value="en" name="owner-alert-language"/>{{say(copy.en)}}</label></fieldset>
    <button class="desk-button primary" type="submit" :disabled="busy||!dirty">{{say(busy?copy.saving:copy.save)}}</button>
   </form>
   <p v-if="error" class="form-error" role="alert">{{error}} <button type="button" class="desk-link" :disabled="busy||loading" @click="load(true)">{{say(copy.refresh)}}</button></p>
   <p v-if="notice" role="status">{{notice}}</p>
   <div class="owner-notification-test"><button type="button" class="desk-button" :disabled="busy||!saved?.configured||!saved.enabled||dirty" @click="test">{{say(copy.test)}}</button><p class="form-help">{{say(copy.test_help)}}</p></div>
   <div class="owner-notification-log-title"><h3>{{say(copy.log)}}</h3><button type="button" class="icon-button" :aria-label="say(copy.refresh)" :disabled="loading||busy" @click="load()"><PhArrowClockwise/></button></div>
   <p v-if="saved" class="form-help">{{formatCopy(copy.usage,{v0:saved.used,v1:saved.daily_limit})}}</p>
   <p class="form-help">{{say(copy.accepted_help)}}</p>
   <p v-if="saved&&!saved.items.length">{{say(copy.empty)}}</p>
    <ol class="owner-notification-log"><li v-for="item in saved?.items" :key="item.id"><div><strong>{{say(copy[item.kind==='test'?'test_kind':item.kind])}}</strong><span :data-state="item.state">{{say(copy[item.state])}}</span></div><time>{{date(item.created_at)}}</time><p v-if="item.reservation_id">{{item.reservation_id}}</p><p v-if="item.error">{{say(copy[item.error]||copy.generic_error)}}</p><button v-if="item.state==='failed'&&(item.kind==='created'||item.attempts<8)" type="button" class="desk-link" :disabled="busy||!saved?.enabled||dirty" @click="retry(item.id)">{{say(copy.retry_action)}}</button></li></ol>
  </div>
 </SlideOver>
</template>
<style scoped>
.owner-notification-toggle{display:flex;align-items:center;justify-content:space-between;gap:16px}
.owner-notifications-open{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;min-height:44px}.owner-notifications{display:grid;gap:16px;color:var(--ink,#303437);overflow-wrap:anywhere}.owner-notifications>p{margin:0}.owner-notification-status{font-size:14px;color:#536f62}.owner-notifications form{display:grid;gap:16px}.owner-notifications label:not(.owner-quota-option){display:grid;gap:8px}.owner-notifications input[type=password]{width:100%;min-width:0;min-height:48px;padding:12px;border:1px solid #ccd9e1;border-radius:12px;font-size:16px;background:#fff}.owner-notifications .form-help{margin:0;line-height:1.65;font-size:13px}.owner-notifications fieldset{min-width:0;padding:0;border:0;display:flex;flex-wrap:wrap;gap:8px 20px}.owner-notifications legend{margin-bottom:8px}.owner-quota-option{display:flex;align-items:center;gap:8px;min-height:44px}.owner-quota-option input{width:18px;height:18px;accent-color:#607f99}.owner-notifications .desk-button{justify-self:start;min-height:44px;white-space:normal}.owner-notification-test{display:grid;gap:8px;padding-block:20px;border-block:1px solid #dce3e8}.owner-notification-log-title{display:flex;align-items:center;justify-content:space-between;gap:12px}.owner-notification-log-title h3{margin:0;font-size:18px}.owner-notification-log{list-style:none;margin:0;padding:0}.owner-notification-log li{padding:16px 0;border-bottom:1px solid #dce3e8;display:grid;gap:6px}.owner-notification-log li>div{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.owner-notification-log li p,.owner-notification-log time{margin:0;font-size:13px;color:#68747c}.owner-notification-log [data-state=failed]{color:#a04c3f}.owner-notification-log [data-state=accepted]{color:#536f62}.owner-notification-log .desk-link{justify-self:start}
</style>
