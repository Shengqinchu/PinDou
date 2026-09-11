<script setup lang="ts">
import {ref} from 'vue';
import {onShow,onUnload} from '@dcloudio/uni-app';
import StudioAdminShell from '../../components/StudioAdminShell.vue';
import {useStudioNative} from '../../utils/studio-native';
import {adminCall,adminError,goAdmin} from '../../utils/studio-admin';
import copy from '../../../../05_studio/src/content/workbench.json';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const busy=ref(false),error=ref(''),items=ref<any[]>([]),search=ref(''),page=ref(1),total=ref(0);let sequence=0;
async function load(more=false){const n=++sequence;busy.value=true;error.value='';if(!more)page.value=1;try{const result=await adminCall<any>('/manage/members',{search:search.value,page:page.value});if(n===sequence){items.value=more?[...items.value,...result.items]:result.items;total.value=result.total;}}catch(e){error.value=adminError(e,say);}finally{busy.value=false;}}
onShow(()=>void load());onUnload(()=>{sequence++;});
</script>
<template><StudioAdminShell :title="say(copy.members)" back :language="language" :shell-style="shellStyle" :keyboard-open="keyboardOpen" :busy="busy" :error="error" @refresh="load()" @language="changeLanguage"><input v-model="search" class="admin-input" :placeholder="say(copy.member_search)" confirm-type="search" @confirm="load()"/><view class="native-member-list"><button v-for="person in items" :key="person.owner_id" class="admin-card admin-stack native-member-card" hover-class="admin-pressed" @tap="goAdmin('-member','id='+encodeURIComponent(person.owner_id))"><text class="admin-name">{{person.name}}</text><text class="admin-muted">{{person.booking_profile?.contact||person.email||'—'}}</text><view class="admin-row"><text>{{say(copy.minutes).replace('{count}',String(person.minutes))}}</text><text>{{say(copy.points).replace('{count}',String(person.points))}}</text></view></button></view><view v-if="!busy&&!items.length" class="admin-empty">{{say(copy.empty)}}</view><button v-if="items.length<total" class="admin-secondary" :disabled="busy" @tap="page++;load(true)">{{say(copy.more)}}</button></StudioAdminShell></template>
<style scoped>.native-member-list{margin-top:14px}.native-member-card{display:flex;width:100%;text-align:left}.native-member-card .admin-row{width:100%;font-size:13px}</style>
