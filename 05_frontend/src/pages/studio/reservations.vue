<script setup lang="ts">
import {ref,watch} from 'vue';
import {onShow,onHide,onUnload} from '@dcloudio/uni-app';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import StudioCancel from '../../components/StudioCancel.vue';
import {useUserStore} from '../../store/user';
import {useStudioNative} from '../../utils/studio-native';
import {studioRead,MiniappError} from '../../utils/miniapp-client';
import {studioWords,bookingError,refreshStudioContent,fillWords} from '../../utils/studio-content';
import type {Receipt} from '../../utils/studio-booking';
const user=useUserStore(),{language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const items=ref<Receipt[]>([]),page=ref(1),total=ref(0),loading=ref(false),errorCode=ref('');let sequence=0,timer:ReturnType<typeof setInterval>|undefined,alive=true;
const words=(module:Parameters<typeof studioWords>[0],key:string)=>say(studioWords(module,key));
const guestCount=(value:number)=>fillWords(studioWords('flow','guest_count'),language.value,{v0:value});
async function refresh(){
 if(loading.value||!user.token)return;
 const seq=++sequence,token=user.token;loading.value=true;errorCode.value='';
 try{const value=await studioRead<{items:Receipt[];total:number}>('/auth/reservations?page='+page.value,token);if(alive&&seq===sequence&&token===user.token){items.value=value.items;total.value=value.total;}}
 catch(e){if(alive&&seq===sequence){errorCode.value=e instanceof MiniappError?e.code:'generic_error';if(e instanceof MiniappError&&[401,403].includes(e.status)){items.value=[];user.logout();}}}
 finally{if(alive&&seq===sequence)loading.value=false;}
}
function changePage(delta:number){if(loading.value)return;page.value+=delta;items.value=[];void refresh();uni.pageScrollTo({scrollTop:0,duration:0});}
function login(){uni.navigateTo({url:'/pages/auth/studio-login'});}
function visit(){uni.navigateTo({url:'/pages/studio/visit'});}
function detail(id:string){uni.navigateTo({url:'/pages/studio/reservation?id='+encodeURIComponent(id)});}
function changed(result:Receipt){items.value=items.value.map(item=>item.id===result.id?result:item);}
watch(()=>user.token,()=>{sequence++;loading.value=false;items.value=[];total.value=0;page.value=1;});
onShow(()=>{void refreshStudioContent();void refresh();clearInterval(timer);timer=setInterval(()=>void refresh(),15000);});
onHide(()=>clearInterval(timer));onUnload(()=>{alive=false;sequence++;clearInterval(timer);});
</script>
<template>
 <StudioShell id="studio-shell" fitted :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" nav="bookings" @language="changeLanguage">
  <view class="studio-native-main">
   <view class="studio-native-section-head"><text class="studio-native-title">{{words('account','my_reservations')}}</text><button class="studio-native-eye" :disabled="loading||!user.token" :aria-label="words('wallet','refresh')" @tap="refresh"><view v-if="loading" class="studio-native-progress"/><StudioGlyph v-else name="refresh" :size="21"/></button></view>
   <template v-if="!user.token"><text class="studio-native-body">{{words('account','account_login_required')}}</text><button class="studio-native-primary" hover-class="studio-native-pressed" @tap="login">{{words('account','sign_in')}}</button></template>
   <template v-else>
    <text v-if="errorCode" class="studio-native-error">{{say(bookingError(errorCode))}}</text>
    <text v-if="loading&&!items.length" class="studio-native-body">{{words('receipt','loading_your_reservation_9f91f7')}}</text>
    <text v-else-if="!items.length&&!errorCode" class="studio-native-body">{{words('account','no_reservations')}}</text>
    <view v-for="item in items" :key="item.id" class="studio-booking-card"><button class="studio-booking-open" hover-class="studio-native-pressed" @tap="detail(item.id)"><view class="studio-booking-card-head"><text class="studio-plan-name">{{item.booking.date}}</text><text class="studio-booking-status" :class="'studio-booking-status--'+item.status">{{words('cancellation',item.status)}}</text></view><text>{{item.booking.start}}–{{item.booking.end}}</text><view class="studio-booking-summary"><text class="studio-native-body">{{guestCount(item.booking.guests)}} · {{words('visit',item.booking.plan==='day'?'a_day_of_making_01d6e2':'by_the_hour_5300b2')}}</text><StudioGlyph name="arrow" :size="18"/></view></button><StudioCancel :id="'cancel-'+item.id" :reservation="item" :language="language" @changed="changed"/></view>
    <view v-if="total>30" class="studio-booking-pagination"><button class="studio-native-secondary" :disabled="loading||page===1" @tap="changePage(-1)">{{words('wallet','previous')}}</button><text>{{page}}</text><button class="studio-native-secondary" :disabled="loading||page*30>=total" @tap="changePage(1)">{{words('wallet','next')}}</button></view>
   </template>
   <button class="studio-native-primary" hover-class="studio-native-pressed" @tap="visit"><text class="studio-native-primary-label">{{words('home','come_create_2eee81')}}</text><StudioGlyph name="arrow"/></button>
  </view>
 </StudioShell>
</template>
