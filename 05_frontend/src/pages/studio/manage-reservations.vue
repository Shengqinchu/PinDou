<script setup lang="ts">
import {ref} from 'vue';
import {onLoad,onShow,onUnload} from '@dcloudio/uni-app';
import StudioAdminShell from '../../components/StudioAdminShell.vue';
import {useStudioNative} from '../../utils/studio-native';
import {adminCall,adminError,goAdmin} from '../../utils/studio-admin';
import copy from '../../../../05_studio/src/content/workbench.json';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const busy=ref(false),error=ref(''),items=ref<any[]>([]),status=ref('pending'),day=ref(''),search=ref(''),page=ref(1),total=ref(0);
const states=['pending','confirmed','completed','cancelled','all'];let sequence=0;
const words=(key:string)=>say((copy as Record<string,string[]>)[key]||copy.all);
async function load(append=false){const n=++sequence;busy.value=true;error.value='';if(!append)page.value=1;
 try{const result=await adminCall<{items:any[];total:number}>('/manage/reservations',{status:status.value,...(day.value?{day:day.value}:{}),search:search.value,page:page.value});if(n===sequence){items.value=append?[...items.value,...result.items]:result.items;total.value=result.total;}}
 catch(e){if(n===sequence)error.value=adminError(e,say);}finally{if(n===sequence)busy.value=false;}}
function change(value:string){status.value=value;void load();}
function dateChange(event:any){day.value=event.detail.value;void load();}
onLoad(q=>{if(typeof q?.date==='string')day.value=q.date;if(typeof q?.status==='string'&&states.includes(q.status))status.value=q.status;});onShow(()=>void load());onUnload(()=>{sequence++;});
</script>
<template><StudioAdminShell :title="say(copy.reservations)" active="reservations" :language="language" :shell-style="shellStyle" :keyboard-open="keyboardOpen" :busy="busy" :error="error" @refresh="load()" @language="changeLanguage">
 <input v-model="search" class="admin-input" :placeholder="say(copy.search)" confirm-type="search" @confirm="load()"/>
 <view class="admin-filters"><button v-for="state in states" :key="state" :class="{chosen:status===state}" hover-class="admin-pressed" @tap="change(state)">{{words(state)}}</button></view>
 <view class="admin-row admin-booking-date"><picker mode="date" :value="day" @change="dateChange"><view class="admin-secondary">{{day||say(copy.date)}}</view></picker><button v-if="day||search" class="admin-secondary" @tap="day='';search='';load()">{{say(copy.clear)}}</button></view>
 <button v-for="item in items" :key="item.id" class="admin-card admin-stack admin-booking-card" hover-class="admin-pressed" @tap="goAdmin('-reservation','id='+encodeURIComponent(item.id))"><view class="admin-row"><text class="admin-name">{{item.name}}</text><text class="admin-badge">{{words(item.status)}}</text></view><text>{{item.booking.date}} · {{item.booking.start}}–{{item.booking.end}}</text><text class="admin-muted">{{say(copy.guests).replace('{count}',String(item.booking.guests))}}<text v-if="item.payload?.notes"> · {{item.payload.notes}}</text></text></button>
 <view v-if="!busy&&!items.length" class="admin-empty">{{say(copy.empty)}}</view><button v-if="items.length<total" class="admin-secondary" :disabled="busy" @tap="page++;load(true)">{{say(copy.more)}}</button>
 </StudioAdminShell></template>
<style scoped>.admin-booking-date{margin-bottom:14px}.admin-booking-card{display:flex;width:100%;text-align:left}.admin-booking-card>.admin-row{width:100%}</style>
