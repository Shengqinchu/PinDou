<script setup lang="ts">
import copy from '../../../05_studio/src/content/customer-notifications.json';
import {wechatKinds,type WechatKind,type WechatChoice} from '../utils/customer-notifications';
const props=defineProps<{language:string;choices:Partial<Record<WechatKind,WechatChoice>>}>();
const words=(key:string)=>(copy as Record<string,string[]>)[key]?.[props.language==='en'?1:0]||'';
</script>
<template>
 <view v-if="Object.keys(choices).length" class="wechat-outcome" role="status">
  <text class="wechat-outcome-title">{{words('wechat_result_title')}}</text>
  <view v-for="kind in wechatKinds.filter(item=>choices[item])" :key="kind" class="wechat-outcome-row"><text>{{words('wechat_kind_'+kind)}}</text><text>{{words(choices[kind]==='accept'?'wechat_choice_allowed':choices[kind]==='unavailable'?'wechat_choice_unavailable':'wechat_choice_declined')}}</text></view>
 </view>
</template>
<style scoped>
.wechat-outcome{display:flex;flex-direction:column;gap:6px;padding:12px;border:1px solid #dce5ea;border-radius:10px;background:#f7fbfd;color:#56666f;font-size:13px;line-height:1.5}.wechat-outcome-title{font-weight:600}.wechat-outcome-row{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 12px}
</style>
