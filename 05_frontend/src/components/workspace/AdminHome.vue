<script setup lang="ts">
defineOptions({options:{styleIsolation:'shared'}});
import {ref} from 'vue';
import {onViewShow as onShow,onViewHide as onHide,onViewUnload as onUnload} from '../../utils/studio-view-lifecycle';
import StudioAdminShell from '../../components/StudioAdminShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import {useStudioNative} from '../../utils/studio-native';
import {adminCall,adminError,goAdmin} from '../../utils/studio-admin';
import {adminView} from '../../utils/studio-admin-cache';
import copy from '../../../../05_studio/src/content/workbench.json';
import notices from '../../../../05_studio/src/content/customer-notifications.json';
import business from '../../../../05_studio/src/content/business.json';
import {money,type FinanceSummary} from '../../../../05_studio/src/business-model';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
type Summary={today:string;pending:number;visits:number;unread:number;finance:FinanceSummary};
const view=adminView<{data?:Summary}>('home');
const busy=ref(false),error=ref(''),data=ref<Summary|undefined>(view.snapshot?.data);
let alive=true;
const remember=()=>view.save({data:data.value});
async function refresh(force=true){if(!view.valid())data.value=undefined;if(busy.value||(!force&&view.fresh()))return;busy.value=true;error.value='';const revision=view.begin();try{const value=await adminCall<Summary>('/manage/desk-summary');if(alive){data.value=value;view.loaded(revision);remember();}}catch(e){error.value=adminError(e,say);if(!view.valid())data.value=undefined;}finally{busy.value=false;}}
const entries=[{page:'-notifications',label:notices.delivery_log,icon:'info'},{page:'-reservations',label:copy.reservations,icon:'calendar'},{page:'-messages',label:copy.messages,icon:'wechat'},{page:'-members',label:copy.members,icon:'user'},{page:'-finance',label:copy.finance,icon:'grid'},{page:'-calendar',label:copy.calendar,icon:'calendar'}];
function openAlerts(){uni.navigateTo({url:'/pages/studio/owner'});}
onShow(()=>void refresh(false));onHide(remember);onUnload(()=>{remember();alive=false;});
</script>
<template>
 <StudioAdminShell :title="say(copy.title)" :language="language" :shell-style="shellStyle" :keyboard-open="keyboardOpen" :busy="busy&&!data" :error="error" @refresh="refresh()" @language="changeLanguage">
  <template v-if="data"><view class="admin-home-metrics"><button class="admin-card" hover-class="admin-pressed" @tap="goAdmin('-reservations')"><text class="admin-muted">{{say(copy.pending)}}</text><text class="admin-home-number">{{data.pending}}</text></button><button class="admin-card" hover-class="admin-pressed" @tap="goAdmin('-reservations','date='+data.today+'&status=all')"><text class="admin-muted">{{say(copy.today)}}</text><text class="admin-home-number">{{data.visits}}</text></button><button class="admin-card" hover-class="admin-pressed" @tap="goAdmin('-messages')"><text class="admin-muted">{{say(copy.unread)}}</text><text class="admin-home-number">{{data.unread}}</text></button></view>
  <view class="admin-card admin-stack"><view class="admin-row"><text class="admin-name">{{say(business.month)}} · {{say(business.title)}}</text><text class="admin-muted">{{data.today}}</text></view><view class="admin-pair"><view class="admin-stack"><text class="admin-muted">{{say(business.income)}}</text><text class="admin-name">{{money(data.finance.income_cents)}}</text></view><view class="admin-stack"><text class="admin-muted">{{say(business.expense)}}</text><text class="admin-name">{{money(data.finance.expense_cents)}}</text></view></view><text v-if="data.finance.needs_amount" class="admin-muted">{{say(business.pending_count).replace('{count}',String(data.finance.needs_amount))}}</text></view>
  <view class="admin-home-links"><button v-for="entry in entries" :key="entry.page" class="admin-card admin-row" hover-class="admin-pressed" @tap="goAdmin(entry.page)"><StudioGlyph :name="entry.icon"/><text>{{say(entry.label)}}</text><StudioGlyph name="arrow" :size="18"/></button><button class="admin-card admin-row" hover-class="admin-pressed" @tap="openAlerts"><StudioGlyph name="info"/><text>{{say(copy.alerts)}}</text><StudioGlyph name="arrow" :size="18"/></button></view></template>
 </StudioAdminShell>
</template>
<style scoped>
.admin-home-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.admin-home-metrics .admin-card{display:flex;flex-direction:column;gap:8px;align-items:flex-start;padding:15px 12px}.admin-home-number{font-size:30px;line-height:1.2}.admin-home-links{display:grid;gap:10px;grid-template-columns:repeat(2,minmax(0,1fr))}.admin-home-links .admin-card{margin:0;min-height:76px;padding:14px 12px;gap:8px;text-align:left}.admin-home-links text{flex:1;font-size:14px}.admin-home-metrics .admin-muted{font-size:11px}@media(max-width:350px){.admin-home-links{grid-template-columns:1fr}.admin-home-links .admin-card{min-height:54px}}@media(min-width:800px){.admin-home-links{grid-template-columns:repeat(3,minmax(0,1fr))}}
</style>
