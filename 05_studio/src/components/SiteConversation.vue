<script setup lang="ts">
import {computed,inject,nextTick,onBeforeUnmount,onMounted,ref,watch} from 'vue';
import {commerceApi} from '../commerce';
import {deskKey} from '../admin';
import {accountUser} from '../account';
import {say,locale} from '../state';
import copy from '../content/customer-notifications.json';
const props=withDefaults(defineProps<{staffId?:string;reservationId?:string}>(),{staffId:'',reservationId:''});
const desk=inject(deskKey,undefined);const items=ref<any[]>([]),draft=ref(''),error=ref(''),busy=ref(false),hasOlder=ref(false),body=ref<HTMLElement>();
let alive=true,loading=false,timer:ReturnType<typeof setInterval>,key='',sentBody='',generation=0;
const endpoint=computed(()=>props.staffId?'/manage/site-messages/'+props.staffId:'/auth/messages');
const call=<T,>(path:string,options?:RequestInit)=>props.staffId&&desk?desk.request<T>(path,options):commerceApi<T>(path,options);
const fail=(e:any)=>say((copy as Record<string,string[]>)[e?.code]||copy.generic_error);
const mine=(row:any)=>row.sender_role===(props.staffId?'staff':'customer');
async function load(older=false){if(loading||!alive)return;loading=true;const version=generation;
 const previous=body.value?.scrollHeight||0,near=!body.value||body.value.scrollHeight-body.value.clientHeight-body.value.scrollTop<70;
 try{const suffix=older&&items.value.length?'?before='+items.value[0].seq:items.value.length?'?after='+items.value[items.value.length-1].seq:'';
 const result=await call<any>(endpoint.value+suffix);if(!alive||version!==generation)return;
 const rows=[...(older?result.items:items.value),...(older?items.value:result.items)];items.value=[...new Map(rows.map(r=>[r.id,r])).values()].sort((a,b)=>a.seq-b.seq);if(older||suffix==='')hasOlder.value=result.has_older;
 await nextTick();if(body.value){if(older)body.value.scrollTop+=body.value.scrollHeight-previous;else if(near)body.value.scrollTop=body.value.scrollHeight;}
 if(!document.hidden&&near&&!older&&items.value.length)void call(endpoint.value+'/read',{method:'POST',body:JSON.stringify({seq:items.value[items.value.length-1].seq})}).catch(()=>{});
 }catch(e){if(version===generation)error.value=fail(e);}finally{loading=false;}}
async function send(){const content=draft.value.trim();if(!content||busy.value)return;busy.value=true;error.value='';if(content!==sentBody){key=crypto.randomUUID();sentBody=content;}
 try{await call(endpoint.value,{method:'POST',body:JSON.stringify({content,request_id:key,reservation_id:props.reservationId})});draft.value='';key='';sentBody='';await load();await nextTick();if(body.value)body.value.scrollTop=body.value.scrollHeight;}catch(e){error.value=fail(e);}finally{busy.value=false;}}
watch([()=>props.staffId,()=>accountUser.value?.id],()=>{generation++;items.value=[];draft.value='';key='';error.value='';void load();});
onMounted(()=>{void load();timer=setInterval(()=>void load(),2000);});onBeforeUnmount(()=>{alive=false;generation++;clearInterval(timer);});
</script>
<template><section class="site-conversation"><p v-if="error" class="form-error" role="alert">{{error}} <button class="text-link" @click="load()">{{say(copy.refresh)}}</button></p><div ref="body" class="site-conversation-body" role="log"><button v-if="hasOlder" class="text-link" @click="load(true)">{{say(copy.more)}}</button><p v-if="!items.length" class="site-chat-empty">{{say(copy.empty)}}</p><article v-for="row in items" :key="row.id" :class="['site-chat-message',{mine:mine(row),system:row.sender_role==='system'}]"><small>{{say(row.sender_role==='system'?copy.system:mine(row)?copy.you:staffId?copy.customer:copy.host)}} · {{new Date(row.created_at*1000).toLocaleString(locale==='zh'?'zh-CN':'en-CA',{timeZone:'America/Toronto'})}}</small><p>{{row.body}}</p><RouterLink v-if="row.reservation_id&&!staffId" :to="'/reservation/'+row.reservation_id">{{say(copy.view_booking)}}</RouterLink></article></div><form class="site-chat-composer" @submit.prevent="send"><textarea v-model="draft" :aria-label="say(copy.reply)" :placeholder="say(copy.reply)" maxlength="4000" rows="2"/><button class="desk-button" :disabled="busy||!draft.trim()">{{say(busy?copy.sending:copy.send)}}</button></form></section></template>
<style scoped>.site-conversation{display:flex;flex-direction:column;border:1px solid #dce5ea;border-radius:14px;overflow:hidden;background:#fff;min-width:0}.site-conversation>.form-error{padding:10px 14px;margin:0}.site-conversation-body{height:clamp(230px,45dvh,600px);overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px}.site-chat-message{max-width:88%;align-self:flex-start;border-radius:12px;background:#f0f5f8;padding:12px 14px;overflow-wrap:anywhere}.site-chat-message.mine{align-self:flex-end;background:#e6f1f7}.site-chat-message.system{align-self:stretch;max-width:none;background:#faf9f4}.site-chat-message small{color:#85939b;font-size:11px}.site-chat-message p{white-space:pre-wrap;margin:7px 0 0;font-size:14px;line-height:1.65}.site-chat-message a{font-size:13px;display:inline-block;margin-top:8px}.site-chat-composer{display:flex;gap:10px;padding:12px;border-top:1px solid #dce5ea;align-items:flex-end}.site-chat-composer textarea{resize:none;min-width:0;flex:1;box-sizing:border-box;font-size:16px;padding:10px;border:1px solid #dce5ea;border-radius:9px}.site-chat-composer button{flex-shrink:0;min-height:44px}.site-chat-empty{color:#84929b;font-size:14px;text-align:center;margin:auto}@media(max-height:500px){.site-conversation-body{height:220px}}@media(prefers-reduced-motion:no-preference){.site-chat-message{animation:site-message-in .3s ease-out}@keyframes site-message-in{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}}</style>
