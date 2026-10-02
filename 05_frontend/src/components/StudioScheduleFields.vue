<script setup lang="ts">
import {computed} from 'vue';
import type {Booking} from '../utils/studio-booking';
import {clock,minutes} from '../utils/studio-booking';
import {studioWords} from '../utils/studio-content';
defineOptions({options:{styleIsolation:'shared'}});
const props=defineProps<{modelValue:Booking;language:string;disabled?:boolean}>();
const emit=defineEmits<{'update:modelValue':[Booking]}>();
const times=Array.from({length:48},(_,i)=>clock(i*30));
const text=(key:string)=>studioWords('edit',key)[props.language==='en'?1:0];
const startIndex=computed(()=>Math.max(0,times.indexOf(props.modelValue.start))),endIndex=computed(()=>Math.max(0,times.indexOf(props.modelValue.end)));
function dateChange(event:{detail:{value:string}}){emit('update:modelValue',{...props.modelValue,date:event.detail.value});}
function timeChange(kind:'start'|'end',event:{detail:{value:string}}){const value=times[Number(event.detail.value)];emit('update:modelValue',{...props.modelValue,[kind]:value,...(kind==='start'&&props.modelValue.plan==='patch'?{end:clock(minutes(value)+60)}:{})});}
function guestsChange(event:{detail:{value:string}}){emit('update:modelValue',{...props.modelValue,guests:Number(event.detail.value)});}
</script>
<template>
 <view class="studio-schedule-fields">
  <text class="studio-schedule-heading">{{text('admin_title')}}</text>
  <view><text class="admin-label">{{text('date')}}</text><picker mode="date" :value="modelValue.date" :disabled="disabled" @change="dateChange"><view class="admin-input">{{modelValue.date}}</view></picker></view>
  <view><text class="admin-label">{{text('guests')}}</text><input class="admin-input" type="number" :value="String(modelValue.guests)" :disabled="disabled" @input="guestsChange"/></view>
  <view><text class="admin-label">{{text('start')}}</text><picker :range="times" :value="startIndex" :disabled="disabled" @change="timeChange('start',$event)"><view class="admin-input">{{modelValue.start}}</view></picker></view>
  <view><text class="admin-label">{{text('end')}}</text><picker :range="times" :value="endIndex" :disabled="disabled||modelValue.plan==='patch'" @change="timeChange('end',$event)"><view class="admin-input">{{modelValue.end}}</view></picker></view>
  <text class="admin-muted studio-schedule-help">{{text('admin_help')}}</text>
 </view>
</template>
<style scoped>
.studio-schedule-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:24px 0;min-width:0}
.studio-schedule-fields>view{min-width:0}.studio-schedule-heading,.studio-schedule-help{grid-column:1/-1}
.studio-schedule-fields .admin-input{font-size:16px;min-height:44px;box-sizing:border-box;width:100%;margin-top:8px}.studio-schedule-heading{font-size:18px;font-weight:500}
</style>
