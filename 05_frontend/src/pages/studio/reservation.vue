<script setup lang="ts">
import {computed,ref,watch} from 'vue';
import {onLoad,onShow,onHide,onUnload} from '@dcloudio/uni-app';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import StudioCancel from '../../components/StudioCancel.vue';
import {useUserStore} from '../../store/user';
import {useStudioNative} from '../../utils/studio-native';
import {studioRead,MiniappError} from '../../utils/miniapp-client';
import {studioWords,bookingError,refreshStudioContent,studioProfile,fillWords} from '../../utils/studio-content';
import type {Receipt} from '../../utils/studio-booking';
const user=useUserStore(),{language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const id=ref(''),result=ref<Receipt>(),loading=ref(false),errorCode=ref('');let sequence=0,timer:ReturnType<typeof setInterval>|undefined,alive=true;
const words=(module:Parameters<typeof studioWords>[0],key:string)=>say(studioWords(module,key));
const title=computed(()=>!result.value?'':words('receipt',({pending:'the_host_will_confirm_it_ae62ce',confirmed:'your_visit_is_confirmed_94453d',completed:'thank_you_for_coming_285672',cancelled:'this_reservation_was_cancelled_54b1d2'} as const)[result.value.status]));
const titleEnding=computed(()=>result.value?.status==='confirmed'?words('receipt','see_you_at_the_studio_add3a5'):result.value?.status==='completed'?words('receipt','lets_make_again_soon_12f0b9'):'');
const duration=(value:number)=>fillWords(studioWords('wallet','whole_hours'),language.value,{v0:Math.round(value/60*100)/100});
async function refresh(){
 if(loading.value)return;
 if(!/^VIS-[0-9A-F]{16}$/.test(id.value)){errorCode.value='reservation_not_found';return;}
 if(!user.token)return;
 const seq=++sequence,token=user.token;loading.value=true;errorCode.value='';
 try{const value=await studioRead<Receipt>('/reservations/'+id.value,token);if(alive&&seq===sequence&&token===user.token)result.value=value;}
 catch(e){if(alive&&seq===sequence){errorCode.value=e instanceof MiniappError?e.code:'generic_error';if(e instanceof MiniappError&&[401,403,404].includes(e.status))result.value=undefined;if(e instanceof MiniappError&&e.status===401)user.logout();}}
 finally{if(alive&&seq===sequence)loading.value=false;}
}
function login(){uni.navigateTo({url:'/pages/auth/studio-login'});}
function details(){uni.navigateTo({url:'/pages/studio/details'});}
function phone(){uni.makePhoneCall({phoneNumber:studioProfile.phone.replace(/\s/g,'')});}
function copyWechat(){uni.setClipboardData({data:studioProfile.wechat});}
function changed(value:Receipt){result.value=value;}
watch(()=>user.token,()=>{sequence++;loading.value=false;result.value=undefined;});
onLoad(options=>{id.value=String(options?.id||'');});
onShow(()=>{void refreshStudioContent();void refresh();clearInterval(timer);timer=setInterval(()=>void refresh(),15000);});
onHide(()=>clearInterval(timer));onUnload(()=>{alive=false;sequence++;clearInterval(timer);});
</script>
<template>
 <StudioShell id="studio-shell" :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" nav="bookings" @language="changeLanguage">
  <view class="studio-native-main">
   <template v-if="!user.token"><text class="studio-native-body">{{words('account','account_login_required')}}</text><button class="studio-native-primary" @tap="login">{{words('account','sign_in')}}</button></template>
   <template v-if="result">
    <view class="studio-receipt-heading"><view class="studio-native-result" :class="{'studio-native-result--cancelled':['pending','cancelled'].includes(result.status)}"><StudioGlyph :name="result.status==='pending'?'clock':result.status==='cancelled'?'close':'check'" :size="30"/></view><text class="studio-native-site">{{result.id}}</text><text class="studio-native-title">{{title}}<text v-if="titleEnding" class="studio-home-title-line">{{titleEnding}}</text></text></view>
    <text v-if="result.status==='pending'" class="studio-native-body">{{words('receipt','the_host_will_review_your_plans_as_fec716')}}</text>
    <text v-if="result.status==='pending'" class="studio-booking-urgent">{{words('receipt','if_your_visit_starts_in_less_than_4b8a93')}}</text>
    <view class="studio-native-definition"><view class="studio-native-definition-row"><text class="studio-native-label">{{words('booking','name')}}</text><text>{{result.name}}</text></view><view class="studio-native-definition-row"><text class="studio-native-label">{{words('receipt','visit_time_9fc550')}}</text><text>{{result.booking.date}} · {{result.booking.start}}–{{result.booking.end}}</text><text class="studio-native-label">{{words('receipt','hamilton_local_time_496f95')}}</text></view><view class="studio-native-definition-row"><text class="studio-native-label">{{words('receipt','guests_c77186')}}</text><text>{{fillWords(studioWords('flow','guest_count'),language,{v0:result.booking.guests})}}</text></view><view class="studio-native-definition-row"><text class="studio-native-label">{{words('receipt','experience_cc25a0')}}</text><text>{{words('visit',result.booking.plan==='day'?'a_day_of_making_01d6e2':'by_the_hour_5300b2')}} · {{duration(result.booked_minutes)}}</text></view><view class="studio-native-definition-row"><text class="studio-native-label">{{words('wallet','actual')}}</text><text>{{result.actual_minutes===null?words('wallet','unrecorded'):fillWords(studioWords('wallet','per_guest'),language,{v0:duration(result.actual_minutes),v1:result.actual_guests||result.booking.guests})}}</text></view><text v-if="result.public_note" class="studio-native-body">{{result.public_note}}</text></view>
    <StudioCancel id="booking-cancel" :reservation="result" :language="language" @changed="changed"/>
   </template>
   <text v-if="errorCode" class="studio-native-error">{{say(bookingError(errorCode))}}</text>
   <button v-if="user.token" class="studio-native-secondary" :disabled="loading" @tap="refresh"><view v-if="loading" class="studio-native-progress"/><StudioGlyph v-else name="refresh" :size="18"/>{{words('receipt','refresh_reservation_30af18')}}</button>
   <view class="studio-native-menu"><button class="studio-native-menu-row" @tap="details"><StudioGlyph name="pin"/><text class="studio-native-menu-label">{{words('home','studio_details_7c4089')}}</text><StudioGlyph name="arrow" :size="18"/></button><button class="studio-native-menu-row" @tap="copyWechat"><StudioGlyph name="wechat"/><text class="studio-native-menu-label">{{studioProfile.wechat}}</text><StudioGlyph name="copy" :size="18"/></button><button class="studio-native-menu-row" @tap="phone"><StudioGlyph name="phone"/><text>{{studioProfile.phone}}</text></button></view>
  </view>
 </StudioShell>
</template>
