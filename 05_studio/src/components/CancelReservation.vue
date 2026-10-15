<script setup lang="ts">
import { onBeforeUnmount,ref,useId,watch } from 'vue';
import { PhX,PhCalendarX } from '@phosphor-icons/vue';
import { cancellationCopy as copy,reservationRevision,type CancellationPolicy } from '../cancellation';
import { commerceApi } from '../commerce';
import { accountUser } from '../account';
import { useStudioModal } from '../modal';
import { notify } from '../ui';
import { say,formatCopy,prettyDate,phoneHref } from '../state';
import type { Reservation } from '../reservations';
const props=defineProps<{reservation:Reservation}>();
const open=ref(false),busy=ref(false),loading=ref(false),error=ref(''),policy=ref<CancellationPolicy>();
const dialog=ref<HTMLDialogElement>(),heading=useId(),description=useId();
const modal=useStudioModal(dialog,'photo');let seq=0;
watch(open,value=>value?modal.open():modal.close());
watch(()=>accountUser.value?.id,()=>{seq++;open.value=false;policy.value=undefined;busy.value=false;loading.value=false;});
onBeforeUnmount(()=>{seq++;});
function dismiss(){if(!busy.value){seq++;loading.value=false;open.value=false;}}
async function check(){
 const n=++seq,owner=accountUser.value?.id;loading.value=true;error.value='';policy.value=undefined;
 try{const data=await commerceApi<CancellationPolicy>('/reservations/'+props.reservation.id+'/cancellation');if(n===seq&&owner===accountUser.value?.id)policy.value=data;}
 catch(e){if(n===seq)error.value=(e as Error).message;}
 finally{if(n===seq)loading.value=false;}
}
function begin(){open.value=true;void check();}
async function cancel(){
 if(busy.value||loading.value||!policy.value?.eligible)return;
 const n=++seq,owner=accountUser.value?.id;busy.value=true;error.value='';
 try{
  await commerceApi('/reservations/'+props.reservation.id+'/cancel',{method:'POST',body:JSON.stringify({version:policy.value.version})});
  if(n===seq&&owner===accountUser.value?.id){busy.value=false;open.value=false;reservationRevision.value++;notify(copy.done[0],copy.done[1]);}
 }catch(e){if(n===seq){error.value=(e as Error).message;}}
 finally{if(n===seq)busy.value=false;}
}
</script>
<template>
 <button v-if="reservation.can_cancel" type="button" class="text-link reservation-cancel-link" @click="begin"><PhCalendarX/>{{say(copy.action)}}</button>
 <Teleport to="body"><dialog ref="dialog" class="modal-shell cancellation-dialog" :aria-labelledby="heading" :aria-describedby="description" @cancel.prevent="dismiss">
  <div class="modal-shade" aria-hidden="true" @click="dismiss"/>
  <section class="modal-panel cancellation-panel">
   <div class="cancellation-heading"><h2 :id="heading">{{say(copy.title)}}</h2><button type="button" class="icon-button" :aria-label="say(copy.keep)" :disabled="busy" @click="dismiss"><PhX/></button></div>
   <p class="cancellation-booking">{{prettyDate(reservation.booking.date)}} · {{reservation.booking.start}}–{{reservation.booking.end}}</p>
   <p :id="description">{{say(copy.rule)}}</p>
   <p v-if="loading" role="status">{{say(copy.loading)}}</p>
   <template v-if="policy"><p v-if="policy.eligible" class="cancellation-count">{{formatCopy(copy.count,{v0:policy.used,v1:policy.limit,v2:Math.max(0,policy.remaining-1)})}}</p><p v-else class="form-error">{{say(copy[policy.reason!])}}</p><p class="cancellation-reset">{{formatCopy(copy.reset,{v0:prettyDate(policy.reset_date)})}}</p></template>
   <p v-if="error" class="form-error" role="alert">{{error}}</p><button v-if="error" type="button" class="text-link" :disabled="busy||loading" @click="check">{{say(copy.retry)}}</button>
   <div class="cancellation-actions"><button type="button" autofocus class="button button-secondary" :disabled="busy" @click="dismiss">{{say(copy.keep)}}</button><button v-if="!policy||policy.eligible" type="button" class="button cancellation-confirm" :disabled="busy||loading||!policy?.eligible" @click="cancel">{{say(busy?copy.working:copy.confirm)}}</button><a v-else class="text-link" :href="phoneHref">{{say(copy.contact)}}</a></div>
  </section>
 </dialog></Teleport>
</template>
