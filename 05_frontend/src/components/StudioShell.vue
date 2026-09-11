<script setup lang="ts">
import StudioBrand from './StudioBrand.vue';
import StudioNav from './StudioNav.vue';
import {ref,watch,nextTick} from 'vue';
defineOptions({ options: { styleIsolation: 'shared' } });
const props=defineProps<{ language: string; keyboardOpen?: boolean; shellStyle: Record<string,string>; nav?:'home'|'bookings'|'account'; fitted?:boolean; resetKey?:number }>();
const scrollTop=ref(0);
watch(()=>props.resetKey,async()=>{scrollTop.value=1;await nextTick();scrollTop.value=0;});
defineEmits<{ language: [] }>();
</script>
<template>
  <view class="studio-native" :class="{'studio-native--en':language==='en','studio-native--keyboard':keyboardOpen,'studio-native--nav':nav,'studio-native--fitted':fitted}" :style="shellStyle">
    <view class="studio-native-top">
      <StudioBrand :language="language" />
      <button class="studio-native-language" hover-class="studio-native-pressed" :hover-stay-time="180" @tap="$emit('language')">{{language==='zh'?'English':'中文'}}</button>
    </view>
    <scroll-view v-if="fitted" class="studio-native-scroll" scroll-y :scroll-top="scrollTop" :show-scrollbar="false" :scroll-with-animation="false"><view class="studio-native-scroll-inner"><slot /></view></scroll-view>
    <slot v-else />
    <view class="studio-native-dock"><slot name="actions"/></view>
    <StudioNav v-if="nav&&!keyboardOpen" id="studio-navigation" :active="nav" :language="language"/>
  </view>
</template>
