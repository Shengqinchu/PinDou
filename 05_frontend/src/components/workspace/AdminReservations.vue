<script setup lang="ts">
defineOptions({options:{styleIsolation:'shared'}});
import {ref} from 'vue';
import {studioPlanWords,studioWords,fillWords} from '../../utils/studio-content';
import {onViewLoad as onLoad,onViewShow as onShow,onViewHide as onHide,onViewUnload as onUnload} from '../../utils/studio-view-lifecycle';
import StudioAdminShell from '../../components/StudioAdminShell.vue';
import {useStudioNative} from '../../utils/studio-native';
import {adminCall,adminError,goAdmin} from '../../utils/studio-admin';
import {adminView} from '../../utils/studio-admin-cache';
import copy from '../../../../05_studio/src/content/workbench.json';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
type State={experience:string;items:any[];status:string;day:string;search:string;page:number;total:number;loaded:boolean};
const view=adminView<State>('reservations'),saved=view.snapshot;
const busy=ref(false),error=ref(''),items=ref<any[]>(saved?.items||[]),status=ref(saved?.status||'pending'),day=ref(saved?.day||''),search=ref(saved?.search||''),page=ref(saved?.page||1),total=ref(saved?.total||0),loaded=ref(saved?.loaded||false);
const experience=ref(saved?.experience||'all');
const patchWords=(key:string)=>say(studioWords('patch',key));
const gift=(count:number)=>fillWords(studioWords('promotion','gift_count'),language.value,{v0:count});
const states=['pending','confirmed','completed','cancelled','all'];let sequence=0;
const words=(key:string)=>say((copy as Record<string,string[]>)[key]||copy.all);
const remember=()=>view.save({experience:experience.value,items:items.value,status:status.value,day:day.value,search:search.value,page:page.value,total:total.value,loaded:loaded.value});
async function load(append=false,force=true){if(!view.valid()){items.value=[];loaded.value=false;}if(!force&&(busy.value||view.fresh()))return;const n=++sequence,revision=view.begin();busy.value=true;error.value='';if(!append&&force)page.value=1;
 const pages=append?[page.value]:Array.from({length:page.value},(_,i)=>i+1);
 try{const results=await Promise.all(pages.map(p=>adminCall<{items:any[];total:number}>('/manage/reservations',{experience:experience.value,status:status.value,...(day.value?{day:day.value}:{}),search:search.value,page:p})));if(n===sequence){const next=results.flatMap(r=>r.items);items.value=append?[...items.value,...next]:next;total.value=results[0].total;loaded.value=true;view.loaded(revision);remember();}}
 catch(e){if(n===sequence){error.value=adminError(e,say);if(!view.valid()){items.value=[];loaded.value=false;}}}finally{if(n===sequence)busy.value=false;}}
function change(value:string){status.value=value;void load();}
function dateChange(event:any){day.value=event.detail.value;void load();}
onLoad(q=>{let changed=false;if(typeof q?.date==='string'&&q.date!==day.value){day.value=q.date;changed=true;}if(typeof q?.status==='string'&&states.includes(q.status)&&q.status!==status.value){status.value=q.status;changed=true;}if(changed){view.expire();page.value=1;void load(false,false);}});onShow(()=>void load(false,false));onHide(remember);onUnload(()=>{remember();sequence++;});
</script>
<template><StudioAdminShell :title="say(copy.reservations)" active="reservations" :language="language" :shell-style="shellStyle" :keyboard-open="keyboardOpen" :busy="busy&&!loaded" :error="error" @refresh="load()" @language="changeLanguage">
 <view class="admin-pair"><button class="admin-secondary" hover-class="admin-pressed" :hover-start-time="0" :hover-stay-time="180" @tap="goAdmin('-calendar')">{{say(copy.calendar)}}</button><button class="admin-secondary" hover-class="admin-pressed" :hover-start-time="0" :hover-stay-time="180" @tap="goAdmin('-patch-offer')">{{say(studioWords('promotion','edit'))}}</button></view>
 <view class="admin-filters" :aria-label="patchWords('filter')"><button v-for="kind in ['all','beads','patch']" :key="kind" :class="{chosen:experience===kind}" hover-class="admin-pressed" :hover-start-time="0" :hover-stay-time="180" @tap="experience=kind;load()">{{patchWords(kind)}}</button></view>
 <input v-model="search" class="admin-input" :placeholder="say(copy.search)" confirm-type="search" @confirm="load()"/>
 <view class="admin-filters"><button v-for="state in states" :key="state" :class="{chosen:status===state}" hover-class="admin-pressed" :hover-start-time="0" :hover-stay-time="180" @tap="change(state)">{{words(state)}}</button></view>
 <view class="admin-row admin-booking-date"><picker mode="date" :value="day" @change="dateChange"><view class="admin-secondary">{{day||say(copy.date)}}</view></picker><button hover-class="admin-pressed" :hover-start-time="0" :hover-stay-time="180" v-if="day||search" class="admin-secondary" @tap="day='';search='';load()">{{say(copy.clear)}}</button></view>
 <button v-for="item in items" :key="item.id" class="admin-card admin-stack admin-booking-card" hover-class="admin-pressed" :hover-start-time="0" :hover-stay-time="180" @tap="goAdmin('-reservation','id='+encodeURIComponent(item.id))"><view class="admin-row"><text class="admin-name">{{item.name}}</text><text class="admin-badge">{{words(item.status)}}</text></view><text class="admin-muted">{{say(studioPlanWords(item.booking.plan))}}</text><text v-if="item.patch_gift_guests>0" class="admin-patch-gift">{{gift(item.patch_gift_guests)}}</text><text>{{item.booking.date}} · {{item.booking.start}}–{{item.booking.end}}</text><text class="admin-muted">{{say(copy.guests).replace('{count}',String(item.booking.guests))}}<text v-if="item.payload?.notes"> · {{item.payload.notes}}</text></text></button>
 <view v-if="!busy&&!items.length" class="admin-empty">{{say(copy.empty)}}</view><button hover-class="admin-pressed" :hover-start-time="0" :hover-stay-time="180" v-if="items.length<total" class="admin-secondary" :disabled="busy" @tap="page++;load(true)">{{say(copy.more)}}</button>
 </StudioAdminShell></template>
<style scoped>.admin-booking-date{margin-bottom:14px}.admin-booking-card{display:flex;width:100%;text-align:left}.admin-booking-card>.admin-row{width:100%}</style>
