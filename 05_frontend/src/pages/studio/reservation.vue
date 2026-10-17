<script setup lang="ts">
import {pressTo} from '../../utils/press';
import {computed,ref,watch} from 'vue';
import {onLoad,onShow,onHide,onUnload} from '@dcloudio/uni-app';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import StudioCancel from '../../components/StudioCancel.vue';
import StudioEditReservation from '../../components/StudioEditReservation.vue';
import StudioWechatOutcome from '../../components/StudioWechatOutcome.vue';
import {bookingWechatChoices} from '../../utils/customer-notifications';
import notices from '../../../../05_studio/src/content/customer-notifications.json';
import {useUserStore} from '../../store/studio-user';
import {useStudioNative} from '../../utils/studio-native';
import {MiniappError} from '../../utils/miniapp-client';
import {peekStudioSnapshot,readStudioCached} from '../../utils/studio-cache';
import {studioPlanWords,studioWords,bookingError,refreshStudioContent,studioProfile,fillWords} from '../../utils/studio-content';
import type {Receipt} from '../../utils/studio-booking';
const user=useUserStore(),{language,width,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const id=ref(''),result=ref<Receipt>(),loading=ref(false),errorCode=ref('');let sequence=0,timer:ReturnType<typeof setInterval>|undefined,alive=true;
const wechatChoices=computed(()=>bookingWechatChoices(user.token,id.value));
const words=(module:Parameters<typeof studioWords>[0],key:string)=>say(studioWords(module,key));
const title=computed(()=>!result.value?'':words('receipt',({pending:'the_host_will_confirm_it_ae62ce',confirmed:'your_visit_is_confirmed_94453d',completed:'thank_you_for_coming_285672',cancelled:'this_reservation_was_cancelled_54b1d2'} as const)[result.value.status]));
const titleEnding=computed(()=>result.value?.status==='confirmed'?words('receipt','see_you_at_the_studio_add3a5'):result.value?.status==='completed'?words('receipt','lets_make_again_soon_12f0b9'):'');
const duration=(value:number)=>fillWords(studioWords('wallet','whole_hours'),language.value,{v0:Math.round(value/60*100)/100});
async function refresh(force=false){
 if(loading.value)return;
 if(!/^VIS-[0-9A-F]{16}$/.test(id.value)){errorCode.value='reservation_not_found';return;}
 if(!user.token)return;
 const seq=++sequence,token=user.token,path='/reservations/'+id.value,saved=peekStudioSnapshot<Receipt>(path,token);errorCode.value='';
 if(saved){result.value=saved.data;if(!force&&saved.age<15000)return;}
 loading.value=true;
 try{const value=await readStudioCached<Receipt>(path,token,15000,force);if(alive&&seq===sequence&&token===user.token)result.value=value;}
 catch(e){if(alive&&seq===sequence){errorCode.value=e instanceof MiniappError?e.code:'generic_error';if(e instanceof MiniappError&&[401,403,404].includes(e.status))result.value=undefined;if(e instanceof MiniappError&&e.status===401)user.logout();}}
 finally{if(alive&&seq===sequence)loading.value=false;}
}
function login(){pressTo('/pages/auth/studio-login');}
function details(){pressTo('/pages/studio/details');}
function notifications(){pressTo('/pages/studio/notifications');}
function phone(){uni.makePhoneCall({phoneNumber:studioProfile.phone.replace(/\s/g,'')});}
function copyWechat(){uni.setClipboardData({data:studioProfile.wechat});}
function changed(value:Receipt){sequence++;loading.value=false;result.value=value;}
watch(()=>user.token,()=>{sequence++;loading.value=false;result.value=undefined;});
onLoad(options=>{id.value=String(options?.id||'');});
onShow(()=>{void refreshStudioContent();void refresh();clearInterval(timer);timer=setInterval(()=>void refresh(true),15000);});
onHide(()=>clearInterval(timer));onUnload(()=>{alive=false;sequence++;clearInterval(timer);});
</script>
<template>
 <StudioShell id="studio-shell" fitted :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" nav="bookings" @language="changeLanguage">
  <view class="studio-native-main studio-receipt">
   <template v-if="!user.token"><text class="studio-native-body">{{words('account','account_login_required')}}</text><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-primary" @tap="login">{{words('account','sign_in')}}</button></template>
   <template v-if="result">
    <view class="studio-receipt-heading"><text class="studio-native-title">{{title}}<text v-if="titleEnding" class="studio-home-title-line">{{titleEnding}}</text></text><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-eye" :disabled="loading" :aria-label="words('receipt','refresh_reservation_30af18')" @tap="refresh(true)"><view v-if="loading" class="studio-native-progress"/><StudioGlyph v-else name="refresh" :size="20"/></button></view>
    <text v-if="result.status==='pending'" class="studio-native-body">{{words('receipt','the_host_will_review_your_plans_as_fec716')}}</text>
    <text v-if="result.status==='pending'" class="studio-booking-urgent">{{words('receipt','if_your_visit_starts_in_less_than_4b8a93')}}</text>
    <!-- #ifdef MP-WEIXIN -->
    <StudioWechatOutcome v-if="wechatChoices" :language="language" :choices="wechatChoices"/>
    <!-- #endif -->
    <view class="studio-native-definition"><view class="studio-native-definition-row"><text class="studio-native-label">{{words('booking','name')}}</text><text>{{result.name}}</text></view><view class="studio-native-definition-row"><text class="studio-native-label">{{words('receipt','visit_time_9fc550')}}</text><text>{{result.booking.date}} · {{result.booking.start}}–{{result.booking.end}}</text><text class="studio-native-label">{{words('receipt','hamilton_local_time_496f95')}}</text></view><view class="studio-native-definition-row"><text class="studio-native-label">{{words('receipt','guests_c77186')}}</text><text>{{fillWords(studioWords('flow','guest_count'),language,{v0:result.booking.guests})}}</text></view><view class="studio-native-definition-row"><text class="studio-native-label">{{words('receipt','experience_cc25a0')}}</text><text>{{say(studioPlanWords(result.booking.plan))}} · {{duration(result.booked_minutes)}}</text></view><view class="studio-native-definition-row"><text class="studio-native-label">{{words('wallet','actual')}}</text><text>{{result.actual_minutes===null?words('wallet','unrecorded'):fillWords(studioWords('wallet','per_guest'),language,{v0:duration(result.actual_minutes),v1:result.actual_guests||result.booking.guests})}}</text></view><text v-if="result.public_note" class="studio-native-body">{{result.public_note}}</text></view>
    <text v-if="result.previous_visit" class="studio-native-small">{{words('edit','previous_visit')}} · {{result.previous_visit.booking.date}} · {{duration(result.previous_visit.actual_minutes||0)}}</text>
    <view class="studio-receipt-actions"><StudioEditReservation :reservation="result" :language="language" :width="width" @changed="changed"/><StudioCancel id="booking-cancel" :reservation="result" :language="language" @changed="changed"/><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-link" @tap="details"><StudioGlyph name="pin" :size="18"/>{{words('home','studio_details_7c4089')}}</button></view>
   </template>
   <view v-if="result" class="studio-receipt-actions"><button class="studio-native-link" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="notifications">{{say(notices.notification_settings)}}</button></view>
   <text v-if="errorCode" class="studio-native-error">{{say(bookingError(errorCode))}}</text>
   <button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" v-if="user.token&&!result" class="studio-native-secondary" :disabled="loading" @tap="refresh(true)"><view v-if="loading" class="studio-native-progress"/><StudioGlyph v-else name="refresh" :size="18"/>{{words('receipt','refresh_reservation_30af18')}}</button>
   <view class="studio-contact-shortcuts"><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-secondary" @tap="copyWechat"><StudioGlyph name="wechat" :size="18"/><text>{{studioProfile.wechat}}</text></button><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-secondary" @tap="phone"><StudioGlyph name="phone" :size="18"/><text>{{studioProfile.phone}}</text></button></view>
  </view>
 </StudioShell>
</template>
