<script setup lang="ts">
import {computed,onBeforeUnmount,reactive,ref,watch} from 'vue';
import {PhBellRinging} from '@phosphor-icons/vue';
import {useDesk} from '../../admin';
import {say} from '../../state';
import {messageCopy as sms,type MessageBridge} from '../../messaging';
import defaults from '../../content/owner-wechat.json';
import {contentModule} from '../../content-store';
import SlideOver from '../SlideOver.vue';
const copy=contentModule('owner-wechat',defaults);
const {request}=useDesk();
type OwnerBinding={id:string;label:string;enabled:boolean;authorization_available:boolean;error:string};
type WechatSettings={enabled:boolean;available:boolean;version:number;template_id:string;bindings:OwnerBinding[];items:{id:string;state:string;error:string;reservation_id:string}[]};
type SmsSettings={owner_enabled:boolean;owner_phone:string;language:string;version:number;bridges:MessageBridge[];notifications:{id:string;state:string;error:string;reservation_id:string}[]};
const open=ref(false),busy=ref(false),error=ref(''),note=ref(''),label=ref(say(copy.owner));
const wechat=ref<WechatSettings>(),phone=ref<SmsSettings>(),qr=ref<{scene:string;qr_image:string;expires_at:number}>();
const form=reactive({owner_enabled:false,owner_phone:'',language:'zh'});
const tick=ref(Date.now()),expired=computed(()=>!!qr.value&&tick.value>=qr.value.expires_at*1000);
const sender=computed(()=>phone.value?.bridges.find(b=>b.role==='owner_alert'));
let timer:ReturnType<typeof setInterval>|undefined;
function fail(e:unknown){const code=(e as {code?:string}).code||(e as Error).message;error.value=say((copy as Record<string,string[]>)[code]||(sms as Record<string,string[]>)[code]||copy.generic_error);}
async function refresh(resetForm=false){
  const results=await Promise.allSettled([request<WechatSettings>('/manage/owner-wechat'),request<SmsSettings>('/manage/messages/settings')]);
  if(results[0].status==='fulfilled')wechat.value=results[0].value;else fail(results[0].reason);
  if(results[1].status==='fulfilled'){phone.value=results[1].value;if(resetForm)Object.assign(form,{owner_enabled:phone.value.owner_enabled,owner_phone:phone.value.owner_phone,language:phone.value.language});}else fail(results[1].reason);
}
async function act(action:()=>Promise<unknown>){if(busy.value)return;busy.value=true;error.value='';note.value='';try{await action();await refresh();note.value=say(copy.saved);}catch(e){fail(e);}finally{busy.value=false;}}
function configureTemplate(){void act(()=>request('/manage/owner-wechat/template',{method:'POST'}));}
function saveWechat(){if(wechat.value)void act(()=>request('/manage/owner-wechat',{method:'PUT',body:JSON.stringify({version:wechat.value!.version,enabled:wechat.value!.enabled})}));}
function saveSms(){if(phone.value)void act(()=>request('/manage/messages/settings',{method:'PUT',body:JSON.stringify({...form,version:phone.value!.version})}));}
async function createBinding(){await act(async()=>{qr.value=await request('/manage/owner-wechat/bindings',{method:'POST',body:JSON.stringify({label:label.value.trim()||say(copy.owner)})});});note.value='';}
function revoke(id:string){void act(()=>request('/manage/owner-wechat/bindings/'+id,{method:'DELETE'}));}
watch(open,value=>{if(value){void refresh(true);timer=setInterval(()=>{tick.value=Date.now();},1000);}else{clearInterval(timer);qr.value=undefined;}});
onBeforeUnmount(()=>clearInterval(timer));
</script>
<template>
  <button class="desk-link" @click="open=true"><PhBellRinging/>{{say(copy.channels)}}</button>
  <SlideOver v-model="open" :title="say(copy.channels)" :busy="busy">
    <div class="owner-channel-settings">
      <p v-if="error" class="desk-error" role="alert">{{error}}</p><p v-if="note" role="status">{{note}}</p>
      <section v-if="phone"><h3>{{say(sms.owner_notifications)}}</h3><p>{{say(sms.owner_channel_note)}}</p><p :class="{'channel-ready':sender?.online&&sender?.send_enabled}">{{sender?.send_enabled?(sender.online?say(sms.online):say(sms.offline)):say(sms.not_ready)}}<span v-if="sender"> · {{sender.sender}}</span></p>
        <form @submit.prevent="saveSms"><label>{{say(sms.owner_phone)}}<input v-model="form.owner_phone" type="tel" maxlength="40" autocomplete="tel"/></label><label class="owner-toggle"><input v-model="form.owner_enabled" type="checkbox" :disabled="!sender?.send_enabled"/>{{say(sms.owner_enabled)}}</label><button class="desk-button" :disabled="busy">{{say(sms.save)}}</button></form>
        <details v-if="phone.notifications.length"><summary>{{say(sms.recent_notifications)}}</summary><p v-for="item in phone.notifications" :key="item.id">{{item.reservation_id}} · {{say((sms as Record<string,string[]>)[item.state]||sms.unknown)}}</p></details>
      </section>
      <section v-if="wechat"><h3>{{say(copy.title)}}</h3><p>{{say(copy.subscription_note)}}</p><p v-if="wechat.template_id">{{say(copy.template_ready)}}</p><button v-else class="desk-button" :disabled="busy||!wechat.available" @click="configureTemplate">{{say(copy.setup_template)}}</button><form v-if="wechat.template_id" @submit.prevent="saveWechat"><label class="owner-toggle"><input v-model="wechat.enabled" type="checkbox"/>{{say(copy.enabled)}}</label><button class="desk-button" :disabled="busy">{{say(copy.save)}}</button></form>
        <div class="owner-binding-form"><label>{{say(copy.label)}}<input v-model="label" maxlength="40"/></label><button class="desk-button" :disabled="busy||!wechat.template_id" @click="createBinding">{{say(copy.bind)}}</button></div>
        <div v-if="qr" class="owner-binding-qr"><p>{{say(copy.scan)}}</p><img v-if="!expired" :src="qr.qr_image" :alt="say(copy.bind)" width="250" height="250"/><p role="status">{{say(expired?copy.expired:copy.expires)}}</p><button class="desk-link" :disabled="busy" @click="refresh()">{{say(copy.refresh)}}</button></div>
        <div v-for="binding in wechat.bindings.filter(b=>b.enabled)" :key="binding.id" class="owner-binding"><div><strong>{{binding.label}}</strong><p>{{say(binding.authorization_available?copy.authorization_available:copy.authorization_needed)}}</p></div><button class="desk-link" :disabled="busy" @click="revoke(binding.id)">{{say(copy.revoke)}}</button></div>
        <details v-if="wechat.items.length"><summary>{{say(copy.recent)}}</summary><p v-for="item in wechat.items" :key="item.id">{{item.reservation_id}} · {{say((copy as Record<string,string[]>)[item.state]||copy.unknown)}}</p></details>
      </section>
    </div>
  </SlideOver>
</template>
<style scoped>
.owner-channel-settings{display:grid;gap:25px}.owner-channel-settings>section{border-bottom:1px solid #e2e8eb;padding-bottom:24px}.owner-channel-settings h3{margin:0 0 12px}.owner-channel-settings p{font-size:13px;line-height:1.7;color:#78858b}.owner-channel-settings form,.owner-binding-form{display:grid;gap:15px;margin:15px 0}.owner-channel-settings label{display:grid;gap:7px;font-size:14px}.owner-channel-settings input:not([type=checkbox]){width:100%;font:inherit;font-size:16px;padding:12px;border:1px solid #dae4e9;border-radius:9px}.owner-channel-settings .owner-toggle{display:flex;align-items:center;gap:10px}.owner-toggle input{width:18px;height:18px}.owner-channel-settings .desk-button{justify-self:start}.owner-binding-qr{text-align:center;border:1px solid #e2e8eb;border-radius:12px;padding:14px}.owner-binding-qr img{max-width:100%;height:auto}.owner-binding{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px 0;border-top:1px solid #e8edef}.owner-binding p{margin:4px 0}.owner-channel-settings .channel-ready{color:#527864}.owner-channel-settings details{margin-top:15px;font-size:12px;overflow-wrap:anywhere}.owner-channel-settings summary{cursor:pointer}
</style>
