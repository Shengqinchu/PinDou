<script setup lang="ts">
import {studioWords,fillWords} from '../utils/studio-content';
import type {Payload} from '../utils/studio-booking';
defineOptions({options:{styleIsolation:'shared'}});
const props=defineProps<{review:Payload}>();
defineEmits<{confirm:[];dismiss:[]}>();
const words=(module:Parameters<typeof studioWords>[0],key:string)=>studioWords(module,key)[props.review.locale==='en'?1:0];
</script>
<template>
 <view class="studio-modal studio-submit-modal" role="dialog" aria-modal="true" :aria-label="words('flow','review')" @tap="$emit('dismiss')" @touchmove.stop.prevent>
  <view class="studio-modal-panel studio-submit-panel" @tap.stop>
   <text class="studio-native-subtitle">{{words('flow','review')}}</text>
   <view class="studio-native-definition">
    <view class="studio-native-definition-row"><text class="studio-native-label">{{words('receipt','experience_cc25a0')}}</text><text>{{words('visit',review.booking.plan==='day'?'a_day_of_making_01d6e2':'by_the_hour_5300b2')}}</text></view>
    <view class="studio-native-definition-row"><text class="studio-native-label">{{words('flow','guests')}}</text><text>{{fillWords(studioWords('flow','guest_count'),review.locale,{v0:review.booking.guests})}}</text></view>
    <view class="studio-native-definition-row"><text class="studio-native-label">{{words('calendar','date_label')}}</text><text>{{review.booking.date}}</text></view>
    <view class="studio-native-definition-row"><text class="studio-native-label">{{words('calendar','time_296653')}}</text><text>{{review.booking.start}}–{{review.booking.end}}</text><text class="studio-native-label">{{words('receipt','hamilton_local_time_496f95')}}</text></view>
   </view>
   <text class="studio-native-body studio-native-small">{{words('flow','confirmation_note')}}</text>
   <view class="studio-submit-actions"><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-secondary" @tap="$emit('dismiss')">{{words('flow','back_to_edit')}}</button><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-primary" @tap="$emit('confirm')">{{words('flow','confirm_submit')}}</button></view>
  </view>
 </view>
</template>
