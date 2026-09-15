<script setup lang="ts">
import {onBeforeUnmount,ref,watch} from 'vue';
import {PhArrowClockwise} from '@phosphor-icons/vue';
import {useDesk} from '../../admin';
import {say,formatCopy} from '../../state';
import {contentModule} from '../../content-store';
import defaults from '../../content/owner-delivery.json';
const copy=contentModule('owner-delivery',defaults) as Record<string,string[]>;
type Channel={enabled:boolean;configured?:boolean;ready?:boolean;online?:boolean;limited?:boolean;authorized?:boolean;bound?:boolean;used?:number;limit?:number};
type Delivery={level:'ready'|'warning'|'critical';continuous_ready:boolean;unacknowledged_count:number;unacknowledged_ids:string[];channels:Record<string,Channel>};
const props=defineProps<{active:boolean}>();
const {request}=useDesk();
const data=ref<Delivery>(),busy=ref(false),failed=ref(false);
let alive=true,timer:ReturnType<typeof setInterval>|undefined;
async function load(){
  if(busy.value||!props.active)return;
  busy.value=true;
  try{const value=await request<Delivery>('/manage/owner-delivery');if(alive){data.value=value;failed.value=false;}}
  catch{if(alive)failed.value=true;}
  finally{busy.value=false;}
}
function state(name:string,channel:Channel){
  if(!channel.enabled)return 'disabled';
  if(name==='wechat')return !channel.bound?'not_configured':channel.authorized?'authorized':'authorization_needed';
  if(!channel.configured)return 'not_configured';
  if(channel.ready)return 'online';
  return name==='sms'?'offline':channel.limited?'limited':'blocked';
}
watch(()=>props.active,active=>{clearInterval(timer);if(active){void load();timer=setInterval(()=>{if(!document.hidden)void load();},15000);}},{immediate:true});
onBeforeUnmount(()=>{alive=false;clearInterval(timer);});
</script>
<template>
  <aside class="owner-delivery" :data-level="failed?'critical':data?.level" :aria-label="say(copy.title)">
    <div class="owner-delivery-heading"><strong>{{say(copy.title)}}</strong><button type="button" class="icon-button" :disabled="busy" :aria-label="say(copy.refresh)" @click="load"><PhArrowClockwise/></button></div>
    <p v-if="failed" role="alert">{{say(copy.unavailable)}}</p>
    <p v-else-if="!data" role="status">{{say(copy.loading)}}</p>
    <template v-else>
      <p :role="data.level==='critical'?'alert':'status'"><strong>{{say(copy[data.level])}}</strong> · {{say(data.continuous_ready?copy.continuous:copy.no_route)}}</p>
      <p v-if="data.unacknowledged_count" role="alert">{{formatCopy(copy.unacknowledged,{v0:data.unacknowledged_count})}}</p>
      <details><summary>{{say(copy.details)}}</summary>
        <dl><div v-for="(channel,name) in data.channels" :key="name"><dt>{{say(copy[name])}}</dt><dd>{{say(copy[state(name,channel)])}}</dd></div></dl>
        <p>{{formatCopy(copy.usage,{v0:data.channels.serverchan.used,v1:data.channels.serverchan.limit})}}</p>
        <p v-if="data.unacknowledged_ids.length" class="owner-delivery-ids">{{data.unacknowledged_ids.join(' · ')}}</p>
        <p>{{say(copy.receipt)}}</p>
      </details>
    </template>
  </aside>
</template>
<style scoped>
.owner-delivery{margin-block:0 24px;padding:16px 20px;border:1px solid #d8e4df;border-radius:16px;background:#f7faf8;font-size:13px;line-height:1.7;overflow-wrap:anywhere}.owner-delivery[data-level=warning]{border-color:#e2d6b6;background:#fdfaf2}.owner-delivery[data-level=critical]{border-color:#e1c7c7;background:#fff7f7}.owner-delivery-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.owner-delivery-heading strong{font-size:15px}.owner-delivery-heading button{flex:none;min-width:44px;min-height:44px}.owner-delivery p{margin:8px 0}.owner-delivery summary{cursor:pointer;min-height:44px;display:list-item;align-content:center}.owner-delivery dl{margin:8px 0}.owner-delivery dl>div{display:grid;grid-template-columns:minmax(150px,1fr) minmax(0,2fr);gap:12px;padding:7px 0;border-bottom:1px solid #e2e5e4}.owner-delivery dd{margin:0}.owner-delivery-ids{font-size:12px}@media(max-width:600px){.owner-delivery{padding:12px 14px}.owner-delivery dl>div{grid-template-columns:1fr;gap:2px}}
</style>
