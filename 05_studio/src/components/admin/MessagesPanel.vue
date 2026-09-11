<script setup lang="ts">
import {computed,nextTick,onActivated,onBeforeUnmount,onDeactivated,onMounted,reactive,ref,watch} from 'vue';
import {useRoute} from 'vue-router';
import {register} from 'vue-advanced-chat';
import {PhArrowClockwise,PhArrowLeft,PhChatCircle,PhPlus} from '@phosphor-icons/vue';
import {useDesk} from '../../admin';
import {locale,say} from '../../state';
import {messageCopy as copy,type CustomerMessage,type MessageBridge,type MessagePage,type MessageThread,type ThreadPage} from '../../messaging';
import SlideOver from '../SlideOver.vue';

register();
const props=defineProps<{active:boolean}>();
const {request}=useDesk();
const route=useRoute();
const threads=ref<MessageThread[]>([]),messages=ref<CustomerMessage[]>([]),bridge=ref<MessageBridge|null>(null);
const selectedId=ref(''),selected=ref<MessageThread|null>(null),query=ref(''),unreadOnly=ref(false);
const error=ref(''),busy=ref(false),loading=ref(false),sending=ref(false),newOpen=ref(false);
const roomCursor=ref(''),before=ref<number|null>(null),messagesDone=ref(true);
const form=reactive({phone:'',name:'',reservation_id:''});
const drafts=reactive<Record<string,string>>({}),pending=new Map<string,{id:string;content:string}>();
const draft=computed({get:()=>drafts[selectedId.value]||'',set:(value:string)=>{drafts[selectedId.value]=value;}});
const ready=computed(()=>!!bridge.value?.enabled&&!!bridge.value?.send_enabled);
const room=computed(()=>selected.value?[{roomId:selected.value.id,roomName:selected.value.name||selected.value.phone,users:[{_id:'owner',username:say(copy.desk_source)},{_id:'customer',username:selected.value.name||selected.value.phone}]}]:[]);
const stateLabel=(state:string)=>say((copy as Record<string,string[]>)[state]||copy.unknown);
const dateText=(stamp:number)=>new Intl.DateTimeFormat(locale.value==='zh'?'zh-CN':'en-CA',{timeZone:'America/Toronto',month:'short',day:'numeric'}).format(stamp*1000);
const timeText=(stamp:number)=>new Intl.DateTimeFormat(locale.value==='zh'?'zh-CN':'en-CA',{timeZone:'America/Toronto',hour:'2-digit',minute:'2-digit',hour12:false}).format(stamp*1000);
const chatMessages=computed(()=>messages.value.map(m=>({_id:m.id,indexId:m.seq,content:m.content,senderId:m.direction==='outbound'?'owner':'customer',username:[m.channel,say(m.source==='desk'?copy.desk_source:copy.phone_source),m.direction==='outbound'?stateLabel(m.state):''].filter(Boolean).join(' · '),date:dateText(m.created_at),timestamp:timeText(m.created_at),saved:['sent','delivered'].includes(m.state),distributed:m.state==='delivered',seen:false,disableActions:true,disableReactions:true})));
const textMessages=computed(()=>({ROOMS_EMPTY:say(copy.empty),ROOM_EMPTY:say(copy.no_messages),NEW_MESSAGES:say(copy.new_messages),MESSAGE_DELETED:'',MESSAGES_EMPTY:say(copy.no_messages),CONVERSATION_STARTED:'',TYPE_MESSAGE:say(copy.write),SEARCH:say(copy.search),IS_ONLINE:say(copy.online),LAST_SEEN:'',IS_TYPING:'',CANCEL_SELECT_MESSAGE:say(copy.cancel)}));
const chatStyles={general:{background:'#ffffff',color:'#29343a',borderStyle:'none'},container:{borderRadius:'0',boxShadow:'none'},content:{background:'#ffffff'},message:{background:'#f1f5f7',backgroundMe:'#e8f2f8',color:'#29343a',colorMe:'#29343a'}};
let interval:ReturnType<typeof setInterval>|undefined,searchTimer:ReturnType<typeof setTimeout>|undefined,active=true,listSequence=0,messageSequence=0,loadedThread='',listBusy=false,messageBusy=false;
function messageError(e:unknown){const code=(e as {code?:string;message?:string}).code||(e as Error).message;return say((copy as Record<string,string[]>)[code]||copy.generic_error);}
function shown(){return active&&props.active&&document.visibilityState==='visible';}
async function loadThreads(append=false){
  if(listBusy)return;listBusy=true;const sequence=++listSequence;
  try{
    const params=new URLSearchParams({query:query.value,unread:String(unreadOnly.value)});
    if(append&&roomCursor.value)params.set('cursor',roomCursor.value);
    const result=await request<ThreadPage>('/manage/messages/threads?'+params);
    if(sequence!==listSequence)return;
    const merged=append?[...threads.value,...result.items]:result.items;
    threads.value=[...new Map(merged.map(t=>[t.id,t])).values()];roomCursor.value=result.next_cursor;bridge.value=result.bridge;
  }catch(e){error.value=messageError(e);}finally{listBusy=false;}
}
async function loadMessages(older=false){
  const ident=selectedId.value;if(!ident||messageBusy||(older&&!before.value))return;
  messageBusy=true;const sequence=++messageSequence;
  try{
    const result=await request<MessagePage>(`/manage/messages/threads/${ident}${older?'?before='+before.value:''}`);
    if(sequence!==messageSequence||ident!==selectedId.value)return;
    selected.value=result.thread;loadedThread=ident;
    messages.value=[...new Map([...messages.value,...result.items].map(m=>[m.id,m])).values()].sort((a,b)=>a.seq-b.seq);
    if(older||before.value===null){before.value=result.next_before;messagesDone.value=!result.has_more;}
    await nextTick();
    if(shown()&&ident===selectedId.value&&result.items.length){
      const seq=Math.max(...result.items.map(m=>m.seq));
      await request(`/manage/messages/threads/${ident}/read`,{method:'POST',body:JSON.stringify({through_seq:seq})});
      const found=threads.value.find(t=>t.id===ident);if(found)found.unread=0;
    }
  }catch(e){if(sequence===messageSequence)error.value=messageError(e);}finally{if(sequence===messageSequence)messageBusy=false;}
}
async function selectThread(value:MessageThread){
  if(selectedId.value===value.id)return;
  ++messageSequence;selectedId.value=value.id;selected.value=value;messages.value=[];before.value=null;messagesDone.value=true;loadedThread='';messageBusy=false;error.value='';
  await loadMessages();
}
function fetchOlder(event:Event){const raw=(event as CustomEvent).detail,data=Array.isArray(raw)?raw[0]:raw;if(data?.options?.reset){if(loadedThread!==selectedId.value)void loadMessages();}else void loadMessages(true);}
async function send(){
  const ident=selectedId.value,content=draft.value.trim();if(!ident||!content||sending.value||!ready.value)return;
  if(content.length>2000){error.value=messageError({message:'sms_content_invalid'});return;}
  const previous=pending.get(ident);const attempt=previous?.content===content?previous:{id:crypto.randomUUID(),content};pending.set(ident,attempt);
  sending.value=true;error.value='';
  try{
    const message=await request<CustomerMessage>(`/manage/messages/threads/${ident}/messages`,{method:'POST',body:JSON.stringify({request_id:attempt.id,content})});
    if(selectedId.value===ident)messages.value=[...new Map([...messages.value,message].map(m=>[m.id,m])).values()].sort((a,b)=>a.seq-b.seq);
    if(drafts[ident]?.trim()===content)drafts[ident]='';pending.delete(ident);await loadThreads();
  }catch(e){error.value=(e as {status?:number}).status?messageError(e):say(copy.send_uncertain);}
  finally{sending.value=false;}
}
async function create(){
  busy.value=true;error.value='';
  try{const value=await request<MessageThread>('/manage/messages/threads',{method:'POST',body:JSON.stringify(form)});newOpen.value=false;await loadThreads();await selectThread(value);Object.assign(form,{phone:'',name:'',reservation_id:''});}
  catch(e){error.value=messageError(e);}finally{busy.value=false;}
}
async function setHandled(){if(!selected.value)return;try{const status=selected.value.status==='open'?'closed':'open';await request(`/manage/messages/threads/${selectedId.value}`,{method:'PATCH',body:JSON.stringify({status})});selected.value.status=status;await loadThreads();}catch(e){error.value=messageError(e);}}
async function refresh(){loading.value=true;try{await loadThreads();await loadMessages();}finally{loading.value=false;}}
function changed(){if(searchTimer)clearTimeout(searchTimer);searchTimer=setTimeout(()=>void loadThreads(),250);}
watch([query,unreadOnly],changed);
function visibility(){if(shown())void refresh();}
onMounted(async()=>{
  await refresh();
  interval=setInterval(()=>{if(shown())void refresh();},7000);document.addEventListener('visibilitychange',visibility);
});
let openedReservation='';
watch(()=>[props.active,route.query.reservation],async()=>{
  const ident=route.query.reservation;if(!props.active||typeof ident!=='string'||ident===openedReservation)return;
  openedReservation=ident;form.reservation_id=ident;
  try{const value=await request<MessageThread>('/manage/messages/threads',{method:'POST',body:JSON.stringify({reservation_id:ident})});await loadThreads();await selectThread(value);}
  catch(e){if((e as {status?:number}).status===422){newOpen.value=true;}else error.value=messageError(e);}
},{immediate:true});
onActivated(()=>{active=true;void refresh();});onDeactivated(()=>{active=false;});
onBeforeUnmount(()=>{active=false;++listSequence;++messageSequence;clearInterval(interval);clearTimeout(searchTimer);document.removeEventListener('visibilitychange',visibility);});
defineExpose({refresh});
</script>

<template>
  <section class="sms-workspace" :class="{'sms-has-selection':selectedId}">
    <header class="sms-heading"><div><h1>{{say(copy.title)}}</h1><p>{{say(copy.subtitle)}}</p></div><div class="sms-heading-actions"><button class="desk-link" :disabled="loading" @click="refresh"><PhArrowClockwise :class="{spinning:loading}"/>{{say(copy.refresh)}}</button><button class="desk-button" @click="newOpen=true"><PhPlus/>{{say(copy.new_conversation)}}</button></div></header>
    <p class="sms-connection" :class="{'is-ready':ready&&bridge?.online&&!bridge?.health.error}">{{!ready?say(copy.not_ready):bridge?.health.error?say((copy as Record<string,string[]>)[String(bridge.health.error)]||copy.account_unavailable):bridge?.online?say(copy.online):say(copy.offline)}}<span v-if="bridge"> · {{bridge.sender}}</span></p>
    <p v-if="error" class="desk-error" role="alert">{{error}}</p>
    <div class="sms-inbox">
      <aside class="sms-threads" :aria-label="say(copy.title)">
        <input v-model="query" type="search" :placeholder="say(copy.search)" :aria-label="say(copy.search)"/>
        <div class="sms-filters"><button :class="{active:!unreadOnly}" @click="unreadOnly=false">{{say(copy.all)}}</button><button :class="{active:unreadOnly}" @click="unreadOnly=true">{{say(copy.unread)}}</button></div>
        <div class="sms-thread-scroll"><p v-if="!threads.length" class="sms-empty">{{say(copy.empty)}}</p><button v-for="item in threads" :key="item.id" class="sms-thread" :class="{selected:item.id===selectedId}" @click="selectThread(item)"><span class="sms-thread-name">{{item.name||item.phone}}<b v-if="item.unread" class="sms-unread">{{item.unread}}</b></span><small>{{item.phone}}</small><span class="sms-preview">{{item.latest?.content||say(copy.no_messages)}}</span></button><button v-if="roomCursor" class="desk-link sms-more" @click="loadThreads(true)">{{say(copy.more_customers)}}</button></div>
      </aside>
      <div class="sms-conversation">
        <template v-if="selected">
          <header class="sms-room-heading"><button class="sms-mobile-back desk-link" :aria-label="say(copy.all)" @click="selectedId='';selected=null"><PhArrowLeft/></button><div><strong>{{selected.name||selected.phone}}</strong><small>{{selected.phone}}</small></div><button class="desk-link" @click="setHandled">{{say(selected.status==='open'?copy.close:copy.reopen)}}</button></header>
          <details v-if="selected.reservations.length" class="sms-reservations"><summary>{{say(copy.reservation)}} · {{selected.reservations.length}}</summary><div v-for="booking in selected.reservations" :key="booking.id"><strong>{{booking.name}}</strong><span>{{booking.booking.date}} · {{booking.booking.start}}–{{booking.booking.end}} · {{booking.booking.guests}}</span><RouterLink :to="{path:'/manage',query:{view:'reservations',booking:booking.id}}">{{booking.id}}</RouterLink></div></details>
          <div class="sms-chat-body"><vue-advanced-chat height="100%" current-user-id="owner" :rooms="JSON.stringify(room)" :room-id="selectedId" :messages="JSON.stringify(chatMessages)" :rooms-loaded="true" :messages-loaded="messagesDone" :single-room="true" :show-header="false" :show-footer="false" :show-files="false" :show-audio="false" :show-emojis="false" :show-reaction-emojis="false" :message-actions="'[]'" :message-selection-actions="'[]'" :menu-actions="'[]'" :username-options="JSON.stringify({minUsers:0,currentUser:true})" :text-formatting="JSON.stringify({disabled:true})" :link-options="JSON.stringify({disabled:true})" :styles="JSON.stringify(chatStyles)" :text-messages="JSON.stringify(textMessages)" @fetch-messages="fetchOlder"/></div>
          <form class="sms-composer" @submit.prevent="send"><label class="sr-only" for="sms-draft">{{say(copy.write)}}</label><textarea :title="say(copy.channel_hint)" id="sms-draft" v-model="draft" rows="2" maxlength="2000" :placeholder="say(copy.write)" :disabled="sending"/><button class="desk-button" type="submit" :disabled="!ready||sending||!draft.trim()">{{say(sending?copy.sending:copy.send)}}</button></form>
        </template>
        <div v-else class="sms-empty sms-welcome"><PhChatCircle :size="34"/><p>{{say(copy.select_conversation)}}</p></div>
      </div>
    </div>
    <SlideOver v-model="newOpen" :title="say(copy.new_conversation)" :busy="busy"><form class="sms-create" @submit.prevent="create"><label>{{say(copy.name)}}<input v-model="form.name" maxlength="80" autocomplete="name"/></label><label>{{say(copy.phone)}}<input v-model="form.phone" type="tel" maxlength="40" autocomplete="tel" :required="!form.reservation_id"/></label><p>{{say(copy.number_hint)}}</p><label>{{say(copy.reservation)}}<input v-model="form.reservation_id" maxlength="64"/></label><p>{{say(copy.sync_hint)}}</p><p v-if="error" class="desk-error" role="alert">{{error}}</p><button class="desk-button" type="submit" :disabled="busy">{{say(copy.connect)}}</button></form></SlideOver>
  </section>
</template>

<style scoped>
.sms-workspace{min-width:0}.sms-heading{display:flex;align-items:center;justify-content:space-between;gap:18px;margin:12px 0}.sms-heading h1{font-size:clamp(24px,2.4vw,34px);margin:0}.sms-heading p,.sms-connection{font-size:13px;color:#737f85;margin:6px 0}.sms-heading-actions{display:flex;gap:14px;align-items:center}.sms-heading-actions button{display:inline-flex;align-items:center;gap:6px}.sms-connection.is-ready{color:#4d7660}.sms-inbox{display:grid;grid-template-columns:minmax(220px,29%) minmax(0,1fr);height:clamp(370px,calc(var(--visual-viewport-height,100dvh) - 270px),860px);background:#fff;border:1px solid #dce5e9;border-radius:16px;overflow:hidden;margin-top:14px}.sms-threads{display:flex;flex-direction:column;min-height:0;padding:14px 0 0;border-right:1px solid #e2e8eb}.sms-threads>input{margin:0 12px;width:calc(100% - 24px);font-size:16px;min-height:42px;border:1px solid #dce5e9;border-radius:9px;padding:8px}.sms-filters{display:flex;gap:6px;padding:10px 12px}.sms-filters button{background:transparent;border:0;padding:7px 12px;border-radius:18px;cursor:pointer}.sms-filters .active{background:#eaf3f8}.sms-thread-scroll{overflow:auto;min-height:0;overscroll-behavior:contain}.sms-thread{display:flex;flex-direction:column;gap:5px;text-align:left;width:100%;border:0;border-top:1px solid #edf0f2;background:#fff;padding:16px;cursor:pointer;min-height:95px}.sms-thread.selected{background:#edf5fa}.sms-thread-name{display:flex;align-items:center;justify-content:space-between;gap:6px;font-weight:600}.sms-thread small{color:#7b858a}.sms-preview{color:#7b858a;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}.sms-unread{background:#7294aa;color:white;border-radius:15px;min-width:21px;text-align:center;font-size:11px;padding:2px 5px}.sms-conversation{display:flex;min-width:0;min-height:0;flex-direction:column}.sms-room-heading{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:13px 18px;border-bottom:1px solid #e6ecef;flex-shrink:0}.sms-room-heading small{display:block;color:#7b858a;margin-top:4px}.sms-chat-body{flex:1;min-height:0;overflow:hidden}.sms-chat-body vue-advanced-chat{display:block;height:100%}.sms-composer{display:flex;align-items:flex-end;gap:10px;border-top:1px solid #e2e8eb;padding:12px 16px max(12px,env(safe-area-inset-bottom));flex-shrink:0}.sms-composer textarea{flex:1;min-width:0;resize:vertical;max-height:150px;border:1px solid #dce5e9;border-radius:9px;padding:10px;line-height:1.5;font:inherit;font-size:16px}.sms-composer button{white-space:nowrap;min-height:44px}.sms-empty{padding:25px 18px;color:#829098;text-align:center}.sms-welcome{margin:auto}.sms-create{display:grid;gap:18px}.sms-create label{display:grid;gap:8px}.sms-create input{padding:12px;border:1px solid #dce5e9;border-radius:9px;font-size:16px;min-width:0;width:100%}.sms-create p{font-size:13px;color:#78858c;margin:0}.sms-reservations{padding:8px 18px;background:#f8fafb;font-size:12px;flex-shrink:0;max-height:160px;overflow:auto}.sms-reservations summary{cursor:pointer;padding:4px 0}.sms-reservations>div{display:flex;gap:10px;flex-wrap:wrap;padding:8px 0;border-top:1px solid #e7ecef}.sms-more{margin:12px}.sms-mobile-back{display:none}
@media(max-width:700px){.sms-heading{align-items:flex-start}.sms-heading-actions{gap:10px;flex-wrap:wrap;justify-content:flex-end}.sms-heading-actions .desk-button{padding:10px}.sms-heading p{display:none}.sms-inbox{grid-template-columns:1fr;height:calc(var(--visual-viewport-height,100dvh) - 215px);min-height:280px;border-radius:12px}.sms-threads{border-right:0}.sms-conversation{display:none}.sms-has-selection .sms-threads{display:none}.sms-has-selection .sms-conversation{display:flex}.sms-mobile-back{display:inline-flex}.sms-room-heading{padding:12px}.sms-composer{padding-left:10px;padding-right:10px;gap:8px}.sms-composer .desk-button{padding:10px}.sms-room-heading>.desk-link:last-child{font-size:12px}.sms-connection{font-size:11px}}
@media(max-height:540px){.sms-inbox{height:calc(var(--visual-viewport-height,100dvh) - 130px);min-height:230px}.sms-heading{margin:4px 0}.sms-heading h1{font-size:22px}.sms-heading p{display:none}.sms-composer textarea{max-height:85px}.sms-room-heading{padding-top:7px;padding-bottom:7px}}

:global(html .desk-main:has(.sms-workspace)){height:var(--visible-height);display:flex;flex-direction:column;min-height:0}
:global(html .desk-main:has(.sms-workspace) .desk-topbar){flex-shrink:0}
:global(html .desk-main:has(.sms-workspace)>.desk-content){display:flex;flex-direction:column;flex:1;min-height:0;margin-block:0;padding-top:14px;padding-bottom:max(14px,var(--safe-bottom))}
.sms-workspace{display:flex;flex-direction:column;flex:1;min-height:0}.sms-inbox{height:auto;flex:1;min-height:180px}.sms-heading,.sms-connection,.sms-workspace>.desk-error{flex-shrink:0}.sms-workspace>.desk-error{max-height:64px;overflow:auto;margin-block:8px}.sms-room-heading strong{overflow-wrap:anywhere}.sms-room-heading>div{min-width:0}
@media(max-width:600px){.sms-heading h1{font-size:23px}.sms-heading{gap:8px}.sms-heading-actions{gap:8px}.sms-heading p{display:none}.sms-room-heading{padding:10px}.sms-composer{padding:10px}.sms-composer textarea{max-height:90px}}
@media(max-height:500px){.sms-heading{margin:3px 0}.sms-heading h1{font-size:21px}.sms-heading p,.sms-connection{display:none}.sms-inbox{min-height:155px;margin-top:6px}.sms-workspace>.desk-error{max-height:42px;font-size:12px;padding:8px}.sms-room-heading{padding:6px 10px}.sms-composer{padding:6px 10px}.sms-composer textarea{height:42px;min-height:42px;max-height:70px}:global(html .desk-main:has(.sms-workspace)>.desk-content){padding-top:8px;padding-bottom:8px}}
</style>
