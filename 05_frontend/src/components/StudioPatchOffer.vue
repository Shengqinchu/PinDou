<script setup lang="ts">
import StudioGlyph from './StudioGlyph.vue';
import {studioWords,fillWords} from '../utils/studio-content';
import type {PatchPromotion} from '../utils/studio-patch-promotion';
defineOptions({options:{styleIsolation:'shared'}});
const props=defineProps<{offer:PatchPromotion;language:string}>();
defineEmits<{dismiss:[];book:[]}>();
const words=(key:string)=>studioWords('promotion',key)[props.language==='en'?1:0];
</script>
<template>
 <view class="studio-modal" role="dialog" aria-modal="true" :aria-label="words('title')" @tap="$emit('dismiss')" @touchmove.stop.prevent>
  <view class="studio-modal-panel studio-patch-popup" @tap.stop>
   <view class="studio-patch-popup-top"><StudioGlyph name="patch" :size="32"/><button class="studio-native-eye" hover-class="studio-native-pressed" :aria-label="words('close')" @tap="$emit('dismiss')"><StudioGlyph name="close"/></button></view>
   <text class="studio-native-title">{{words('title')}}</text>
   <text class="studio-native-body">{{offer.remaining>0?fillWords(studioWords('promotion','intro'),language,{v0:offer.quota}):words('exhausted')}}</text>
   <text v-if="offer.remaining>0" class="studio-native-small studio-native-label">{{fillWords(studioWords('promotion','remaining'),language,{v0:offer.remaining,v1:offer.quota})}}</text>
   <text class="studio-patch-bonus">{{words('bonus')}}</text>
   <button class="studio-native-primary" hover-class="studio-native-pressed" @tap="$emit('book')"><text class="studio-native-primary-label">{{words('book')}}</text><StudioGlyph name="arrow" :size="19"/></button>
  </view>
 </view>
</template>
