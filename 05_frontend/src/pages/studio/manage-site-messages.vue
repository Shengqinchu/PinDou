<script setup lang="ts">
import {ref} from 'vue';
import {onShow,onHide,onUnload} from '@dcloudio/uni-app';
import StudioAdminShell from '../../components/StudioAdminShell.vue';
import {useStudioNative} from '../../utils/studio-native';
import {adminCall} from '../../utils/studio-admin';
import copy from '../../../../05_studio/src/content/customer-notifications.json';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();const items=ref<any[]>([]),query=ref(''),error=ref(''),busy=ref(false);let active=false,alive=true,timer:ReturnType<typeof setInterval>|undefined;
async function load(){if(busy.value||!active)return;busy.value=true;try{const value=await adminCall<any>('/manage/site-messages',{query:query.value});if(alive)items.value=value.items;}catch{error.value=say(copy.generic_error);}finally{busy.value=false;}}
function open(id:string){uni.navigateTo({url:'/pages/studio/messages?thread='+encodeURIComponent(id)});}
onShow(()=>{active=true;void load();timer=setInterval(()=>void load(),5000);});onHide(()=>{active=false;clearInterval(timer);});onUnload(()=>{alive=false;active=false;clearInterval(timer);});
</script>
<template><StudioAdminShell active="messages" back :title="say(copy.site_messages)" :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" :busy="busy&&!items.length" :error="error" @refresh="load" @language="changeLanguage"><input v-model="query" class="admin-input" :placeholder="say(copy.search)" @confirm="load"/><view style="margin-top:14px"><button v-for="item in items" :key="item.id" class="admin-card admin-stack" style="width:100%;text-align:left;display:flex" @tap="open(item.id)"><view class="admin-row" style="width:100%"><text class="admin-name">{{item.name}}</text><text v-if="item.unread" class="admin-badge">{{item.unread}}</text></view><text class="admin-muted" style="max-height:44px;overflow:hidden">{{item.latest?.body}}</text></button></view></StudioAdminShell></template>
