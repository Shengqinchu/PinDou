<script setup lang="ts">
import {reactive,ref,computed,watch} from 'vue';
import {onLoad,onShow,onUnload} from '@dcloudio/uni-app';
import StudioAdminShell from '../../components/StudioAdminShell.vue';
import StudioCustomerIdentity from '../../components/StudioCustomerIdentity.vue';
import StudioOwnerSaveConfirm from '../../components/StudioOwnerSaveConfirm.vue';
import {useStudioNative} from '../../utils/studio-native';
import {adminCall,adminError,goAdmin,confirmAdmin} from '../../utils/studio-admin';
import {prepareOwnerSubscription,ownerSubscriptionReady,requestOwnerSubscription,type OwnerSubscription,type SubscriptionResult} from '../../utils/owner-subscription';
import alertCopy from '../../../../05_studio/src/content/owner-wechat.json';
import copy from '../../../../05_studio/src/content/workbench.json';
import walletCopy from '../../../../05_studio/src/content/wallet.json';
import {hoursInput,minutesFromHours} from '../../../../05_studio/src/time-units';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const busy=ref(false),saving=ref(false),error=ref(''),entry=ref<any>(),customer=ref<any>();let ident='',sequence=0,saved='';
const alertPrompt=ref<OwnerSubscription|null>(null),savePrompt=ref(false),alertNote=ref('');
let alive=true,alertSequence=0,alertRequest:Promise<SubscriptionResult>|null=null;
let saveIntent:{id:string;data:Record<string,unknown>}|null=null;
async function prepareAlerts(){
 if(alertRequest||!alive)return;const n=++alertSequence;alertPrompt.value=null;
 try{const next=await prepareOwnerSubscription();if(alive&&n===alertSequence)alertPrompt.value=next;}catch{}
}
const draft=reactive({status:'pending',staff_note:'',public_note:'',actual_hours:'',actual_guests:''});
const states=['pending','confirmed','completed','cancelled'];const labels=computed(()=>states.map(s=>say((copy as Record<string,string[]>)[s])));
async function load(force=false){if(busy.value||(!force&&entry.value&&JSON.stringify(draft)!==saved))return;const n=++sequence;busy.value=true;error.value='';
 try{const result=await adminCall<{items:any[]}>('/manage/reservations',{search:ident,status:'all'});const row=result.items.find(r=>r.id===ident);if(!row)throw new Error();if(n===sequence){entry.value=row;customer.value=undefined;if(row.owner_id)void adminCall<{account:any}>('/manage/members/'+encodeURIComponent(row.owner_id)).then(result=>{if(n===sequence)customer.value=result.account;}).catch(()=>{});Object.assign(draft,{status:row.status,staff_note:row.staff_note||'',public_note:row.public_note||'',actual_hours:hoursInput(row.actual_minutes),actual_guests:row.actual_guests==null?'':String(row.actual_guests)});saved=JSON.stringify(draft);}}
 catch(e){error.value=adminError(e,say);}finally{busy.value=false;}}
async function save(){if(!entry.value||saving.value)return;
 const completing=draft.status==='completed',minutes=completing?minutesFromHours(draft.actual_hours):null,guests=draft.actual_guests.trim()?Number(draft.actual_guests):null;
 if(completing&&(minutes===null||minutes<1||minutes>1440||!Number.isInteger(guests)||Number(guests)<1||Number(guests)>99)){error.value=say(walletCopy.wallet_actual_hours_details_required);return;}
 const {actual_hours,actual_guests,...fields}=draft;
 saveIntent={id:ident,data:{...fields,version:entry.value.version,...(completing?{actual_minutes:minutes,actual_guests:guests}:{})}};
 if(!alertRequest&&ownerSubscriptionReady(alertPrompt.value)){savePrompt.value=true;return;}
 if(!await confirmAdmin(say(copy.confirm_save),completing?say(copy.confirm_complete):'',say(copy.confirm),say(copy.cancel))){saveIntent=null;return;}
 await persistSave();}
function confirmSave(subscribe:boolean){
 if(saving.value||!saveIntent)return;
 savePrompt.value=false;alertNote.value='';
 let actionFinished:()=>void=()=>{};
 const action=new Promise<void>(resolve=>{actionFinished=resolve;});
 if(subscribe){
  // A visible confirmation button is the real user gesture for WeChat.
  const pending=requestOwnerSubscription(alertPrompt.value,action);alertRequest=pending;
  void pending.then(result=>{if(alive)alertNote.value=say(result==='accept'?alertCopy.subscription_saved:result==='reject'||result==='ban'?alertCopy.subscription_denied:alertCopy.save_alert_unavailable);}).finally(()=>{if(alertRequest===pending)alertRequest=null;void prepareAlerts();});
 }
 void persistSave().finally(actionFinished);
}
function dismissSave(){savePrompt.value=false;saveIntent=null;}
async function persistSave(){
 const intent=saveIntent;if(!intent||saving.value)return;saveIntent=null;saving.value=true;error.value='';
 try{await adminCall('/manage/reservations/'+intent.id,intent.data,'PATCH');if(alive){await load(true);uni.showToast({title:say(copy.saved),icon:'none'});}}
 catch(e){if(alive)error.value=adminError(e,say);}finally{saving.value=false;}
}
watch(()=>draft.status,()=>{error.value='';});
async function message(){try{const thread=await adminCall<{id:string}>('/manage/messages/threads',{reservation_id:ident},'POST');goAdmin('-conversation','id='+thread.id);}catch(e){error.value=adminError(e,say);}}
function copyContact(){if(entry.value?.payload?.contact)uni.setClipboardData({data:entry.value.payload.contact});}
onLoad(q=>{ident=typeof q?.id==='string'?q.id:'';});onShow(()=>{void load();void prepareAlerts();});onUnload(()=>{alive=false;sequence++;alertSequence++;});
</script>
<template><StudioAdminShell :title="say(copy.details)" active="reservations" back :language="language" :shell-style="shellStyle" :keyboard-open="keyboardOpen" :busy="busy" :error="error" @refresh="load(true)" @language="changeLanguage">
 <template v-if="entry"><view v-if="customer" class="admin-card"><StudioCustomerIdentity :customer="customer" :language="language"/></view><view class="admin-card admin-stack"><view class="admin-row"><text class="admin-name">{{entry.name}}</text><text class="admin-badge">{{say(copy.guests).replace('{count}',String(entry.booking.guests))}}</text></view><text>{{entry.booking.date}} · {{entry.booking.start}}–{{entry.booking.end}}</text><text class="admin-muted">{{say(copy.timezone)}}</text><button class="admin-secondary" hover-class="admin-pressed" @tap="copyContact">{{entry.payload.contact}}</button><text v-if="entry.payload.notes" class="admin-muted">{{say(copy.customer_note)}} · {{entry.payload.notes}}</text></view>
 <view class="admin-card"><view class="admin-field"><text class="admin-label">{{say(copy.status)}}</text><picker :range="labels" :value="states.indexOf(draft.status)" @change="draft.status=states[Number($event.detail.value)]"><view class="admin-input">{{labels[states.indexOf(draft.status)]}}</view></picker></view><view v-if="draft.status==='completed'" class="admin-pair"><view class="admin-field"><text class="admin-label">{{say(walletCopy.actual_hours)}}</text><input v-model="draft.actual_hours" type="digit" class="admin-input"/></view><view class="admin-field"><text class="admin-label">{{say(copy.actual_guests)}}</text><input v-model="draft.actual_guests" type="number" class="admin-input"/></view></view><view class="admin-field"><text class="admin-label">{{say(copy.staff_note)}}</text><textarea v-model="draft.staff_note" class="admin-textarea" maxlength="1500" :adjust-position="false"/></view><view class="admin-field"><text class="admin-label">{{say(copy.public_note)}}</text><textarea v-model="draft.public_note" class="admin-textarea" maxlength="1000" :adjust-position="false"/></view></view>
 <view class="admin-pair"><button class="admin-secondary" hover-class="admin-pressed" @tap="message">{{say(copy.messages)}}</button><button v-if="entry.owner_id" class="admin-secondary" hover-class="admin-pressed" @tap="goAdmin('-member','id='+encodeURIComponent(entry.owner_id)+'&reservation='+ident)">{{say(copy.members)}}</button></view></template>
 <template #actions><text v-if="alertNote" class="admin-muted" role="status">{{alertNote}}</text><view v-if="entry" class="admin-dock-row"><button class="admin-primary" :disabled="saving||busy||savePrompt" hover-class="admin-pressed" @tap="save">{{say(saving?copy.saving:copy.save)}}</button></view><StudioOwnerSaveConfirm v-if="savePrompt" :language="language" :completed="draft.status==='completed'" @confirm="confirmSave" @dismiss="dismissSave"/></template>
 </StudioAdminShell></template>
