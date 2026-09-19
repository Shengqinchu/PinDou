<script setup lang="ts">
import { ref, watch } from 'vue';
import SlideOver from '../SlideOver.vue';
import { useDesk } from '../../admin';
import { CommerceError } from '../../commerce';
import { contentModule } from '../../content-store';
import defaults from '../../content/admin-controls.json';
import { say } from '../../state';
const w=contentModule('admin-controls',defaults);
const props=defineProps<{modelValue:boolean;title:string;description:string;items:string[];path:string;body:Record<string,unknown>;restore?:boolean}>();
const emit=defineEmits<{'update:modelValue':[boolean];saved:[];reload:[]}>();
const {request}=useDesk();
const busy=ref(false),error=ref(''),uncertain=ref(false),conflict=ref(false);
let attempt:{key:string;path:string;body:string}|undefined;
watch(()=>props.modelValue,value=>{if(value){attempt=undefined;error.value='';uncertain.value=false;conflict.value=false;}});
async function submit(){
 if(busy.value||conflict.value)return;
 attempt??={key:crypto.randomUUID(),path:props.path,body:JSON.stringify(props.body)};
 busy.value=true;error.value='';
 try{
  await request(attempt.path,{method:'POST',headers:{'Idempotency-Key':attempt.key},body:attempt.body});
  emit('update:modelValue',false);emit('saved');
 }catch(e){
  error.value=(e as Error).message;
  uncertain.value=!(e instanceof CommerceError&&e.status>=400&&e.status<500);
  conflict.value=e instanceof CommerceError&&e.status===409;
 }finally{busy.value=false;}
}
</script>
<template>
 <SlideOver :model-value="modelValue" :title="title" :busy="busy" @update:model-value="emit('update:modelValue',$event)">
  <p class="archive-description">{{description}}</p>
  <ul class="archive-items"><li v-for="(item,index) in items" :key="index">{{item}}</li></ul>
  <p v-if="error" class="desk-error" role="alert">{{error}}</p>
  <p v-if="uncertain" role="status">{{say(w.uncertain)}}</p>
  <template #footer>
   <button type="button" class="desk-button secondary" :disabled="busy" @click="emit('update:modelValue',false)">{{say(w.cancel)}}</button>
   <button v-if="conflict" type="button" class="desk-button primary" @click="emit('update:modelValue',false);emit('reload')">{{say(w.reload)}}</button>
   <button v-else type="button" class="desk-button" :class="restore?'primary':'admin-delete-button'" :disabled="busy" @click="submit">{{say(busy?w.saving:uncertain?w.retry:restore?w.confirmRestore:w.confirmDelete)}}</button>
  </template>
 </SlideOver>
</template>
<style>
.admin-delete-button{color:#9b4147;border:1px solid #d6aeb2;background:#fff8f8}
.archive-description{line-height:1.8;color:#4c5960;overflow-wrap:anywhere}
.archive-items{padding-left:24px;line-height:2;overflow-wrap:anywhere}
.admin-archive-tabs{display:flex;gap:20px;flex-wrap:wrap;border-bottom:1px solid #dce6ec;margin:20px 0}
.admin-archive-tabs button{border:0;background:none;padding:12px 0;min-height:44px;color:#667b87;font:inherit}
.admin-archive-tabs button[aria-pressed=true]{border-bottom:2px solid #799eaf;color:#263d47}
.admin-archive-notice{padding:12px;background:#f0f6fa;border-radius:10px;line-height:1.8}
.wallet-redeem-all{margin:0 0 12px;min-height:44px}
.wallet-form:focus{outline:2px solid #8fadb9;outline-offset:4px}
.wallet-reverse{min-height:44px!important;padding:8px 12px!important;border:1px solid #dce6ec!important;border-radius:8px}
</style>
