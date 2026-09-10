<script setup lang="ts">
import { computed,onBeforeUnmount,onMounted,ref,watch } from 'vue';
import { PhTelegramLogo,PhArrowSquareOut,PhArrowClockwise } from '@phosphor-icons/vue';
import SlideOver from '../SlideOver.vue';
import ToggleSwitch from '../ToggleSwitch.vue';
import { useDesk } from '../../admin';
import { CommerceError } from '../../commerce';
import { contentModule } from '../../content-store';
import { say,locale } from '../../state';
import defaults from '../../content/telegram-notifications.json';
import sharedDefaults from '../../content/owner-notifications.json';
const copy=contentModule('telegram-notifications',defaults) as Record<string,string[]>;
const common=contentModule('owner-notifications',sharedDefaults) as Record<string,string[]>;
type Activity={id:string;kind:string;reservation_id:string;state:string;error:string;created_at:number;attempts:number};
type Settings={version:number;enabled:boolean;configured:boolean;connected:boolean;language:string;bot_username:string;chat_label:string;items:Activity[]};
type Binding={id:string;url:string;expires_at:number};
const {request}=useDesk();
const open=ref(false),busy=ref(false),loading=ref(false),checking=ref(false),token=ref(''),error=ref(''),notice=ref('');
const saved=ref<Settings>(),enabled=ref(false),language=ref('zh'),draftVersion=ref(0),binding=ref<Binding>();
const dirty=computed(()=>!!token.value||enabled.value!==!!saved.value?.enabled||language.value!==saved.value?.language);
const statusText=computed(()=>say(!saved.value?.configured?copy.not_configured:!saved.value.connected?copy.not_bound:saved.value.enabled?copy.connected:copy.paused));
let timer:ReturnType<typeof setInterval>|undefined,testId='';
const path='/manage/telegram-notifications';
function fail(e:unknown){const code=e instanceof CommerceError?e.code||'generic_error':'generic_error';error.value=say(copy[code]||common[code]||common.generic_error);}
function resetDraft(){if(!saved.value)return;enabled.value=!!saved.value.enabled;language.value=saved.value.language;draftVersion.value=saved.value.version;}
async function load(reset=false){if(loading.value)return;loading.value=true;try{saved.value=await request<Settings>(path);if(reset)resetDraft();}catch(e){fail(e);}finally{loading.value=false;}}
async function show(){open.value=true;error.value='';notice.value='';await load(true);}
async function save(){if(busy.value||!saved.value)return;busy.value=true;error.value='';notice.value='';try{saved.value=await request<Settings>(path,{method:'PUT',body:JSON.stringify({version:draftVersion.value,enabled:enabled.value,language:language.value,...(token.value.trim()?{token:token.value.trim()}:{})})});token.value='';binding.value=undefined;resetDraft();notice.value=say(common.saved);}catch(e){fail(e);}finally{busy.value=false;}}
async function bind(){if(busy.value)return;busy.value=true;error.value='';notice.value='';try{binding.value=await request<Binding>(path+'/bind',{method:'POST'});}catch(e){fail(e);}finally{busy.value=false;}}
async function check(){if(checking.value||busy.value||!binding.value)return;checking.value=true;try{const result=await request<{connected:boolean;settings?:Settings}>(path+'/bind/check',{method:'POST',body:JSON.stringify({id:binding.value.id})});if(result.connected&&result.settings){saved.value=result.settings;binding.value=undefined;resetDraft();notice.value=say(copy.bound);error.value='';}}catch(e){fail(e);if(e instanceof CommerceError&&['telegram_binding_expired','version_conflict'].includes(e.code||''))binding.value=undefined;}finally{checking.value=false;}}
async function test(){if(busy.value)return;busy.value=true;error.value='';notice.value='';testId ||= crypto.randomUUID();try{await request(path+'/test',{method:'POST',body:JSON.stringify({request_id:testId})});testId='';notice.value=say(copy.test_queued);await load();}catch(e){fail(e);}finally{busy.value=false;}}
async function retry(id:string){if(busy.value)return;busy.value=true;error.value='';try{await request(path+'/'+id+'/retry',{method:'POST'});await load();}catch(e){fail(e);}finally{busy.value=false;}}
function date(value:number){return new Intl.DateTimeFormat(locale.value==='zh'?'zh-CN':'en-CA',{timeZone:'America/Toronto',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(value*1000);}
onMounted(()=>{void load(true);timer=setInterval(()=>{if(open.value&&!document.hidden&&!busy.value){if(binding.value)void check();else void load();}},3000);});
onBeforeUnmount(()=>{clearInterval(timer);token.value='';});
watch(open,value=>{if(!value)token.value='';});
</script>
<template>
 <button type="button" class="desk-link telegram-notifications-open" @click="show"><PhTelegramLogo/>{{say(copy.open)}}</button>
 <SlideOver v-model="open" :title="say(copy.title)" :busy="busy">
  <div class="telegram-notifications">
   <p>{{say(copy.intro)}}</p><p class="telegram-status" role="status">{{statusText}}<span v-if="saved?.bot_username"> · @{{saved.bot_username}}</span></p>
   <p v-if="loading&&!saved">{{say(common.loading)}}</p>
   <form v-if="saved" @submit.prevent="save">
    <a class="text-link" href="https://t.me/BotFather" target="_blank" rel="noopener noreferrer">{{say(copy.botfather)}} <PhArrowSquareOut/></a>
    <label>{{say(copy.token)}}<input v-model="token" type="password" autocomplete="off" autocapitalize="none" :spellcheck="false" maxlength="150" :disabled="busy" :aria-label="say(copy.token)"/></label>
    <p class="form-help">{{say(copy.token_help)}}</p>
    <div v-if="saved.connected" class="telegram-toggle"><span>{{say(copy.enabled)}}</span><ToggleSwitch v-model="enabled" :label="say(copy.enabled)" :disabled="busy"/></div>
    <fieldset :disabled="busy"><legend>{{say(common.language)}}</legend><label class="telegram-option"><input v-model="language" type="radio" value="zh" name="telegram-language"/>{{say(common.zh)}}</label><label class="telegram-option"><input v-model="language" type="radio" value="en" name="telegram-language"/>{{say(common.en)}}</label></fieldset>
    <button class="desk-button primary" type="submit" :disabled="busy||!dirty">{{say(busy?common.saving:common.save)}}</button>
   </form>
   <p v-if="error" class="form-error" role="alert">{{error}} <button type="button" class="desk-link" :disabled="busy||loading" @click="load(true)">{{say(common.refresh)}}</button></p>
   <p v-if="notice" role="status">{{notice}}</p>
   <section v-if="saved?.configured" class="telegram-pairing">
    <p v-if="saved.connected"><strong>{{say(copy.recipient)}}</strong> · {{saved.chat_label}}</p>
    <p>{{say(copy.bind_help)}}</p>
    <button type="button" class="desk-button telegram-bind" :disabled="busy||checking||dirty" @click="bind">{{say(saved.connected?copy.change:copy.bind)}}</button>
    <template v-if="binding"><a class="desk-button primary telegram-pair-link" :href="binding.url" target="_blank" rel="noopener noreferrer">{{say(copy.open_bot)}} <PhArrowSquareOut/></a><p role="status">{{say(copy.waiting)}}</p><button type="button" class="desk-link" :disabled="checking||busy" @click="check">{{say(copy.check)}}</button></template>
   </section>
   <div class="telegram-test"><button type="button" class="desk-button" :disabled="busy||!saved?.connected||!saved.enabled||dirty" @click="test">{{say(copy.test)}}</button><p class="form-help">{{say(copy.free_help)}}</p></div>
   <div class="telegram-log-title"><h3>{{say(common.log)}}</h3><button type="button" class="icon-button" :aria-label="say(common.refresh)" :disabled="loading||busy" @click="load()"><PhArrowClockwise/></button></div>
   <p class="form-help">{{say(copy.accepted_help)}}</p><p v-if="saved&&!saved.items.length">{{say(common.empty)}}</p>
   <ol class="telegram-log"><li v-for="item in saved?.items" :key="item.id"><div><strong>{{say(common[item.kind==='test'?'test_kind':item.kind])}}</strong><span :data-state="item.state">{{say(common[item.state])}}</span></div><time>{{date(item.created_at)}}</time><p v-if="item.reservation_id">{{item.reservation_id}}</p><p v-if="item.error">{{say(copy[item.error]||common[item.error]||common.generic_error)}}</p><button v-if="item.state==='failed'&&item.attempts<8" type="button" class="desk-link" :disabled="busy||!saved?.enabled||dirty" @click="retry(item.id)">{{say(common.retry_action)}}</button></li></ol>
  </div>
 </SlideOver>
</template>
<style scoped>
.telegram-notifications-open{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;min-height:44px}.telegram-notifications{display:grid;gap:16px;overflow-wrap:anywhere}.telegram-notifications p{margin:0}.telegram-status{font-size:14px;color:#536f62}.telegram-notifications form{display:grid;gap:16px}.telegram-notifications label:not(.telegram-option){display:grid;gap:8px}.telegram-notifications input[type=password]{width:100%;min-width:0;min-height:48px;padding:12px;border:1px solid #ccd9e1;border-radius:12px;font-size:16px;background:#fff}.telegram-notifications .form-help{margin:0;line-height:1.65;font-size:13px}.telegram-notifications fieldset{min-width:0;padding:0;border:0;display:flex;flex-wrap:wrap;gap:8px 20px}.telegram-notifications legend{margin-bottom:8px}.telegram-option{display:flex;align-items:center;gap:8px;min-height:44px}.telegram-option input{width:18px;height:18px;accent-color:#607f99}.telegram-notifications .desk-button{justify-self:start;min-height:44px;white-space:normal}.telegram-toggle{display:flex;align-items:center;justify-content:space-between;gap:16px}.telegram-pairing,.telegram-test{display:grid;gap:12px;padding-block:20px;border-block:1px solid #dce3e8}.telegram-log-title{display:flex;align-items:center;justify-content:space-between;gap:12px}.telegram-log-title h3{margin:0;font-size:18px}.telegram-log{list-style:none;margin:0;padding:0}.telegram-log li{padding:16px 0;border-bottom:1px solid #dce3e8;display:grid;gap:6px}.telegram-log li>div{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.telegram-log li p,.telegram-log time{font-size:13px;color:#68747c}.telegram-log [data-state=failed]{color:#a04c3f}.telegram-log [data-state=accepted]{color:#536f62}.telegram-notifications .desk-link{justify-self:start}
</style>
