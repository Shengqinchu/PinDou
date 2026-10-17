<script setup lang="ts">
import {ref} from 'vue';
import copy from '../../../05_studio/src/content/owner-wechat.json';
import workbench from '../../../05_studio/src/content/workbench.json';
const props = defineProps<{language: string; completed: boolean}>();
defineEmits<{confirm: [subscribe: boolean]; dismiss: []}>();
const subscribe = ref(true);
const say = (words: string[]) => words[props.language === 'en' ? 1 : 0];
</script>
<template>
  <view class="owner-save-overlay" role="dialog" aria-modal="true" :aria-label="say(workbench.confirm_save)" @touchmove.stop.prevent @tap="$emit('dismiss')">
    <view class="owner-save-panel" @tap.stop>
      <text class="owner-save-title">{{say(workbench.confirm_save)}}</text>
      <text v-if="completed">{{say(workbench.confirm_complete)}}</text>
      <checkbox-group @change="subscribe = $event.detail.value.includes('next')">
        <label class="owner-save-choice"><checkbox value="next" :checked="subscribe" color="#769aab"/><text>{{say(copy.save_with_alert)}}</text></label>
      </checkbox-group>
      <text class="owner-save-note">{{say(copy.save_alert_note)}}</text>
      <view class="owner-save-actions">
        <button class="owner-save-secondary" hover-class="admin-pressed" :hover-start-time="0" :hover-stay-time="180" @tap="$emit('dismiss')">{{say(workbench.cancel)}}</button>
        <button class="owner-save-primary" hover-class="admin-pressed" :hover-start-time="0" :hover-stay-time="180" @tap="$emit('confirm', subscribe)">{{say(subscribe ? copy.confirm_with_alert : workbench.confirm)}}</button>
      </view>
    </view>
  </view>
</template>
<style scoped>
.owner-save-overlay{position:fixed;inset:0;z-index:200;display:flex;align-items:center;justify-content:center;padding:20px;background:rgba(31,43,50,.3);box-sizing:border-box}
.owner-save-panel{width:100%;max-width:400px;max-height:85vh;overflow-y:auto;padding:22px;box-sizing:border-box;border:1px solid #dce6ec;border-radius:18px;background:#fff;display:flex;flex-direction:column;gap:16px;color:#303b42;font-size:16px;line-height:1.5}
.owner-save-title{font-size:20px;font-weight:600}.owner-save-choice{display:flex;gap:8px;align-items:center;min-height:44px}.owner-save-choice text{flex:1}.owner-save-note{font-size:13px;color:#6e7d86}.owner-save-actions{display:flex;flex-direction:column;gap:10px}.owner-save-actions button{width:100%;min-height:46px;padding:10px 14px;line-height:1.5;white-space:normal;font-size:16px;border-radius:12px;box-sizing:border-box}.owner-save-primary{background:#e7f2f8;color:#303b42}.owner-save-secondary{background:#f5f7f8;color:#303b42}.owner-save-actions button::after{border:0}
</style>
