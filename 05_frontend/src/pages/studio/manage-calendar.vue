<script setup lang="ts">
import {computed,ref} from 'vue';
import {onShow,onUnload} from '@dcloudio/uni-app';
import StudioAdminShell from '../../components/StudioAdminShell.vue';
import {useStudioNative} from '../../utils/studio-native';
import {adminCall,adminError,goAdmin,today} from '../../utils/studio-admin';
import copy from '../../../../05_studio/src/content/workbench.json';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const days=ref<any[]>([]),start=ref(today()),selected=ref(today()),busy=ref(false),error=ref('');let alive=true;
const day=computed(()=>days.value.find(d=>d.date===selected.value));
const ordered=computed(()=>[...(day.value?.bookings||[])].sort((a,b)=>a.start.localeCompare(b.start)||a.name.localeCompare(b.name)));
const colors=['#759aa9','#938ab8','#b594b7','#b9a372','#87a58c','#ad8991'];
function color(id:string){return colors[[...id].reduce((sum,c)=>sum+c.charCodeAt(0),0)%colors.length];}
const label=(key:string)=>say((copy as Record<string,string[]>)[key]||copy.all);
async function load(){if(busy.value)return;busy.value=true;error.value='';try{const result=await adminCall<{days:any[]}>('/manage/reservation-timetable',{start:start.value});if(alive){days.value=result.days;if(!days.value.some(d=>d.date===selected.value))selected.value=start.value;}}catch(e){error.value=adminError(e,say);}finally{busy.value=false;}}
onShow(()=>void load());onUnload(()=>{alive=false;});
</script>
<template><StudioAdminShell :title="say(copy.calendar)" active="reservations" back :language="language" :shell-style="shellStyle" :keyboard-open="keyboardOpen" :busy="busy" :error="error" @refresh="load()" @language="changeLanguage"><picker mode="date" :value="start" @change="start=$event.detail.value;load()"><view class="admin-input">{{say(copy.date)}} · {{start}}</view></picker><view class="native-calendar-days"><button v-for="d in days" :key="d.date" :class="{chosen:d.date===selected}" hover-class="admin-pressed" @tap="selected=d.date"><text>{{d.date.slice(5)}}</text><text class="admin-muted">{{d.bookings.length}}</text></button></view><view v-if="day" class="admin-row"><text class="admin-name">{{day.date}}</text><text class="admin-muted">{{day.open}}–{{day.close}}</text></view><text class="admin-muted">{{say(copy.timezone)}}</text><view class="native-calendar-bookings"><button v-for="booking in ordered" :key="booking.id" class="admin-card admin-stack native-calendar-booking" :style="{borderLeftColor:color(booking.id)}" hover-class="admin-pressed" @tap="goAdmin('-reservation','id='+booking.id)"><view class="admin-row"><text class="admin-name">{{booking.name}}</text><text class="admin-badge">{{label(booking.status)}}</text></view><view class="admin-row"><text>{{booking.start}}–{{booking.end}}</text><text>{{say(copy.guests).replace('{count}',String(booking.guests))}}</text></view><text v-if="booking.note" class="admin-muted">{{booking.note}}</text></button></view><view v-if="!busy&&!ordered.length" class="admin-empty">{{say(copy.empty)}}</view></StudioAdminShell></template>
<style scoped>.native-calendar-days{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px;margin:14px 0 20px}.native-calendar-days button{display:flex;flex-direction:column;gap:4px;align-items:center;justify-content:center;background:white;border:1px solid #dfe8ed;border-radius:9px;padding:10px 3px;min-height:52px;font-size:12px}.native-calendar-days .chosen{background:#dfedf5;border-color:#97b3c4}.native-calendar-bookings{margin-top:14px}.native-calendar-booking{border-left-width:4px;display:flex;width:100%;text-align:left}.native-calendar-booking>.admin-row{width:100%}@media(max-width:350px){.native-calendar-days{grid-template-columns:repeat(4,minmax(0,1fr))}}</style>
