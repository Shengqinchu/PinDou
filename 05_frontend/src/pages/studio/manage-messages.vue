<script setup lang="ts">
import {ref} from 'vue';
import {onShow,onHide,onUnload} from '@dcloudio/uni-app';
import StudioAdminShell from '../../components/StudioAdminShell.vue';
import {useStudioNative} from '../../utils/studio-native';
import {adminCall,adminError,goAdmin} from '../../utils/studio-admin';
import copy from '../../../../05_studio/src/content/messaging.json';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const data=ref<any>(),busy=ref(false),error=ref(''),query=ref(''),unread=ref(false),adding=ref(false),phone=ref(''),name=ref('');let active=false,timer:ReturnType<typeof setInterval>|undefined;
async function load(more=false){if(busy.value)return;busy.value=true;error.value='';try{const result=await adminCall<any>('/manage/messages/threads',{query:query.value,unread:unread.value,...(more&&data.value?.next_cursor?{cursor:data.value.next_cursor}:{})});if(active)data.value=more&&data.value?{...result,items:[...data.value.items,...result.items]}:result;}catch(e){error.value=adminError(e,say);}finally{busy.value=false;}}
async function create(){if(busy.value||!phone.value.trim())return;busy.value=true;error.value='';try{const thread=await adminCall<{id:string}>('/manage/messages/threads',{phone:phone.value,name:name.value},'POST');adding.value=false;phone.value='';name.value='';goAdmin('-conversation','id='+thread.id);}catch(e){error.value=adminError(e,say);}finally{busy.value=false;}}
function stop(){active=false;clearInterval(timer);timer=undefined;}
onShow(()=>{active=true;void load();clearInterval(timer);timer=setInterval(()=>{if(active)void load();},5000);});onHide(stop);onUnload(stop);
</script>
<template><StudioAdminShell :title="say(copy.title)" active="messages" :language="language" :shell-style="shellStyle" :keyboard-open="keyboardOpen" :busy="busy" :error="error" @refresh="load()" @language="changeLanguage">
 <input v-model="query" class="admin-input" :placeholder="say(copy.search)" confirm-type="search" @confirm="load()"/>
 <view class="admin-filters"><button :class="{chosen:!unread}" @tap="unread=false;load()">{{say(copy.all)}}</button><button :class="{chosen:unread}" @tap="unread=true;load()">{{say(copy.unread)}}</button><button @tap="adding=!adding">+ {{say(copy.new_conversation)}}</button></view>
 <view v-if="adding" class="admin-card admin-stack"><input v-model="name" class="admin-input" :placeholder="say(copy.name)" maxlength="80"/><input v-model="phone" class="admin-input" type="text" :placeholder="say(copy.phone)" maxlength="40"/><text class="admin-muted">{{say(copy.number_hint)}}</text><text class="admin-muted">{{say(copy.sync_hint)}}</text><button class="admin-primary" :disabled="busy||!phone.trim()" @tap="create">{{say(copy.connect)}}</button></view>
 <text v-if="data?.bridge" class="admin-muted">{{say(data.bridge.online?copy.online:copy.offline)}} · {{data.bridge.sender}}</text>
 <view class="native-message-threads"><button v-for="thread in data?.items||[]" :key="thread.id" class="admin-card admin-stack native-message-thread" hover-class="admin-pressed" @tap="goAdmin('-conversation','id='+thread.id)"><view class="admin-row"><text class="admin-name">{{thread.name||thread.phone}}</text><text v-if="thread.unread" class="native-message-badge">{{thread.unread}}</text></view><text class="admin-muted">{{thread.phone}}</text><text class="native-message-preview">{{thread.latest?.content||say(copy.no_messages)}}</text></button></view><view v-if="!busy&&!data?.items.length" class="admin-empty">{{say(copy.empty)}}</view><button v-if="data?.next_cursor" class="admin-secondary" :disabled="busy" @tap="load(true)">{{say(copy.more_customers)}}</button>
 </StudioAdminShell></template>
<style scoped>.native-message-threads{margin-top:12px}.native-message-thread{display:flex;width:100%;text-align:left}.native-message-thread>.admin-row{width:100%}.native-message-badge{font-size:12px;background:#658da6;color:white;border-radius:12px;min-width:20px;text-align:center;padding:2px 5px}.native-message-preview{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;font-size:13px;color:#6f808b}</style>
