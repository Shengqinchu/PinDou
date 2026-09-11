<script setup lang="ts">
import StudioGlyph from './StudioGlyph.vue';
import copy from '../../../05_studio/src/content/workbench.json';
import {goAdmin} from '../utils/studio-admin';
import {navigateStudio} from '../utils/studio-navigation';
import {adminView} from '../utils/studio-admin-cache';
import {ref,onMounted,onBeforeUnmount,nextTick} from 'vue';
import {onHide} from '@dcloudio/uni-app';
defineOptions({options:{styleIsolation:'shared'}});
const props=withDefaults(defineProps<{title:string;language:string;shellStyle:Record<string,string>;keyboardOpen?:boolean;active?:'home'|'reservations'|'messages'|'finance';back?:boolean;busy?:boolean;error?:string;scrollTo?:string}>(),{active:'home',back:false,busy:false,error:'',scrollTo:''});
defineEmits<{refresh:[];language:[]}>();
const say=(s:string[])=>s[props.language==='en'?1:0];
const currentPage=getCurrentPages().slice(-1)[0] as any;
const scrollCache=adminView<{top:number}>('scroll:'+(currentPage?.route||props.active)+':'+(currentPage?.options?.id||''));
const scrollTop=ref(scrollCache.snapshot?.top||0);let lastTop=scrollTop.value;
function rememberScroll(){scrollCache.save({top:lastTop});}
onMounted(()=>nextTick(()=>{scrollTop.value=lastTop;}));onHide(rememberScroll);onBeforeUnmount(rememberScroll);
const tabs=[{id:'home',page:'',icon:'home',label:copy.home},{id:'reservations',page:'-reservations',icon:'calendar',label:copy.reservations},{id:'messages',page:'-messages',icon:'wechat',label:copy.messages},{id:'finance',page:'-finance',icon:'grid',label:copy.finance}];
function navigateBack(){uni.navigateBack({fail:()=>uni.redirectTo({url:'/pages/studio/manage'})});}
function navigate(item:{id:string;page:string}){if(item.id!==props.active||props.back)navigateStudio('/pages/studio/manage'+item.page);}
</script>
<template>
 <view class="admin-native" :class="{'admin-native--en':language==='en'}" :style="shellStyle">
  <view class="admin-native-heading"><button v-if="back" class="admin-icon" :aria-label="say(copy.back)" hover-class="admin-pressed" @tap="navigateBack">‹</button><text class="admin-native-title">{{title}}</text><button class="admin-icon" :disabled="busy" :aria-label="say(copy.refresh)" hover-class="admin-pressed" @tap="$emit('refresh')"><StudioGlyph name="refresh" :size="21"/></button><button class="admin-language" hover-class="admin-pressed" @tap="$emit('language')">{{language==='zh'?'EN':'中文'}}</button></view>
  <view v-if="error" class="admin-error"><text>{{error}}</text></view>
  <view v-if="busy" class="admin-loading"><text>{{say(copy.loading)}}</text></view>
  <scroll-view class="admin-native-body" scroll-y :scroll-top="scrollTop" :scroll-into-view="scrollTo" :scroll-with-animation="false" :show-scrollbar="false" @scroll="lastTop=$event.detail.scrollTop"><view class="admin-native-content"><slot/></view></scroll-view>
  <view class="admin-native-actions"><slot name="actions"/></view>
  <view v-if="!keyboardOpen" class="admin-native-tabs"><button v-for="item in tabs" :key="item.id" :class="{chosen:active===item.id}" hover-class="admin-pressed" @tap="navigate(item)"><StudioGlyph :name="item.icon" :size="21"/><text>{{say(item.label)}}</text></button></view>
 </view>
</template>
