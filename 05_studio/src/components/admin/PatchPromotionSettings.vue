<script setup lang="ts">
import { ref,watch,onBeforeUnmount } from 'vue';
import { PhGift,PhPencilSimple,PhCheck } from '@phosphor-icons/vue';
import { useDesk } from '../../admin';
import { promotionCopy as copy,type ManagedPromotion } from '../../patch-promotion';
import { say,formatCopy } from '../../state';
import { notify } from '../../ui';
import SlideOver from '../SlideOver.vue';
import InfoTip from '../InfoTip.vue';
import ToggleSwitch from '../ToggleSwitch.vue';
const props=defineProps<{active:boolean;refreshKey:number}>();
const {request}=useDesk(),promotion=ref<ManagedPromotion>(),open=ref(false),busy=ref(false),loading=ref(false),error=ref(''),saveError=ref('');
const quota=ref<number|string>(10),remaining=ref<number|string>(10),remainingEdited=ref(false),enabled=ref(true),version=ref(0);let seq=0;
async function load(){const n=++seq;loading.value=true;error.value='';try{const data=await request<ManagedPromotion>('/manage/patch-promotion');if(n===seq)promotion.value=data;}catch(e){if(n===seq)error.value=(e as Error).message;}finally{if(n===seq)loading.value=false;}}
function edit(){if(!promotion.value)return;quota.value=promotion.value.quota;remaining.value=promotion.value.remaining;remainingEdited.value=false;enabled.value=promotion.value.enabled;version.value=promotion.value.version;saveError.value='';open.value=true;}
watch(quota,()=>{if(!remainingEdited.value&&promotion.value&&Number.isInteger(quota.value))remaining.value=Math.max(0,Number(quota.value)-promotion.value.allocated+(promotion.value.remaining_adjustment??0));});
async function save(){
 if(busy.value||[quota.value,remaining.value].some(v=>!Number.isInteger(v)||Number(v)<0||Number(v)>100000))return;
 busy.value=true;saveError.value='';
 try{promotion.value=await request<ManagedPromotion>('/manage/patch-promotion',{method:'PUT',body:JSON.stringify({quota:quota.value,...(remainingEdited.value?{remaining:remaining.value}:{}),enabled:enabled.value,version:version.value})});open.value=false;notify(copy.saved[0],copy.saved[1]);}
 catch(e){saveError.value=(e as Error).message;}
 finally{busy.value=false;}
}
async function reloadEdit(){await load();if(!error.value)edit();}
watch(()=>[props.active,props.refreshKey],()=>{if(props.active)void load();},{immediate:true});
onBeforeUnmount(()=>seq++);
</script>
<template>
 <section class="patch-promotion-settings">
  <div class="patch-promotion-heading"><PhGift :size="23"/><div><h2>{{say(copy.desk_title)}}</h2><p v-if="promotion"><span v-if="!promotion.enabled">{{say(copy.paused)}} · </span>{{formatCopy(copy.remaining,{v0:promotion.remaining,v1:promotion.quota})}} · {{formatCopy(copy.allocated,{v0:promotion.allocated})}}</p><p v-else role="status">{{say(copy.loading)}}</p></div><InfoTip :label="say(copy.rules_label)"><p>{{say(copy.rules)}}</p></InfoTip></div>
  <button type="button" class="desk-button secondary" :disabled="!promotion||loading" @click="edit"><PhPencilSimple/>{{say(copy.edit)}}</button>
  <p v-if="error" class="desk-error" role="alert">{{error}} <button type="button" class="desk-link" @click="load">{{say(copy.retry)}}</button></p>
 </section>
 <SlideOver v-model="open" :title="say(copy.desk_title)" :busy="busy">
  <form id="patch-promotion-form" class="patch-promotion-form" @submit.prevent="save">
   <label class="desk-field">{{say(copy.quota)}}<input v-model.number="quota" type="number" min="0" max="100000" step="1" required :disabled="busy"/></label>
   <label class="desk-field">{{say(copy.remaining_label)}}<input v-model.number="remaining" type="number" min="0" max="100000" step="1" required :disabled="busy" aria-describedby="patch-remaining-help" @input="remainingEdited=true"/></label>
   <p id="patch-remaining-help" class="fine-print">{{say(copy.remaining_help)}}</p>
   <div class="patch-promotion-toggle"><span>{{say(copy.enabled)}}</span><ToggleSwitch v-model="enabled" :label="say(copy.enabled)" :disabled="busy"/></div>
   <p class="fine-print">{{say(copy.rules)}}</p><p class="fine-print">{{say(copy.quota_help)}}</p>
   <p v-if="saveError" class="desk-error" role="alert">{{saveError}} <button type="button" class="desk-link" :disabled="busy" @click="reloadEdit">{{say(copy.retry)}}</button></p>
  </form>
  <template #footer><button type="button" class="desk-button secondary" :disabled="busy" @click="open=false">{{say(copy.cancel)}}</button><button type="submit" form="patch-promotion-form" class="desk-button primary" :disabled="busy">{{say(busy?copy.saving:copy.save)}}<PhCheck/></button></template>
 </SlideOver>
</template>
<style>
.patch-promotion-settings{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;padding:20px 24px;background:#f2f7fa;border:1px solid #e2e9ed;border-radius:18px;margin:20px 0}
.patch-promotion-heading{display:flex;align-items:center;gap:12px;min-width:0}.patch-promotion-heading>svg{flex-shrink:0;color:#607d8c}
.patch-promotion-heading h2{font:600 16px var(--body);margin:0 0 6px}.patch-promotion-heading p{font-size:13px;margin:0;color:#61717b;font-variant-numeric:tabular-nums}
.patch-promotion-form{display:grid;gap:20px}.patch-promotion-form .fine-print{margin:0;line-height:1.8}
.patch-promotion-toggle{display:flex;align-items:center;justify-content:space-between;gap:16px}
.patch-gift-badge{display:inline-flex;width:fit-content;align-items:center;color:#49667a;background:#eaf3f8;border:1px solid #d8e7ee;border-radius:7px;padding:3px 7px;font-size:12px;line-height:1.5}
.patch-promotion-settings>.desk-error{flex-basis:100%;margin:0}
@media(max-width:600px){.patch-promotion-settings{padding:16px}.patch-promotion-settings>.desk-button{margin-left:auto}.patch-promotion-heading{gap:8px}.patch-promotion-heading h2{font-size:15px}}
</style>
