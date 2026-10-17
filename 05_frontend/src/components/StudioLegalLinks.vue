<script setup lang="ts">
import {pressTo} from '../utils/press';
import copy from '../../../05_studio/src/content/studio-miniapp-legal.json';
defineProps<{language:string}>();
function open(type:'privacy'|'agreement'){pressTo('/pages/consent/consent?type='+type);}
</script>
<template>
 <view class="studio-legal-links">
  <button hover-class="studio-native-pressed" :hover-start-time="0" :hover-stay-time="180" @tap="open('privacy')">{{copy.privacy_title[language==='en'?1:0]}}</button>
  <button hover-class="studio-native-pressed" :hover-start-time="0" :hover-stay-time="180" @tap="open('agreement')">{{copy.agreement_title[language==='en'?1:0]}}</button>
 </view>
</template>
<style scoped>
.studio-legal-links{display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap}
.studio-legal-links button{min-height:44px;padding:8px 0;margin:0;border:0;border-radius:0;background:transparent;color:#70838e;font-size:11px;line-height:1.5;display:flex;align-items:center;white-space:normal}
.studio-legal-links button::after{border:0}
</style>
