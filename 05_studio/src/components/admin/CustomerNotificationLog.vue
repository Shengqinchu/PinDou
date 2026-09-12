<script setup lang="ts">
import {ref,watch} from 'vue';
import {useDesk} from '../../admin';
import {say,locale} from '../../state';
import copy from '../../content/customer-notifications.json';
import SlideOver from '../SlideOver.vue';
const {request}=useDesk();const open=ref(false),busy=ref(false),error=ref(''),data=ref<any>();
async function load(){if(busy.value)return;busy.value=true;error.value='';try{data.value=await request('/manage/customer-notifications');}catch{error.value=say(copy.generic_error);}finally{busy.value=false;}}
function label(key:string){return say((copy as Record<string,string[]>)[key]||copy.unknown);}
watch(open,value=>{if(value)void load();});
</script>
<template><button class="desk-link" @click="open=true">{{say(copy.delivery_log)}}</button><SlideOver v-model="open" :title="say(copy.delivery_log)"><div class="customer-notice-log"><button class="text-link" :disabled="busy" @click="load">{{say(copy.refresh)}}</button><p v-if="error" class="form-error">{{error}}</p><template v-if="data"><p v-if="!data.email_configured">{{say(copy.email_missing)}}</p><p v-if="!data.items.length">{{say(copy.delivery_empty)}}</p><article v-for="item in data.items" :key="item.id"><strong>{{label(item.kind+'_title')}}</strong><span>{{item.channel==='email'?say(copy.email):item.channel==='wechat'?'WeChat':say(copy.sms)}} · {{label(item.state)}}</span><small>{{new Date(item.created_at*1000).toLocaleString(locale==='zh'?'zh-CN':'en-CA',{timeZone:'America/Toronto'})}}</small><small v-if="item.reservation_id">{{item.reservation_id}}</small><code v-if="item.error&&['failed','unknown','waiting_config'].includes(item.state)">{{item.error}}</code></article></template></div></SlideOver></template>
<style scoped>.customer-notice-log{display:grid;gap:14px}.customer-notice-log article{display:flex;flex-direction:column;gap:6px;border:1px solid #dce5ea;border-radius:12px;padding:14px;font-size:14px;overflow-wrap:anywhere}.customer-notice-log small{color:#7c8b94}.customer-notice-log code{font-size:11px}.customer-notice-log>.text-link{justify-self:start}</style>
