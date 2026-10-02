<script setup lang="ts">
import {computed,onBeforeUnmount,reactive,ref,watch} from 'vue';
import StudioCalendar from './StudioCalendar.vue';
import StudioGlyph from './StudioGlyph.vue';
import {useUserStore} from '../store/studio-user';
import {MiniappError,studioRead,studioCall} from '../utils/miniapp-client';
import {studioWords,bookingError,fillWords} from '../utils/studio-content';
import {invalidateStudioSnapshots,rememberStudioSnapshot} from '../utils/studio-cache';
import {onViewHide} from '../utils/studio-view-lifecycle';
import {validBooking,requestId,type Booking,type Calendar,type Receipt} from '../utils/studio-booking';
defineOptions({options:{styleIsolation:'shared'}});
const props=defineProps<{reservation:Receipt;language:string;width:number}>();
const emit=defineEmits<{changed:[Receipt]}>();
const user=useUserStore(),open=ref(false),loading=ref(false),busy=ref(false),errorCode=ref(''),conflict=ref(false),calendar=ref<Calendar>(),base=ref<Receipt>();
const booking=reactive<Booking>({...props.reservation.booking});let sequence=0,intent:{booking:Record<string,unknown>;version:number;request_key:string}|undefined;
const text=(key:string)=>studioWords('edit',key)[props.language==='en'?1:0];
const guests=computed(()=>Array.from({length:calendar.value?.max_guests_per_group||Math.max(4,booking.guests)},(_,index)=>index+1));
const eligible=computed(()=>base.value&&(['cancelled','completed'].includes(base.value.status)||JSON.stringify(booking)!==JSON.stringify(base.value.booking))&&!conflict.value&&validBooking(calendar.value||null,booking));
function dismiss(){if(busy.value)return;sequence++;loading.value=false;open.value=false;}
async function load(reload=false){
 const n=++sequence,token=user.token;loading.value=true;calendar.value=undefined;errorCode.value='';
 try{
  if(reload){const latest=await studioRead<Receipt>('/reservations/'+props.reservation.id,token);if(n!==sequence||token!==user.token)return;base.value=latest;Object.assign(booking,latest.booking);conflict.value=false;intent=undefined;emit('changed',latest);}
  const result=await studioRead<Calendar&{reservation_version:number}>('/reservations/'+props.reservation.id+'/edit-calendar?guests='+booking.guests,token);
  if(n!==sequence||token!==user.token)return;
  if(result.reservation_version!==base.value?.version){conflict.value=true;errorCode.value='version_conflict';return;}
  calendar.value=result;
 }catch(e){if(n===sequence)errorCode.value=e instanceof MiniappError?e.code:'generic_error';}
 finally{if(n===sequence)loading.value=false;}
}
function begin(){base.value=props.reservation;Object.assign(booking,props.reservation.booking);conflict.value=false;intent=undefined;open.value=true;void load();}
function guestChange(event:{detail:{value:string}}){booking.guests=guests.value[Number(event.detail.value)];intent=undefined;void load();}
function select(value:Booking){Object.assign(booking,value);}
async function submit(){
 if(!eligible.value||busy.value||!base.value)return;
 const n=++sequence,token=user.token;busy.value=true;errorCode.value='';
 const fields={date:booking.date,start:booking.start,end:booking.end,guests:booking.guests};
 if(!intent||JSON.stringify(intent.booking)!==JSON.stringify(fields)||intent.version!==base.value.version)intent={booking:fields,version:base.value.version,request_key:requestId()};
 try{
  const result=await studioCall<{reservation:Receipt}>('/reservations/'+base.value.id+'/reschedule',intent,'',token);
  if(n===sequence&&token===user.token){invalidateStudioSnapshots(token);rememberStudioSnapshot('/reservations/'+result.reservation.id,token,result.reservation);busy.value=false;open.value=false;emit('changed',result.reservation);uni.showToast({title:text('saved'),icon:'none'});}
 }catch(e){if(n===sequence){errorCode.value=e instanceof MiniappError?e.code:'generic_error';conflict.value=errorCode.value==='version_conflict';}}
 finally{if(n===sequence)busy.value=false;}
}
watch(()=>user.token,()=>{sequence++;open.value=false;loading.value=false;busy.value=false;intent=undefined;});
watch(()=>props.reservation.version,value=>{if(open.value&&base.value&&value!==base.value.version){conflict.value=true;errorCode.value='version_conflict';}});
onBeforeUnmount(()=>sequence++);onViewHide(()=>{if(!busy.value){sequence++;open.value=false;loading.value=false;}});
</script>
<template>
 <button v-if="reservation.can_edit" class="studio-native-link" hover-class="studio-native-pressed" @tap="begin">{{text('action')}}</button>
 <view v-if="open" class="studio-modal studio-edit-overlay" role="dialog" aria-modal="true" :aria-label="text('title')" @touchmove.stop.prevent @tap="dismiss">
  <view class="studio-modal-panel studio-edit-panel" @tap.stop>
   <view class="studio-edit-heading"><text class="studio-native-subtitle">{{text('title')}}</text><button class="studio-native-eye" :disabled="busy" :aria-label="text('cancel')" hover-class="studio-native-pressed" @tap="dismiss"><StudioGlyph name="close" :size="22"/></button></view>
   <scroll-view scroll-y class="studio-edit-body" @touchmove.stop>
    <text class="studio-native-small">{{text('customer_help')}}</text><text v-if="base?.status==='completed'" class="studio-native-small">{{text('completed_help')}}</text>
    <view class="studio-edit-guests"><text class="studio-native-label">{{text('guests')}}</text><picker :range="guests" :value="Math.max(0,guests.indexOf(booking.guests))" :disabled="busy||loading" @change="guestChange"><view class="studio-native-select">{{fillWords(studioWords('edit','guest_count'),language,{v0:booking.guests})}}</view></picker></view>
    <text v-if="loading" class="studio-native-label">{{text('loading')}}</text>
    <StudioCalendar v-if="calendar&&!conflict" :calendar="calendar" :booking="booking" :disabled="busy||loading" :language="language" :width="Math.min(900,width-72)" @select="select"/>
    <text v-if="booking.date&&booking.start&&booking.end" class="studio-native-small studio-edit-summary">{{fillWords(studioWords('edit','summary'),language,{v0:booking.date,v1:booking.start,v2:booking.end,v3:booking.guests})}}</text>
    <text v-if="errorCode" class="studio-native-error">{{bookingError(errorCode)[language==='en'?1:0]}}</text><button v-if="errorCode" class="studio-native-link" :disabled="busy||loading" @tap="load(conflict)">{{text(conflict?'reload':'retry')}}</button>
   </scroll-view>
   <view class="studio-edit-actions"><button class="studio-native-secondary" :disabled="busy" hover-class="studio-native-pressed" @tap="dismiss">{{text('cancel')}}</button><button class="studio-native-primary" :disabled="busy||loading||!eligible" hover-class="studio-native-pressed" @tap="submit">{{text(busy?'saving':'submit')}}</button></view>
  </view>
 </view>
</template>
<style scoped>
.studio-edit-panel{width:calc(100vw - 32px);max-width:960px;box-sizing:border-box;padding:24px;max-height:85vh;overflow:hidden}
.studio-edit-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px}
.studio-edit-heading .studio-native-eye{flex-shrink:0}.studio-edit-body{max-height:58vh;height:58vh}
.studio-edit-guests{display:flex;align-items:center;gap:16px;margin:18px 0}.studio-edit-guests .studio-native-select{font-size:16px;min-height:44px;min-width:84px}
.studio-edit-actions{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px}.studio-edit-actions button{min-width:0;font-size:15px;padding-inline:12px}
.studio-edit-summary{display:block;margin-top:12px}
@media(max-width:360px){.studio-edit-panel{padding:18px}.studio-edit-actions{gap:8px}}
</style>
