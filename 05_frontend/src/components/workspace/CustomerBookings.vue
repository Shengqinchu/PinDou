<script setup lang="ts">
defineOptions({options:{styleIsolation:'shared',virtualHost:true}});
import {ref,watch} from 'vue';
import {onViewShow as onShow,onViewHide as onHide,onViewUnload as onUnload} from '../../utils/studio-view-lifecycle';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import StudioCancel from '../../components/StudioCancel.vue';
import {useUserStore} from '../../store/studio-user';
import {useStudioNative} from '../../utils/studio-native';
import {MiniappError} from '../../utils/miniapp-client';
import {peekStudioSnapshot,readStudioCached} from '../../utils/studio-cache';
import {studioWords,bookingError,refreshStudioContent,fillWords} from '../../utils/studio-content';
import type {Receipt} from '../../utils/studio-booking';
const user=useUserStore(),{language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const items=ref<Receipt[]>([]),page=ref(1),total=ref(0),loading=ref(false),loaded=ref(false),errorCode=ref('');let sequence=0,timer:ReturnType<typeof setInterval>|undefined,alive=true;
type ReservationList={items:Receipt[];total:number};
const words=(module:Parameters<typeof studioWords>[0],key:string)=>say(studioWords(module,key));
const guestCount=(value:number)=>fillWords(studioWords('flow','guest_count'),language.value,{v0:value});
async function refresh(force=false){
 if(loading.value||!user.token)return;
 const seq=++sequence,token=user.token,path='/auth/reservations?page='+page.value,saved=peekStudioSnapshot<ReservationList>(path,token);errorCode.value='';
 if(saved){items.value=saved.data.items;total.value=saved.data.total;loaded.value=true;if(!force&&saved.age<15000)return;}
 loading.value=true;
 try{const value=await readStudioCached<ReservationList>(path,token,15000,force);if(alive&&seq===sequence&&token===user.token){items.value=value.items;total.value=value.total;loaded.value=true;}}
 catch(e){if(alive&&seq===sequence){errorCode.value=e instanceof MiniappError?e.code:'generic_error';if(e instanceof MiniappError&&[401,403].includes(e.status)){items.value=[];user.logout();}}}
 finally{if(alive&&seq===sequence)loading.value=false;}
}
function changePage(delta:number){if(loading.value)return;page.value+=delta;items.value=[];loaded.value=false;void refresh();uni.pageScrollTo({scrollTop:0,duration:0});}
function login(){uni.navigateTo({url:'/pages/auth/studio-login'});}
function visit(){uni.navigateTo({url:'/pages/studio/visit'});}
function detail(id:string){uni.navigateTo({url:'/pages/studio/reservation?id='+encodeURIComponent(id)});}
function changed(result:Receipt){items.value=items.value.map(item=>item.id===result.id?result:item);}
watch(()=>user.token,()=>{sequence++;loading.value=false;loaded.value=false;items.value=[];total.value=0;page.value=1;});
onShow(()=>{void refreshStudioContent();void refresh();clearInterval(timer);timer=setInterval(()=>void refresh(true),15000);});
onHide(()=>clearInterval(timer));onUnload(()=>{alive=false;sequence++;clearInterval(timer);});
</script>
<template>
 <StudioShell id="studio-bookings-pane" fitted embedded :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle">
  <view class="studio-native-main">
   <view class="studio-native-section-head"><text class="studio-native-title">{{words('account','my_reservations')}}</text><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-eye" :disabled="loading||!user.token" :aria-label="words('wallet','refresh')" @tap="refresh(true)"><view v-if="loading" class="studio-native-progress"/><StudioGlyph v-else name="refresh" :size="21"/></button></view>
   <template v-if="!user.token"><text class="studio-native-body">{{words('account','account_login_required')}}</text><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-primary" hover-class="studio-native-pressed" @tap="login">{{words('account','sign_in')}}</button></template>
   <template v-else>
    <text v-if="errorCode" class="studio-native-error">{{say(bookingError(errorCode))}}</text>
    <text v-if="loading&&!loaded" class="studio-native-body">{{words('receipt','loading_your_reservation_9f91f7')}}</text>
    <text v-else-if="!items.length&&!errorCode" class="studio-native-body">{{words('account','no_reservations')}}</text>
    <view v-for="item in items" :key="item.id" class="studio-booking-card"><button :hover-stay-time="180" :hover-start-time="0" class="studio-booking-open" hover-class="studio-native-pressed" @tap="detail(item.id)"><view class="studio-booking-card-head"><text class="studio-plan-name">{{item.booking.date}}</text><text class="studio-booking-status" :class="'studio-booking-status--'+item.status">{{words('cancellation',item.status)}}</text></view><text>{{item.booking.start}}–{{item.booking.end}}</text><view class="studio-booking-summary"><text class="studio-native-body">{{guestCount(item.booking.guests)}} · {{words('visit',item.booking.plan==='day'?'a_day_of_making_01d6e2':'by_the_hour_5300b2')}}</text><StudioGlyph name="arrow" :size="18"/></view></button><StudioCancel :id="'cancel-'+item.id" :reservation="item" :language="language" @changed="changed"/></view>
    <view v-if="total>30" class="studio-booking-pagination"><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-secondary" :disabled="loading||page===1" @tap="changePage(-1)">{{words('wallet','previous')}}</button><text>{{page}}</text><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-secondary" :disabled="loading||page*30>=total" @tap="changePage(1)">{{words('wallet','next')}}</button></view>
   </template>
   <button :hover-stay-time="180" :hover-start-time="0" class="studio-native-primary" hover-class="studio-native-pressed" @tap="visit"><text class="studio-native-primary-label">{{words('home','come_create_2eee81')}}</text><StudioGlyph name="arrow"/></button>
  </view>
 </StudioShell>
</template>
