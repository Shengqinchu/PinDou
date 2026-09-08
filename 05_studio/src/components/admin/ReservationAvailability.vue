<script setup lang="ts">
import { contentModule } from "../../content-store";
const copyText = contentModule("components-admin-ReservationAvailability", copyTextDefault);

import copyTextDefault from "../../content/components-admin-ReservationAvailability.json";
import { say,hamiltonDate,prettyDate } from "../../state";
import { ref,watch } from "vue";
import { useDesk } from "../../admin";
import { PhPlus,PhArrowClockwise } from "@phosphor-icons/vue";
const props=defineProps<{active:boolean}>();const {request}=useDesk();
type Block={id:string;date:string;start:string;end:string;note:string;version:number};
const items=ref<Block[]>([]),date=ref(hamiltonDate()),start=ref('14:00'),end=ref('16:00'),note=ref(''),busy=ref(false),error=ref(''),success=ref('');
const times=Array.from({length:48},(_,i)=>`${String(Math.floor(i/2)).padStart(2,'0')}:${i%2?'30':'00'}`);
async function load(){busy.value=true;error.value='';try{items.value=(await request<{items:Block[]}>('/manage/reservation-blocks')).items;}catch(e){error.value=(e as Error).message;}finally{busy.value=false;}}
async function block(){if(busy.value)return;busy.value=true;error.value='';success.value='';try{await request('/manage/reservation-blocks',{method:'POST',body:JSON.stringify({date:date.value,start:start.value,end:end.value,note:note.value})});note.value='';success.value=say(copyText.saved);await load();}catch(e){error.value=(e as Error).message;}finally{busy.value=false;}}
async function remove(item:Block){if(busy.value)return;busy.value=true;error.value='';try{await request(`/manage/reservation-blocks/${item.id}?version=${item.version}`,{method:'DELETE'});await load();}catch(e){error.value=(e as Error).message;}finally{busy.value=false;}}
watch(()=>props.active,v=>{if(v)void load();},{immediate:true});
</script>
<template>
  <section class="availability-editor"><header class="desk-section-heading"><div><h2>{{say(copyText.title)}}</h2><p>{{say(copyText.intro)}}</p></div><button class="desk-icon-button" :disabled="busy" :aria-label="say(copyText.refresh)" @click="load"><PhArrowClockwise/></button></header>
    <form class="availability-form" @submit.prevent="block"><label class="field"><span>{{say(copyText.date)}}</span><input v-model="date" type="date" :min="hamiltonDate()" required/></label><label class="field"><span>{{say(copyText.start)}}</span><select v-model="start"><option v-for="t in times" :key="t">{{t}}</option></select></label><label class="field"><span>{{say(copyText.end)}}</span><select v-model="end"><option v-for="t in times.filter(t=>t>start)" :key="t">{{t}}</option></select></label><label class="field availability-owner-note"><span>{{say(copyText.note)}}</span><input v-model="note" maxlength="200" /></label><button class="desk-button primary" :disabled="busy||end<=start"><PhPlus/>{{say(copyText.block)}}</button></form>
    <p v-if="error" class="desk-error" role="alert">{{error}}</p><p v-if="success" class="editor-state" role="status">{{success}}</p>
    <div v-for="item in items" :key="item.id" class="availability-row"><div><strong>{{prettyDate(item.date)}}</strong><span>{{item.start}}–{{item.end}}</span><small v-if="item.note">{{item.note}}</small></div><button class="desk-button secondary" :disabled="busy" @click="remove(item)">{{say(copyText.restore)}}</button></div><p v-if="!items.length&&!busy" class="form-help">{{say(copyText.empty)}}</p>
  </section>
</template>
