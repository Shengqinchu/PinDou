<script setup lang="ts">
import { onBeforeUnmount,ref,watch } from 'vue';
import { useUserStore } from '../store/user';
import { MiniappError,studioRead,studioCall } from '../utils/miniapp-client';
import { studioWords,bookingError,studioProfile,fillWords } from '../utils/studio-content';
import {invalidateStudioSnapshots,rememberStudioSnapshot} from '../utils/studio-cache';
import {onViewHide} from '../utils/studio-view-lifecycle';
import type { Receipt,CancelPolicy } from '../utils/studio-booking';
defineOptions({options:{styleIsolation:'shared'}});
const props=defineProps<{reservation:Receipt;language:string}>();
const emit=defineEmits<{changed:[Receipt]}>();
const user=useUserStore(),open=ref(false),loading=ref(false),busy=ref(false),policy=ref<CancelPolicy>(),errorCode=ref('');let sequence=0;
const words=(key:string)=>studioWords('cancellation',key)[props.language==='en'?1:0];
function dismiss(){if(busy.value)return;sequence++;open.value=false;loading.value=false;}
async function check(){
 const seq=++sequence,token=user.token;loading.value=true;errorCode.value='';policy.value=undefined;
 try{const value=await studioRead<CancelPolicy>('/reservations/'+props.reservation.id+'/cancellation',token);if(seq===sequence&&token===user.token)policy.value=value;}
 catch(e){if(seq===sequence)errorCode.value=e instanceof MiniappError?e.code:'generic_error';}
 finally{if(seq===sequence)loading.value=false;}
}
function begin(){open.value=true;void check();}
async function cancel(){
 if(busy.value||loading.value||!policy.value?.eligible)return;
 const seq=++sequence,token=user.token;busy.value=true;errorCode.value='';
 try{
  const result=await studioCall<{reservation:Receipt}>('/reservations/'+props.reservation.id+'/cancel',{version:policy.value.version},'',token);
  if(seq===sequence&&token===user.token){invalidateStudioSnapshots(token);rememberStudioSnapshot('/reservations/'+result.reservation.id,token,result.reservation);busy.value=false;open.value=false;emit('changed',result.reservation);uni.showToast({title:words('done'),icon:'none'});}
 }catch(e){if(seq===sequence)errorCode.value=e instanceof MiniappError?e.code:'generic_error';}
 finally{if(seq===sequence)busy.value=false;}
}
function phone(){uni.makePhoneCall({phoneNumber:studioProfile.phone.replace(/\s/g,'')});}
watch(()=>user.token,()=>{sequence++;open.value=false;policy.value=undefined;busy.value=false;loading.value=false;});
onBeforeUnmount(()=>sequence++);
onViewHide(()=>{if(!busy.value){sequence++;open.value=false;policy.value=undefined;loading.value=false;}});
</script>
<template>
 <button :hover-stay-time="180" :hover-start-time="0" v-if="reservation.can_cancel" class="studio-cancel-link" hover-class="studio-native-pressed" @tap="begin">{{words('action')}}</button>
 <view v-if="open" class="studio-modal" role="dialog" aria-modal="true" :aria-label="words('title')" @touchmove.stop.prevent @tap="dismiss">
  <view class="studio-modal-panel" @tap.stop>
   <text class="studio-native-subtitle">{{words('title')}}</text>
   <text class="studio-native-label">{{reservation.booking.date}} · {{reservation.booking.start}}–{{reservation.booking.end}}</text>
   <view v-if="loading" class="studio-native-status"><view class="studio-native-progress"/><text class="studio-native-body">{{words('loading')}}</text></view>
   <text v-if="policy" class="studio-native-label studio-cancel-remaining">{{fillWords(studioWords('cancellation','remaining_short'),language,{v0:policy.remaining,v1:policy.limit})}}</text>
   <text v-if="policy&&!policy.eligible" class="studio-native-error">{{words(policy.reason||'reservation_cancellation_unavailable')}}</text>
   <text v-if="errorCode" class="studio-native-error">{{bookingError(errorCode)[language==='en'?1:0]}}</text>
   <button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" v-if="errorCode" class="studio-native-link" :disabled="busy||loading" @tap="check">{{words('retry')}}</button>
   <button :hover-stay-time="180" :hover-start-time="0" class="studio-native-primary" :disabled="busy" hover-class="studio-native-pressed" @tap="dismiss">{{words('keep')}}</button>
   <button :hover-stay-time="180" :hover-start-time="0" v-if="!policy||policy.eligible" class="studio-native-secondary studio-cancel-confirm" :disabled="busy||loading||!policy?.eligible" hover-class="studio-native-pressed" @tap="cancel">{{words(busy?'working':'confirm')}}</button>
   <button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" v-else class="studio-native-link" @tap="phone">{{words('contact')}}</button>
  </view>
 </view>
</template>
