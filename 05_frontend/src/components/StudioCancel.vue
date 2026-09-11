<script setup lang="ts">
import { computed,onBeforeUnmount,ref,watch } from 'vue';
import { useUserStore } from '../store/user';
import { MiniappError,studioRead,studioCall } from '../utils/miniapp-client';
import { studioWords,bookingError,fillWords,studioProfile } from '../utils/studio-content';
import type { Receipt,CancelPolicy } from '../utils/studio-booking';
defineOptions({options:{styleIsolation:'shared'}});
const props=defineProps<{reservation:Receipt;language:string}>();
const emit=defineEmits<{changed:[Receipt]}>();
const user=useUserStore(),open=ref(false),loading=ref(false),busy=ref(false),policy=ref<CancelPolicy>(),errorCode=ref('');let sequence=0;
const words=(key:string)=>studioWords('cancellation',key)[props.language==='en'?1:0];
const countText=computed(()=>policy.value?fillWords(studioWords('cancellation','count'),props.language,{v0:policy.value.used,v1:policy.value.limit,v2:Math.max(0,policy.value.remaining-1)}):'');
const resetText=computed(()=>policy.value?fillWords(studioWords('cancellation','reset'),props.language,{v0:policy.value.reset_date}):'');
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
  if(seq===sequence&&token===user.token){busy.value=false;open.value=false;emit('changed',result.reservation);uni.showToast({title:words('done'),icon:'none'});}
 }catch(e){if(seq===sequence)errorCode.value=e instanceof MiniappError?e.code:'generic_error';}
 finally{if(seq===sequence)busy.value=false;}
}
function phone(){uni.makePhoneCall({phoneNumber:studioProfile.phone.replace(/\s/g,'')});}
watch(()=>user.token,()=>{sequence++;open.value=false;policy.value=undefined;busy.value=false;loading.value=false;});
onBeforeUnmount(()=>sequence++);
</script>
<template>
 <button v-if="reservation.can_cancel" class="studio-cancel-link" hover-class="studio-native-pressed" @tap="begin">{{words('action')}}</button>
 <view v-if="open" class="studio-modal" role="dialog" aria-modal="true" :aria-label="words('title')" @touchmove.stop.prevent @tap="dismiss">
  <view class="studio-modal-panel" @tap.stop>
   <text class="studio-native-subtitle">{{words('title')}}</text>
   <text class="studio-native-label">{{reservation.booking.date}} · {{reservation.booking.start}}–{{reservation.booking.end}}</text>
   <text class="studio-native-body">{{words('rule')}}</text>
   <view v-if="loading" class="studio-native-status"><view class="studio-native-progress"/><text class="studio-native-body">{{words('loading')}}</text></view>
   <template v-if="policy"><text :class="policy.eligible?'studio-cancel-count':'studio-native-error'">{{policy.eligible?countText:words(policy.reason||'reservation_cancellation_unavailable')}}</text><text class="studio-native-label">{{resetText}}</text></template>
   <text v-if="errorCode" class="studio-native-error">{{bookingError(errorCode)[language==='en'?1:0]}}</text>
   <button v-if="errorCode" class="studio-native-link" :disabled="busy||loading" @tap="check">{{words('retry')}}</button>
   <button class="studio-native-primary" :disabled="busy" hover-class="studio-native-pressed" @tap="dismiss">{{words('keep')}}</button>
   <button v-if="!policy||policy.eligible" class="studio-native-secondary studio-cancel-confirm" :disabled="busy||loading||!policy?.eligible" hover-class="studio-native-pressed" @tap="cancel">{{words(busy?'working':'confirm')}}</button>
   <button v-else class="studio-native-link" @tap="phone">{{words('contact')}}</button>
  </view>
 </view>
</template>
