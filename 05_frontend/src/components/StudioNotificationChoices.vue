<script setup lang="ts">
import {onMounted,ref,watch} from 'vue';
import {useUserStore} from '../store/studio-user';
import {notificationDraft as draft,notificationsReady,loadNotifications,saveNotifications,warmWechat,subscribeWechat,wechatPermissionReady,wechatSubscribing,wechatChoices} from '../utils/customer-notifications';
import StudioWechatOutcome from './StudioWechatOutcome.vue';
import copy from '../../../05_studio/src/content/customer-notifications.json';
const props=withDefaults(defineProps<{language:string;compact?:boolean;method?:string;contact?:string}>(),{compact:false,method:'',contact:''});
const user=useUserStore(),busy=ref(false),error=ref('');const say=(value:string[])=>value[props.language==='en'?1:0];
const explain=(e:any)=>say((copy as Record<string,string[]>)[e?.code]||copy.generic_error);
function toggle(field:'email_enabled'|'sms_enabled',event:Event){draft[field]=Boolean((event as unknown as {detail:{value:boolean}}).detail.value);}
function fill(){if(props.method==='email'&&!draft.email&&props.contact){draft.email=props.contact;draft.email_enabled=true;}if(props.method==='phone'&&!draft.phone&&/^(?:\+?1)?[2-9]\d{9}$/.test(props.contact.replace(/[\s().-]/g,''))){draft.phone=props.contact;draft.sms_enabled=true;}}
async function load(){try{await loadNotifications(user.token);fill();void warmWechat(user.token).catch(()=>{});}catch(e){error.value=explain(e);}}
async function save(){busy.value=true;error.value='';try{await saveNotifications(user.token);uni.showToast({title:say(copy.saved),icon:'none'});}catch(e){error.value=explain(e);}finally{busy.value=false;}}
async function subscribe(){busy.value=true;error.value='';try{
 if(!wechatPermissionReady(user.token)){await warmWechat(user.token,true);error.value=say(wechatPermissionReady(user.token)?copy.wechat_tap_again:copy.wechat_unavailable);return;}
 const accepted=await subscribeWechat(user.token);uni.showToast({title:say(accepted?copy.wechat_ready:copy.wechat_declined),icon:'none'});
 }catch(e){error.value=explain(e);}finally{busy.value=false;}}
onMounted(()=>void load());watch([()=>props.method,()=>props.contact],fill);
</script>
<template><view class="native-notification-choices"><text class="studio-native-subtitle">{{say(copy.title)}}</text><text class="studio-native-small studio-native-body">{{say(copy.help)}}</text><view class="native-notification-row"><text>{{say(copy.email)}}</text><switch :disabled="!notificationsReady" :checked="draft.email_enabled" @change="toggle('email_enabled',$event)"/></view><input v-if="draft.email_enabled" v-model="draft.email" class="native-notification-input" :placeholder="say(copy.email_address)" maxlength="180"/><view class="native-notification-row"><text>{{say(copy.sms)}}</text><switch :disabled="!notificationsReady" :checked="draft.sms_enabled" @change="toggle('sms_enabled',$event)"/></view><input v-if="draft.sms_enabled" v-model="draft.phone" class="native-notification-input" :placeholder="say(copy.phone)" maxlength="40"/>
<!-- #ifdef MP-WEIXIN -->
<button class="studio-native-link" :disabled="busy||wechatSubscribing" @tap="subscribe">{{say(copy.wechat)}}</button><text class="studio-native-small studio-native-body">{{say(copy.wechat_help)}}</text><StudioWechatOutcome :language="language" :choices="wechatChoices"/>
<!-- #endif -->
<text v-if="error" class="studio-native-error">{{error}}</text><button v-if="!compact" class="studio-native-primary" :disabled="busy||!notificationsReady" @tap="save">{{say(busy?copy.saving:copy.save)}}</button></view></template>
<style scoped>.native-notification-choices{display:flex;flex-direction:column;gap:10px;margin-top:16px;padding-top:16px;border-top:1px solid #dce5ea}.native-notification-row{display:flex;align-items:center;justify-content:space-between;gap:12px;font-size:14px;min-height:44px}.native-notification-input{box-sizing:border-box;min-height:46px;width:100%;padding:10px 12px;border:1px solid #dce5ea;border-radius:9px;font-size:16px;background:white}</style>
