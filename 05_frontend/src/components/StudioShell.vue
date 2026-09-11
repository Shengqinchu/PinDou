<script setup lang="ts">
import StudioBrand from './StudioBrand.vue';
import StudioNav from './StudioNav.vue';
defineOptions({ options: { styleIsolation: 'shared' } });
defineProps<{ language: string; keyboardOpen?: boolean; shellStyle: Record<string,string>; nav?:'home'|'bookings'|'account' }>();
defineEmits<{ language: [] }>();
</script>
<template>
  <view class="studio-native" :class="{'studio-native--en':language==='en','studio-native--keyboard':keyboardOpen,'studio-native--nav':nav}" :style="shellStyle">
    <view class="studio-native-top">
      <StudioBrand :language="language" />
      <button class="studio-native-language" hover-class="studio-native-pressed" :hover-stay-time="180" @tap="$emit('language')">{{language==='zh'?'English':'中文'}}</button>
    </view>
    <slot />
    <StudioNav v-if="nav&&!keyboardOpen" id="studio-navigation" :active="nav" :language="language"/>
  </view>
</template>
