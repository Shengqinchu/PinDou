<script setup lang="ts">
import notices from '../../../../05_studio/src/content/customer-notifications.json';
import {nextTick,ref} from 'vue';
import {onLoad,onShow,onHide,onUnload} from '@dcloudio/uni-app';
import StudioAdminShell from '../../components/StudioAdminShell.vue';
import {useStudioNative} from '../../utils/studio-native';
import {adminCall,adminError,goAdmin,requestKey} from '../../utils/studio-admin';
import copy from '../../../../05_studio/src/content/messaging.json';
import workbenchCopy from '../../../../05_studio/src/content/workbench.json';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const thread=ref<any>(),messages=ref<any[]>([]),bridge=ref<any>(),busy=ref(false),sending=ref(false),error=ref(''),draft=ref(''),before=ref<number|null>(null),target=ref(''),showBookings=ref(false);
let ident='',active=false,timer:ReturnType<typeof setInterval>|undefined,readSeq=0,attempt:{content:string;id:string}|null=null;
const words=(key:string)=>say((copy as Record<string,string[]>)[key]||copy.unknown);
const dateText=(stamp:number)=>new Date(stamp*1000).toLocaleString(language.value==='zh'?'zh-CN':'en-CA',{timeZone:'America/Toronto',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false});
async function load(older=false){if(!ident||busy.value)return;busy.value=true;
 try{const result=await adminCall<any>('/manage/messages/threads/'+ident,older&&before.value?{before:before.value}:{});if(!active)return;thread.value=result.thread;
 const max=messages.value.at(-1)?.seq||0;messages.value=[...new Map([...messages.value,...result.items].map(m=>[m.id,m])).values()].sort((a,b)=>a.seq-b.seq);
 if(older||max===0)before.value=result.next_before;error.value='';
 if(!older&&messages.value.at(-1)?.seq>max){await nextTick();target.value='message-'+messages.value.at(-1).id;}
 const latest=Math.max(0,...result.items.map((m:any)=>m.seq));if(latest>readSeq){await adminCall('/manage/messages/threads/'+ident+'/read',{through_seq:latest},'POST');readSeq=latest;}
 }catch(e){if(active)error.value=adminError(e,say);}finally{busy.value=false;}}
async function ready(){try{const result=await adminCall<any>('/manage/messages/threads');if(active)bridge.value=result.bridge;}catch(e){if(active)error.value=adminError(e,say);}}
async function send(){const content=draft.value.trim();if(!content||sending.value||!bridge.value?.send_enabled)return;attempt=attempt?.content===content?attempt:{content,id:requestKey()};sending.value=true;error.value='';
 try{const result=await adminCall<any>('/manage/messages/threads/'+ident+'/messages',{request_id:attempt.id,content},'POST');messages.value=[...new Map([...messages.value,result].map(m=>[m.id,m])).values()].sort((a,b)=>a.seq-b.seq);if(draft.value.trim()===content)draft.value='';attempt=null;await nextTick();target.value='message-'+result.id;}
 catch(e){error.value=adminError(e,say);}finally{sending.value=false;}}
async function handled(){if(!thread.value)return;try{await adminCall('/manage/messages/threads/'+ident,{status:thread.value.status==='open'?'closed':'open'},'PATCH');void load();}catch(e){error.value=adminError(e,say);}}
function stop(){active=false;clearInterval(timer);timer=undefined;}
onLoad(q=>{ident=typeof q?.id==='string'?q.id:'';});onShow(()=>{active=true;void load();void ready();clearInterval(timer);timer=setInterval(()=>{if(active)void load();},2000);});onHide(stop);onUnload(stop);
</script>
<template><StudioAdminShell :title="thread?.name||thread?.phone||say(copy.title)" active="messages" back :language="language" :shell-style="shellStyle" :keyboard-open="keyboardOpen" :error="error" :scroll-to="target" @refresh="load();ready()" @language="changeLanguage">
 <view v-if="thread" class="admin-row native-chat-tools"><text class="admin-muted">{{thread.phone}}</text><button class="admin-secondary" @tap="handled">{{say(thread.status==='open'?copy.close:copy.reopen)}}</button></view>
 <view v-if="thread?.reservations?.length" class="admin-card admin-stack"><button class="admin-row" @tap="showBookings=!showBookings"><text>{{say(copy.reservation)}} · {{thread.reservations.length}}</text><text>{{showBookings?'−':'+'}}</text></button><template v-if="showBookings"><button v-for="booking in thread.reservations" :key="booking.id" class="admin-secondary" @tap="goAdmin('-reservation','id='+booking.id)">{{booking.name}} · {{booking.booking.date}}</button></template></view>
 <button v-if="before" class="admin-secondary" :disabled="busy" @tap="load(true)">{{say(workbenchCopy.more)}}</button>
 <view v-for="message in messages" :key="message.id" :id="'message-'+message.id" :class="['native-chat-line',{'is-outbound':message.direction==='outbound'}]"><view class="native-chat-bubble"><text class="admin-muted">{{message.channel}} · {{say(message.source==='notification'?notices.automatic:message.source==='desk'?copy.desk_source:copy.phone_source)}}</text><text class="native-chat-content" selectable>{{message.content}}</text><text class="native-chat-time">{{dateText(message.created_at)}}<text v-if="message.direction==='outbound'"> · {{words(message.state)}}</text></text></view></view>
 <view v-if="!busy&&!messages.length" class="admin-empty">{{say(copy.no_messages)}}</view>
 <template #actions><view class="native-chat-composer"><textarea v-model="draft" class="admin-textarea" :placeholder="say(copy.write)" maxlength="2000" :adjust-position="false" :disabled="sending"/><button class="admin-primary" :disabled="sending||!draft.trim()||!bridge?.send_enabled" hover-class="admin-pressed" @tap="send">{{say(sending?copy.sending:copy.send)}}</button></view></template>
 </StudioAdminShell></template>
<style scoped>.native-chat-tools{margin-bottom:12px}.native-chat-tools .admin-secondary{font-size:12px;padding:8px 10px}.native-chat-line{display:flex;margin:12px 0;scroll-margin-bottom:12px}.native-chat-line.is-outbound{justify-content:flex-end}.native-chat-bubble{display:flex;flex-direction:column;gap:7px;background:white;border:1px solid #e0e8ed;border-radius:12px;padding:11px 13px;max-width:87%;min-width:100px}.is-outbound .native-chat-bubble{background:#e5f1f8;border-color:#dbeaf3}.native-chat-content{white-space:pre-wrap;word-break:break-word;font-size:15px;line-height:1.6}.native-chat-bubble>.admin-muted{font-size:10px}.native-chat-time{color:#7b91a0;font-size:10px;text-align:right;line-height:1.4}.native-chat-composer{display:flex;align-items:flex-end;gap:8px;padding:10px 0}.native-chat-composer textarea{flex:1;min-width:0;height:72px;min-height:72px}.native-chat-composer button{flex-shrink:0;max-width:100px;font-size:13px;padding:12px}.native-chat-composer .admin-textarea{font-size:16px}@media(max-height:500px){.native-chat-composer textarea{height:44px;min-height:44px}}</style>
