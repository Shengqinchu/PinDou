<script setup lang="ts">
import { contentModule } from "../../content-store";
const copyText = contentModule("components-admin-ReservationAvailability", copyTextDefault);

import copyTextDefault from "../../content/components-admin-ReservationAvailability.json";
import { say } from "../../state";
import { ref,onMounted,onBeforeUnmount } from "vue";
import { PhBell } from "@phosphor-icons/vue";
import { useDesk } from "../../admin";
import { notify } from "../../ui";
const {request}=useDesk();const pending=ref(0),permission=ref(typeof Notification==='undefined'?'unsupported':Notification.permission),message=ref('');
let cursor:number|undefined,timer:ReturnType<typeof setInterval>,inflight=false;
async function check(){if(inflight)return;inflight=true;try{const result=await request<{cursor:number;new_count:number;pending:number}>(`/manage/reservation-notifications?after=${cursor||0}`);pending.value=result.pending;if(cursor!==undefined&&result.new_count){notify(say(copyText.new),say(copyText.new));if(typeof Notification!=='undefined'&&Notification.permission==='granted'){try{const notification=new Notification(say(copyText.notification),{body:say(copyText.new),tag:'puppy-reservations',icon:'/studio-brand/puppy-v3.jpg'});notification.onclick=()=>{window.focus();notification.close();};}catch{}}}cursor=result.cursor;}catch{}finally{inflight=false;}}
async function enable(){if(typeof Notification==='undefined'){message.value=say(copyText.unsupported);return;}try{permission.value=await Notification.requestPermission();message.value=say(permission.value==='granted'?copyText.enabled:copyText.denied);}catch{message.value=say(copyText.unsupported);}}
onMounted(()=>{void check();timer=setInterval(check,20000);});onBeforeUnmount(()=>clearInterval(timer));
</script>
<template><div class="desk-notifications"><PhBell/><span>{{say(copyText.pending)}} {{pending}}</span><button v-if="permission!=='granted'" class="desk-link" @click="enable">{{say(copyText.enable)}}</button><small>{{message||say(copyText.noteNotification)}}</small></div></template>
