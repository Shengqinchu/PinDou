<script setup lang="ts">
import {ref} from 'vue';
import {onLoad,onShow,onUnload} from '@dcloudio/uni-app';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import {useStudioNative} from '../../utils/studio-native';
import {miniSession,studioCall,MiniappError} from '../../utils/miniapp-client';
import copy from '../../../../05_studio/src/content/owner-wechat.json';
import workbenchCopy from '../../../../05_studio/src/content/workbench.json';
type OwnerState={bound:boolean;admin?:boolean;enabled?:boolean;template_id?:string;nonce?:string;binding?:{label:string;authorization_available:boolean}};
type Booking={id:string;status:string;name:string;booking:{date:string;start:string;end:string;guests:number}};
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const state=ref<OwnerState>(),candidate=ref<{label:string;expires_at:number}>(),items=ref<Booking[]>([]);
const busy=ref(false),subscribing=ref(false),error=ref(''),note=ref('');
let ticket='',ticketUntil=0,promptUntil=0,scene='',reference='',alive=true,sequence=0;
const words=(key:string)=>say((copy as Record<string,string[]>)[key]||copy.generic_error);
function failed(e:unknown){error.value=words(e instanceof MiniappError?e.code:'generic_error');}
async function refresh(loadBookings=true){
  if(busy.value||subscribing.value||!alive)return;busy.value=true;error.value='';const current=++sequence;
  try{
    if(!ticket||Date.now()>=ticketUntil){const started=Date.now(),proof=await miniSession();if(!alive||current!==sequence)return;ticket=proof.ticket;ticketUntil=started+Math.max(0,proof.expires_in-30)*1000;}
    const preparedAt=Date.now(),value=await studioCall<OwnerState>('/owner-wechat/status',{},ticket,'','GET');
    if(!alive||current!==sequence)return;state.value=value;promptUntil=Math.min(ticketUntil,preparedAt+240000);
    if(scene)candidate.value=await studioCall('/owner-wechat/binding',{scene},ticket,'','GET');
    if(value.bound&&loadBookings){const result=await studioCall<{items:Booking[]}>('/owner-wechat/reservations',reference?{reference}:{},ticket,'','GET');if(alive&&current===sequence)items.value=result.items;}
  }catch(e){if(alive&&current===sequence){if(e instanceof MiniappError&&e.status===401){ticket='';ticketUntil=0;state.value=undefined;}failed(e);}}finally{if(current===sequence)busy.value=false;}
}
async function confirmBinding(){
  if(busy.value||!scene)return;busy.value=true;error.value='';
  try{await studioCall('/owner-wechat/binding',{scene,confirm:true},ticket);scene='';candidate.value=undefined;note.value=words('bound');}
  catch(e){failed(e);}finally{busy.value=false;}
  await refresh();
}
function subscribe(){
  const current=state.value;
  if(busy.value||subscribing.value||!current?.bound||!current.enabled||!current.template_id||!current.nonce)return;
  if(Date.now()>=promptUntil){note.value=words('owner_wechat_prompt_expired');void refresh(false);return;}
  const template=current.template_id,nonce=current.nonce,proof=ticket;subscribing.value=true;note.value='';error.value='';
  // This call must remain directly inside the user's tap handler. Do not put
  // an awaited network request before the WeChat permission sheet.
  // #ifdef MP-WEIXIN
  uni.requestSubscribeMessage({tmplIds:[template],success:async(result)=>{
    const choice=(result as unknown as Record<string,string>)[template];
    try{if(!['accept','reject','ban'].includes(choice))throw new Error();const record=()=>studioCall('/owner-wechat/subscribe',{nonce,result:choice},proof);try{await record();}catch{await record();}note.value=words(choice==='accept'?'subscription_saved':'subscription_denied');}
    catch(e){failed(e);}finally{subscribing.value=false;void refresh(false);}
  },fail:()=>{subscribing.value=false;error.value=words('subscription_denied');}});
  // #endif
  // #ifndef MP-WEIXIN
  subscribing.value=false;error.value=words('wechat_only');
  // #endif
}
function openDesk(){uni.setClipboardData({data:'https://pindoupuppy.com/manage?view=reservations',success:()=>uni.showToast({title:words('copied'),icon:'none'})});}
function openWorkbench(){uni.navigateTo({url:'/pages/studio/manage'});}
onLoad(query=>{scene=typeof query?.scene==='string'?decodeURIComponent(query.scene):'';reference=typeof query?.reservation==='string'?query.reservation:'';});
onShow(()=>void refresh());onUnload(()=>{alive=false;++sequence;});
</script>
<template>
  <StudioShell fitted :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" nav="account" @language="changeLanguage">
    <view class="studio-native-main owner-screen">
      <view class="studio-native-section-head"><text class="studio-native-title">{{words('page_title')}}</text><button class="studio-native-eye" :disabled="busy" :aria-label="words('refresh')" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="refresh"><StudioGlyph name="refresh" :size="21"/></button></view>
      <text v-if="error" class="studio-native-error" role="alert">{{error}}</text><text v-if="note" class="studio-native-body" role="status">{{note}}</text>
      <button v-if="state?.admin" class="studio-native-primary" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="openWorkbench">{{say(workbenchCopy.entry)}}</button>
      <view v-if="candidate" class="owner-permission"><text class="studio-native-subtitle">{{candidate.label}}</text><text class="studio-native-body">{{words('binding_explanation')}}</text><button class="studio-native-primary" :disabled="busy" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="confirmBinding">{{words('confirm_binding')}}</button></view>
      <view v-else-if="state?.bound" class="owner-permission"><text class="studio-native-body">{{state.binding?.label}} · {{words('bound')}}</text><button class="studio-native-primary" :disabled="busy||subscribing||!state.enabled||!state.template_id" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="subscribe">{{words('subscribe')}}</button><text class="studio-native-label">{{words('subscription_note')}}</text><text v-if="!state.template_id" class="studio-native-label">{{words('owner_wechat_template_required')}}</text></view>
      <text v-else-if="state" class="studio-native-body">{{words('unbound')}}</text>
      <template v-if="state?.bound"><view class="studio-native-section-head"><text class="studio-native-subtitle">{{words('pending')}}</text><button class="studio-native-link" @tap="openDesk">{{words('open_desk')}}</button></view><text class="studio-native-label">{{words('timezone')}}</text><scroll-view scroll-y class="owner-bookings"><text v-if="!items.length" class="studio-native-body">{{words('empty')}}</text><view v-for="booking in items" :key="booking.id" class="owner-booking"><text class="studio-native-subtitle">{{booking.name}}</text><text class="studio-native-body">{{booking.booking.date}} · {{booking.booking.start}}–{{booking.booking.end}}</text><text class="studio-native-label">{{words('guests').replace('{count}',String(booking.booking.guests))}}</text></view></scroll-view></template>
    </view>
  </StudioShell>
</template>
<style scoped>
.owner-screen{display:flex;flex-direction:column;gap:14px;min-height:0;flex:1}.owner-permission{display:flex;flex-direction:column;gap:10px;padding:16px;border:1px solid #dce6ec;border-radius:14px;background:#f7fbfd}.owner-permission .studio-native-primary{min-height:44px;margin:0}.owner-bookings{min-height:0;flex:1;overflow:auto}.owner-booking{display:flex;flex-direction:column;gap:7px;padding:15px 0;border-bottom:1px solid #e1e8ec}.owner-screen .studio-native-section-head{margin:0}.owner-screen .studio-native-title{font-size:clamp(23px,6vw,29px)}
@media(max-height:600px){.owner-screen{gap:8px}.owner-permission{padding:10px;gap:6px}.owner-booking{padding:10px 0}.owner-screen .studio-native-title{font-size:22px}}
</style>
