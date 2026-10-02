<script setup lang="ts">
import { computed,onBeforeUnmount,reactive,ref,useId,watch } from 'vue';
import { PhX,PhPencilSimple } from '@phosphor-icons/vue';
import ReservationCalendar from './ReservationCalendar.vue';
import { reservationEditCopy as copy,changeRequestKey } from '../reservation-edit';
import { commerceApi,CommerceError } from '../commerce';
import { accountUser } from '../account';
import { useStudioModal } from '../modal';
import { notify } from '../ui';
import { say,formatCopy } from '../state';
import { reservationRevision } from '../cancellation';
import { validSelection,type Reservation,type ReservationCalendar as Calendar } from '../reservations';
const props=defineProps<{reservation:Reservation}>();
const emit=defineEmits<{changed:[Reservation]}>();
const open=ref(false),loading=ref(false),busy=ref(false),error=ref(''),conflict=ref(false),calendar=ref<Calendar>();
const base=ref<Reservation>(),booking=reactive({...props.reservation.booking});
const dialog=ref<HTMLDialogElement>(),heading=useId(),modal=useStudioModal(dialog,'photo');
let sequence=0,intent:{booking:Record<string,unknown>;version:number;request_key:string}|undefined;
const changed=computed(()=>base.value&&(['cancelled','completed'].includes(base.value.status)||JSON.stringify(base.value.booking)!==JSON.stringify(booking)));
const valid=computed(()=>changed.value&&!conflict.value&&validSelection(calendar.value||null,booking));
watch(open,value=>value?modal.open():modal.close());
function dismiss(){if(busy.value)return;sequence++;loading.value=false;open.value=false;}
async function load(reload=false){
 const n=++sequence,owner=accountUser.value?.id;loading.value=true;error.value='';calendar.value=undefined;
 try{
  if(reload){const latest=await commerceApi<Reservation>('/reservations/'+props.reservation.id);if(n!==sequence||owner!==accountUser.value?.id)return;base.value=latest;Object.assign(booking,latest.booking);intent=undefined;conflict.value=false;emit('changed',latest);}
  const result=await commerceApi<Calendar&{reservation_version:number}>('/reservations/'+props.reservation.id+'/edit-calendar?guests='+booking.guests);
  if(n!==sequence||owner!==accountUser.value?.id)return;
  if(result.reservation_version!==base.value?.version){conflict.value=true;error.value=say(copy.version_conflict);return;}
  calendar.value=result;
 }catch(e){if(n===sequence)error.value=(e as Error).message;}
 finally{if(n===sequence)loading.value=false;}
}
function begin(){base.value=props.reservation;Object.assign(booking,props.reservation.booking);intent=undefined;conflict.value=false;open.value=true;void load();}
function guestsChanged(){intent=undefined;void load();}
async function submit(){
 if(!valid.value||busy.value||!base.value)return;
 const n=++sequence,owner=accountUser.value?.id;busy.value=true;error.value='';
 const fields={date:booking.date,start:booking.start,end:booking.end,guests:booking.guests};
 if(!intent||JSON.stringify(intent.booking)!==JSON.stringify(fields)||intent.version!==base.value.version)intent={booking:fields,version:base.value.version,request_key:changeRequestKey()};
 try{
  const result=await commerceApi<{reservation:Reservation}>('/reservations/'+base.value.id+'/reschedule',{method:'POST',body:JSON.stringify(intent)});
  if(n===sequence&&owner===accountUser.value?.id){busy.value=false;open.value=false;emit('changed',result.reservation);reservationRevision.value++;notify(copy.saved[0],copy.saved[1]);}
 }catch(e){if(n===sequence){conflict.value=e instanceof CommerceError&&e.status===409&&e.code==='version_conflict';error.value=conflict.value?say(copy.version_conflict):(e as Error).message;}}
 finally{if(n===sequence)busy.value=false;}
}
watch(()=>accountUser.value?.id,()=>{sequence++;open.value=false;busy.value=false;loading.value=false;intent=undefined;});
watch(()=>props.reservation.version,value=>{if(open.value&&base.value&&value!==base.value.version){conflict.value=true;error.value=say(copy.version_conflict);}});
onBeforeUnmount(()=>{sequence++;});
</script>
<template>
 <button v-if="reservation.can_edit" type="button" class="text-link reservation-edit-action" @click="begin"><PhPencilSimple/>{{say(copy.action)}}</button>
 <Teleport to="body"><dialog ref="dialog" class="modal-shell cancellation-dialog reservation-edit-dialog" :aria-labelledby="heading" @cancel.prevent="dismiss">
  <div class="modal-shade" aria-hidden="true" @click="dismiss"/>
  <section class="modal-panel cancellation-panel reservation-edit-panel">
   <header class="reservation-edit-heading"><h2 :id="heading">{{say(copy.title)}}</h2><button class="icon-button" type="button" :aria-label="say(copy.cancel)" :disabled="busy" @click="dismiss"><PhX/></button></header>
   <div class="reservation-edit-body"><p class="fine-print">{{say(copy.customer_help)}}</p><p v-if="base?.status==='completed'" class="fine-print">{{say(copy.completed_help)}}</p>
   <label class="desk-field reservation-edit-guests">{{say(copy.guests)}}<select v-model.number="booking.guests" :aria-label="say(copy.guests)" :disabled="busy||loading" @change="guestsChanged"><option v-for="count in calendar?.max_guests_per_group||Math.max(4,booking.guests)" :key="count" :value="count">{{formatCopy(copy.guest_count,{v0:count})}}</option></select></label>
   <p v-if="loading" role="status">{{say(copy.loading)}}</p>
   <ReservationCalendar v-if="calendar&&!conflict" :calendar="calendar" :booking="booking" :disabled="busy||loading" compact @select="Object.assign(booking,$event)"/>
   <p v-if="booking.date&&booking.start&&booking.end" class="reservation-edit-summary">{{formatCopy(copy.summary,{v0:booking.date,v1:booking.start,v2:booking.end,v3:booking.guests})}}</p>
   <p v-if="error" class="form-error" role="alert">{{error}}</p>
   <button v-if="error" class="text-link" type="button" :disabled="busy||loading" @click="load(conflict)">{{say(conflict?copy.reload:copy.retry)}}</button></div>
   <footer class="reservation-edit-actions"><button class="button button-secondary" type="button" :disabled="busy" @click="dismiss">{{say(copy.cancel)}}</button><button class="button button-primary" type="button" :disabled="busy||loading||!valid" @click="submit">{{say(busy?copy.saving:copy.submit)}}</button></footer>
  </section>
 </dialog></Teleport>
</template>
<style scoped>
.reservation-edit-panel{width:min(960px,calc(100vw - 32px));max-width:960px;max-height:calc(var(--viewport-height,100dvh) - 40px);overflow:hidden;padding:clamp(20px,4vw,32px);display:flex;flex-direction:column;box-sizing:border-box}
.reservation-edit-body{overflow:auto;min-height:0;padding-right:4px}
.reservation-edit-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:12px;flex-shrink:0}
.reservation-edit-heading h2{font-size:clamp(22px,4vw,30px);margin:0}
.reservation-edit-heading .icon-button{flex-shrink:0}
.reservation-edit-guests{max-width:220px;margin:18px 0}
.reservation-edit-guests select{font-size:16px;min-height:44px}
.reservation-edit-actions{display:flex;justify-content:flex-end;gap:12px;margin-top:20px;padding-bottom:env(safe-area-inset-bottom);flex-shrink:0}
.reservation-edit-summary{font-size:14px;color:var(--muted);line-height:1.5}
.reservation-edit-action{display:inline-flex;align-items:center;gap:6px}
@media(max-width:480px){.reservation-edit-actions{display:grid;grid-template-columns:1fr 1fr}.reservation-edit-actions .button{min-width:0;padding-inline:14px;font-size:15px}}
</style>
