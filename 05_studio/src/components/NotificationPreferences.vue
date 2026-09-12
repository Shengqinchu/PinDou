<script setup lang="ts">
import {onMounted,ref,watch} from 'vue';
import {say} from '../state';
import copy from '../content/customer-notifications.json';
import {notificationDraft as draft,notificationLoaded,loadNotificationPreferences,saveNotificationPreferences} from '../customer-notifications';
const props=withDefaults(defineProps<{compact?:boolean;method?:string;contact?:string}>(),{compact:false,method:'',contact:''});
const busy=ref(false),error=ref(''),saved=ref(false);
const explain=(e:unknown)=>say((copy as Record<string,string[]>)[(e as any)?.code]||copy.generic_error);
function prefill(){if(props.method==='phone'&&!draft.phone)draft.phone=props.contact;if(props.method==='email'&&!draft.email)draft.email=props.contact;}
async function load(){try{await loadNotificationPreferences();prefill();}catch(e){error.value=explain(e);}}
async function save(){busy.value=true;error.value='';saved.value=false;try{await saveNotificationPreferences();saved.value=true;}catch(e){error.value=explain(e);}finally{busy.value=false;}}
watch([()=>props.method,()=>props.contact],prefill);onMounted(()=>void load());
</script>
<template><section class="notification-preferences"><h3>{{say(copy.title)}}</h3><p>{{say(copy.help)}}</p><div class="notification-choices"><label><input v-model="draft.email_enabled" :disabled="!notificationLoaded" type="checkbox"/>{{say(copy.email)}}</label><label><input v-model="draft.sms_enabled" :disabled="!notificationLoaded" type="checkbox"/>{{say(copy.sms)}}</label></div><label v-if="draft.email_enabled" class="notification-field">{{say(copy.email_address)}}<input v-model="draft.email" type="email" maxlength="180" autocomplete="email"/></label><label v-if="draft.sms_enabled" class="notification-field">{{say(copy.phone)}}<input v-model="draft.phone" type="tel" maxlength="40" autocomplete="tel"/></label><p v-if="error" role="alert" class="form-error">{{error}}</p><p v-if="saved" role="status">{{say(copy.saved)}}</p><button v-if="!compact" type="button" class="text-link" :disabled="busy||!notificationLoaded" @click="save">{{say(busy?copy.saving:copy.save)}}</button></section></template>
<style scoped>.notification-preferences{border-top:1px solid #dce5ea;padding-top:16px;margin-top:16px}.notification-preferences h3{font-size:17px;margin:0 0 8px}.notification-preferences p{font-size:13px;color:#71818b;line-height:1.6;margin:8px 0}.notification-choices{display:flex;flex-wrap:wrap;gap:12px 24px}.notification-choices label{display:flex;align-items:center;gap:8px;min-height:44px;font-size:14px}.notification-field{display:grid;gap:8px;margin:12px 0;font-size:13px}.notification-field input{width:100%;box-sizing:border-box;min-height:44px;border:1px solid #dce5ea;border-radius:9px;padding:10px 12px;font-size:16px;background:white}</style>
