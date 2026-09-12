<script setup lang="ts">
import {reactive,ref,computed} from 'vue';
import {onLoad,onShow,onUnload} from '@dcloudio/uni-app';
import StudioAdminShell from '../../components/StudioAdminShell.vue';
import StudioCustomerIdentity from '../../components/StudioCustomerIdentity.vue';
import {useStudioNative} from '../../utils/studio-native';
import {adminCall,adminError,goAdmin,confirmAdmin} from '../../utils/studio-admin';
import copy from '../../../../05_studio/src/content/workbench.json';
import walletCopy from '../../../../05_studio/src/content/wallet.json';
import {hoursInput,minutesFromHours} from '../../../../05_studio/src/time-units';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const busy=ref(false),saving=ref(false),error=ref(''),entry=ref<any>(),customer=ref<any>();let ident='',sequence=0,saved='';
const draft=reactive({status:'pending',staff_note:'',public_note:'',actual_hours:'',actual_guests:''});
const states=['pending','confirmed','completed','cancelled'];const labels=computed(()=>states.map(s=>say((copy as Record<string,string[]>)[s])));
async function load(force=false){if(busy.value||(!force&&entry.value&&JSON.stringify(draft)!==saved))return;const n=++sequence;busy.value=true;error.value='';
 try{const result=await adminCall<{items:any[]}>('/manage/reservations',{search:ident,status:'all'});const row=result.items.find(r=>r.id===ident);if(!row)throw new Error();if(n===sequence){entry.value=row;customer.value=undefined;if(row.owner_id)void adminCall<{account:any}>('/manage/members/'+encodeURIComponent(row.owner_id)).then(result=>{if(n===sequence)customer.value=result.account;}).catch(()=>{});Object.assign(draft,{status:row.status,staff_note:row.staff_note||'',public_note:row.public_note||'',actual_hours:hoursInput(row.actual_minutes),actual_guests:row.actual_guests===null?'':String(row.actual_guests)});saved=JSON.stringify(draft);}}
 catch(e){error.value=adminError(e,say);}finally{busy.value=false;}}
async function save(){if(!entry.value||saving.value)return;
 const emptyHours=!draft.actual_hours.trim(),minutes=emptyHours?null:minutesFromHours(draft.actual_hours),guests=draft.actual_guests.trim()?Number(draft.actual_guests):null;
 if(emptyHours!==(guests===null)||(!emptyHours&&(minutes===null||minutes<1||minutes>1440||!Number.isInteger(guests)||Number(guests)<1||Number(guests)>99))){error.value=say(walletCopy.wallet_actual_hours_details_required);return;}
 if(!await confirmAdmin(say(copy.confirm_save),draft.status==='completed'?say(copy.confirm_complete):'',say(copy.confirm),say(copy.cancel)))return;
 const {actual_hours,...fields}=draft;
 saving.value=true;error.value='';try{await adminCall('/manage/reservations/'+ident,{...fields,version:entry.value.version,actual_minutes:minutes,actual_guests:guests},'PATCH');await load(true);uni.showToast({title:say(copy.saved),icon:'none'});}catch(e){error.value=adminError(e,say);}finally{saving.value=false;}}
async function message(){try{const thread=await adminCall<{id:string}>('/manage/messages/threads',{reservation_id:ident},'POST');goAdmin('-conversation','id='+thread.id);}catch(e){error.value=adminError(e,say);}}
function copyContact(){if(entry.value?.payload?.contact)uni.setClipboardData({data:entry.value.payload.contact});}
onLoad(q=>{ident=typeof q?.id==='string'?q.id:'';});onShow(()=>void load());onUnload(()=>{sequence++;});
</script>
<template><StudioAdminShell :title="say(copy.details)" active="reservations" back :language="language" :shell-style="shellStyle" :keyboard-open="keyboardOpen" :busy="busy" :error="error" @refresh="load(true)" @language="changeLanguage">
 <template v-if="entry"><view v-if="customer" class="admin-card"><StudioCustomerIdentity :customer="customer" :language="language"/></view><view class="admin-card admin-stack"><view class="admin-row"><text class="admin-name">{{entry.name}}</text><text class="admin-badge">{{say(copy.guests).replace('{count}',String(entry.booking.guests))}}</text></view><text>{{entry.booking.date}} · {{entry.booking.start}}–{{entry.booking.end}}</text><text class="admin-muted">{{say(copy.timezone)}}</text><button class="admin-secondary" hover-class="admin-pressed" @tap="copyContact">{{entry.payload.contact}}</button><text v-if="entry.payload.notes" class="admin-muted">{{say(copy.customer_note)}} · {{entry.payload.notes}}</text></view>
 <view class="admin-card"><view class="admin-field"><text class="admin-label">{{say(copy.status)}}</text><picker :range="labels" :value="states.indexOf(draft.status)" @change="draft.status=states[Number($event.detail.value)]"><view class="admin-input">{{labels[states.indexOf(draft.status)]}}</view></picker></view><view class="admin-pair"><view class="admin-field"><text class="admin-label">{{say(walletCopy.actual_hours)}}</text><input v-model="draft.actual_hours" type="digit" class="admin-input"/></view><view class="admin-field"><text class="admin-label">{{say(copy.actual_guests)}}</text><input v-model="draft.actual_guests" type="number" class="admin-input"/></view></view><view class="admin-field"><text class="admin-label">{{say(copy.staff_note)}}</text><textarea v-model="draft.staff_note" class="admin-textarea" maxlength="1500" :adjust-position="false"/></view><view class="admin-field"><text class="admin-label">{{say(copy.public_note)}}</text><textarea v-model="draft.public_note" class="admin-textarea" maxlength="1000" :adjust-position="false"/></view></view>
 <view class="admin-pair"><button class="admin-secondary" hover-class="admin-pressed" @tap="message">{{say(copy.messages)}}</button><button v-if="entry.owner_id" class="admin-secondary" hover-class="admin-pressed" @tap="goAdmin('-member','id='+encodeURIComponent(entry.owner_id)+'&reservation='+ident)">{{say(copy.members)}}</button></view></template>
 <template #actions><view v-if="entry" class="admin-dock-row"><button class="admin-primary" :disabled="saving||busy" hover-class="admin-pressed" @tap="save">{{say(saving?copy.saving:copy.save)}}</button></view></template>
 </StudioAdminShell></template>
