<script setup lang="ts">
import StudioBrand from './StudioBrand.vue';
defineOptions({ options: { styleIsolation: 'shared' } });
defineProps<{ language: string; keyboardOpen?: boolean; shellStyle: Record<string,string> }>();
defineEmits<{ language: [] }>();
</script>
<template>
  <view class="studio-native" :class="{'studio-native--en':language==='en','studio-native--keyboard':keyboardOpen}" :style="shellStyle">
    <view class="studio-native-top">
      <StudioBrand :language="language" />
      <button class="studio-native-language" hover-class="studio-native-pressed" :hover-stay-time="180" @tap="$emit('language')">{{language==='zh'?'English':'中文'}}</button>
    </view>
    <slot />
  </view>
</template>
