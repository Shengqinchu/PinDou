<script setup lang="ts">
import {studioPlanWords,studioWords,fillWords} from '../utils/studio-content';
import type {Payload} from '../utils/studio-booking';
import notices from '../../../05_studio/src/content/customer-notifications.json';
defineOptions({options:{styleIsolation:'shared'}});
const props=defineProps<{review:Payload;notificationLoading?:boolean;notificationNote?:string;confirming?:boolean}>();
defineEmits<{confirm:[];dismiss:[];withoutWechat:[]}>();
const words=(module:Parameters<typeof studioWords>[0],key:string)=>studioWords(module,key)[props.review.locale==='en'?1:0];
const notice=(key:string)=>(notices as Record<string,string[]>)[key]?.[props.review.locale==='en'?1:0]||'';
</script>
<template>
 <view class="studio-modal studio-submit-modal" role="dialog" aria-modal="true" :aria-label="words('flow','review')" @tap="!confirming&&$emit('dismiss')" @touchmove.stop.prevent>
  <view class="studio-modal-panel studio-submit-panel" @tap.stop>
   <text class="studio-native-subtitle">{{words('flow','review')}}</text>
   <view class="studio-native-definition">
    <view class="studio-native-definition-row"><text class="studio-native-label">{{words('receipt','experience_cc25a0')}}</text><text>{{studioPlanWords(review.booking.plan)[review.locale==='en'?1:0]}}</text></view>
    <view class="studio-native-definition-row"><text class="studio-native-label">{{words('flow','guests')}}</text><text>{{fillWords(studioWords('flow','guest_count'),review.locale,{v0:review.booking.guests})}}</text></view>
    <view class="studio-native-definition-row"><text class="studio-native-label">{{words('calendar','date_label')}}</text><text>{{review.booking.date}}</text></view>
    <view class="studio-native-definition-row"><text class="studio-native-label">{{words('calendar','time_296653')}}</text><text>{{review.booking.start}}–{{review.booking.end}}</text><text class="studio-native-label">{{words('receipt','hamilton_local_time_496f95')}}</text></view>
   </view>
   <text class="studio-native-body studio-native-small">{{words('flow','confirmation_note')}}</text>
   <!-- #ifdef MP-WEIXIN -->
   <text class="studio-native-body studio-native-small">{{notice(notificationLoading?'wechat_preparing':notificationNote||'wechat_booking_request')}}</text>
   <!-- #endif -->
   <view class="studio-submit-actions"><button :disabled="confirming" :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-secondary" @tap="$emit('dismiss')">{{words('flow','back_to_edit')}}</button><button :disabled="confirming||notificationLoading" :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-primary" @tap="$emit('confirm')">{{words('flow','confirm_submit')}}</button></view>
   <!-- #ifdef MP-WEIXIN -->
   <button hover-class="studio-native-pressed" :hover-start-time="0" :hover-stay-time="180" v-if="notificationNote==='wechat_unavailable'" :disabled="confirming" class="studio-native-link" @tap="$emit('withoutWechat')">{{notice('wechat_submit_without')}}</button>
   <!-- #endif -->
  </view>
 </view>
</template>
