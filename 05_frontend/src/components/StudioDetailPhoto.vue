<script setup lang="ts">
import {computed,ref,watch} from 'vue';
import {studioWords,type StudioMedia} from '../utils/studio-content';
defineOptions({options:{styleIsolation:'shared',virtualHost:true}});
const props=defineProps<{photo:StudioMedia;alt:string;language:string;eager?:boolean}>();
const emit=defineEmits<{open:[]}>();
const failed=ref(false),loaded=ref(false),attempt=ref(0);
watch(()=>props.photo.src,()=>{failed.value=false;loaded.value=false;});
const label=computed(()=>studioWords('process','photoLabel')[props.language==='en'?1:0]+' · '+props.alt);
function press(){if(failed.value){failed.value=false;loaded.value=false;attempt.value++;}else emit('open');}
</script>
<template>
 <view class="studio-detail-photo">
  <button class="studio-detail-photo-button" :data-photo="photo.src" :style="{paddingBottom:(photo.height/photo.width*100)+'%'}" :aria-label="failed?studioWords('miniapp','retry')[language==='en'?1:0]:label" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="press">
   <image v-if="!failed" :key="photo.src+attempt" :src="photo.src" mode="aspectFit" :lazy-load="!eager" webp :aria-label="alt" @load="loaded=true" @error="failed=true"/>
   <view v-if="failed" class="studio-detail-photo-state"><text>{{studioWords('miniapp','retry')[language==='en'?1:0]}}</text></view>
   <view v-else-if="!loaded" class="studio-detail-photo-state" aria-hidden="true"><view class="studio-native-progress"/></view>
  </button>
  <text class="studio-native-label studio-detail-caption">{{alt}}</text>
 </view>
</template>
<style>
.studio-detail-photo{width:100%;min-width:0;display:flex;flex-direction:column;gap:6px}
.studio-native .studio-detail-photo-button{position:relative;display:block;width:100%;height:0;min-height:0;margin:0;padding:0;border-radius:13px;overflow:hidden;background:#f3f7fa}
.studio-detail-photo-button image{position:absolute;inset:0;width:100%;height:100%}
.studio-detail-photo-state{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#657681;font-size:13px;pointer-events:none}
.studio-detail-caption{display:block;line-height:1.5}
</style>
