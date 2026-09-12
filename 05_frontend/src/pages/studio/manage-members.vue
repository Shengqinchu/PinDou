<script setup lang="ts">
import {ref} from 'vue';
import {onShow,onHide,onUnload} from '@dcloudio/uni-app';
import StudioAdminShell from '../../components/StudioAdminShell.vue';
import StudioCustomerIdentity from '../../components/StudioCustomerIdentity.vue';
import {useStudioNative} from '../../utils/studio-native';
import {adminCall,adminError,goAdmin} from '../../utils/studio-admin';
import {adminView} from '../../utils/studio-admin-cache';
import copy from '../../../../05_studio/src/content/workbench.json';
import {hoursNumber} from '../../../../05_studio/src/time-units';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
type State={items:any[];search:string;page:number;total:number;loaded:boolean};
const view=adminView<State>('members'),saved=view.snapshot;
const busy=ref(false),error=ref(''),items=ref<any[]>(saved?.items||[]),search=ref(saved?.search||''),page=ref(saved?.page||1),total=ref(saved?.total||0),loaded=ref(saved?.loaded||false);let sequence=0;
const remember=()=>view.save({items:items.value,search:search.value,page:page.value,total:total.value,loaded:loaded.value});
async function load(more=false,force=true){if(!view.valid()){items.value=[];loaded.value=false;}if(!force&&(busy.value||view.fresh()))return;const n=++sequence,revision=view.begin();busy.value=true;error.value='';if(!more&&force)page.value=1;const pages=more?[page.value]:Array.from({length:page.value},(_,i)=>i+1);try{const results=await Promise.all(pages.map(p=>adminCall<any>('/manage/members',{search:search.value,page:p})));if(n===sequence){const next=results.flatMap(r=>r.items);items.value=more?[...items.value,...next]:next;total.value=results[0].total;loaded.value=true;view.loaded(revision);remember();}}catch(e){if(n===sequence){error.value=adminError(e,say);if(!view.valid()){items.value=[];loaded.value=false;}}}finally{if(n===sequence)busy.value=false;}}
onShow(()=>void load(false,false));onHide(remember);onUnload(()=>{remember();sequence++;});
</script>
<template><StudioAdminShell :title="say(copy.members)" back :language="language" :shell-style="shellStyle" :keyboard-open="keyboardOpen" :busy="busy&&!loaded" :error="error" @refresh="load()" @language="changeLanguage"><input v-model="search" class="admin-input" :placeholder="say(copy.member_search)" confirm-type="search" @confirm="load()"/><view class="native-member-list"><button v-for="person in items" :key="person.owner_id" class="admin-card admin-stack native-member-card" hover-class="admin-pressed" @tap="goAdmin('-member','id='+encodeURIComponent(person.owner_id))"><StudioCustomerIdentity :customer="person" :language="language"/><view class="admin-row"><text>{{say(copy.hours).replace('{count}',hoursNumber(person.minutes))}}</text><text>{{say(copy.points).replace('{count}',String(person.points))}}</text></view></button></view><view v-if="!busy&&!items.length" class="admin-empty">{{say(copy.empty)}}</view><button v-if="items.length<total" class="admin-secondary" :disabled="busy" @tap="page++;load(true)">{{say(copy.more)}}</button></StudioAdminShell></template>
<style scoped>.native-member-list{margin-top:14px}.native-member-card{display:flex;width:100%;text-align:left}.native-member-card .admin-row{width:100%;font-size:13px}</style>
