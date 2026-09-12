<script setup lang="ts">
import {ref} from 'vue';
import {onShow,onHide,onUnload} from '@dcloudio/uni-app';
import StudioAdminShell from '../../components/StudioAdminShell.vue';
import {useStudioNative} from '../../utils/studio-native';
import {adminCall,adminError} from '../../utils/studio-admin';
import {adminView} from '../../utils/studio-admin-cache';
import copy from '../../../../05_studio/src/content/customer-notifications.json';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const view=adminView<{data:any}>('notification-history'),data=ref<any>(view.snapshot?.data),busy=ref(false),error=ref('');let active=false,alive=true,timer:ReturnType<typeof setInterval>|undefined;
const label=(key:string)=>say((copy as Record<string,string[]>)[key]||copy.unknown);
async function load(){if(busy.value)return;busy.value=true;try{const value=await adminCall('/manage/customer-notifications');if(alive){data.value=value;view.save({data:value});error.value='';}}catch(e){error.value=adminError(e,say);}finally{busy.value=false;}}
onShow(()=>{active=true;if(!view.valid())data.value=undefined;void load();clearInterval(timer);timer=setInterval(()=>{if(active)void load();},10000);});onHide(()=>{active=false;clearInterval(timer);});onUnload(()=>{alive=false;active=false;clearInterval(timer);});
</script>
<template><StudioAdminShell back :title="say(copy.delivery_log)" :language="language" :shell-style="shellStyle" :keyboard-open="keyboardOpen" :busy="busy&&!data" :error="error" @language="changeLanguage" @refresh="load"><template v-if="data"><text v-if="!data.email_configured" class="admin-muted">{{say(copy.email_missing)}}</text><text v-if="!data.items.length" class="admin-empty">{{say(copy.delivery_empty)}}</text><view v-for="item in data.items" :key="item.id" class="admin-card admin-stack"><text class="admin-name">{{label(item.kind+'_title')}}</text><text>{{item.channel==='email'?say(copy.email):item.channel==='wechat'?'WeChat':say(copy.sms)}} · {{label(item.state)}}</text><text class="admin-muted">{{new Date(item.created_at*1000).toISOString().replace('T',' ').slice(0,16)}} UTC</text><text v-if="item.reservation_id" class="admin-muted">{{item.reservation_id}}</text></view></template></StudioAdminShell></template>
