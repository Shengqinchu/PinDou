<script setup lang="ts">
import {ref,computed,watch} from 'vue';
import {onShow,onUnload} from '@dcloudio/uni-app';
import StudioAdminShell from '../../components/StudioAdminShell.vue';
import {useStudioNative} from '../../utils/studio-native';
import {adminCall,adminError} from '../../utils/studio-admin';
import {studioWords,fillWords} from '../../utils/studio-content';
import type {PatchPromotion} from '../../utils/studio-patch-promotion';
type Managed=PatchPromotion&{allocated:number;remaining_adjustment:number;started_at:string;version:number};
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const offer=ref<Managed>(),quota=ref(''),remaining=ref(''),remainingEdited=ref(false),enabled=ref(false),loading=ref(false),saving=ref(false),error=ref('');
let sequence=0,alive=true;
const words=(key:string)=>say(studioWords('promotion',key));
const format=(key:string,values:Record<string,string|number>)=>fillWords(studioWords('promotion',key),language.value,values);
const valid=computed(()=>[quota.value,remaining.value].every(v=>/^\d+$/.test(v)&&Number(v)<=100000));
const dirty=computed(()=>!!offer.value&&(quota.value!==String(offer.value.quota)||remaining.value!==String(offer.value.remaining)||enabled.value!==offer.value.enabled));
function apply(value:Managed){offer.value=value;quota.value=String(value.quota);remaining.value=String(value.remaining);remainingEdited.value=false;enabled.value=value.enabled;}
watch(quota,()=>{if(!remainingEdited.value&&offer.value&&/^\d+$/.test(quota.value))remaining.value=String(Math.max(0,Number(quota.value)-offer.value.allocated+(offer.value.remaining_adjustment??0)));});
async function load(force=false){
 if(saving.value||loading.value||(!force&&dirty.value))return;
 const n=++sequence;loading.value=true;error.value='';
 try{const result=await adminCall<Managed>('/manage/patch-promotion');if(alive&&n===sequence)apply(result);}
 catch(e){if(alive&&n===sequence)error.value=adminError(e,say);}
 finally{if(alive&&n===sequence)loading.value=false;}
}
async function save(){
 if(!offer.value||!valid.value||saving.value||loading.value)return;
 saving.value=true;error.value='';
 const body={quota:Number(quota.value),...(remainingEdited.value?{remaining:Number(remaining.value)}:{}),enabled:enabled.value,version:offer.value.version};
 try{const result=await adminCall<Managed>('/manage/patch-promotion',body,'PUT');if(alive){apply(result);uni.showToast({title:words('saved'),icon:'none'});}}
 catch(e){if(alive)error.value=adminError(e,say);}
 finally{if(alive)saving.value=false;}
}
onShow(()=>void load());onUnload(()=>{alive=false;sequence++;});
</script>
<template>
 <StudioAdminShell :title="words('desk_title')" active="reservations" back :language="language" :shell-style="shellStyle" :keyboard-open="keyboardOpen" :busy="loading" :error="error" @refresh="load(true)" @language="changeLanguage">
  <template v-if="offer">
   <view class="admin-card admin-stack"><text class="admin-name">{{format('remaining',{v0:offer.remaining,v1:offer.quota})}}</text><text class="admin-muted">{{format('allocated',{v0:offer.allocated})}}</text><text v-if="!offer.enabled" class="admin-muted">{{words('paused')}}</text></view>
   <view class="admin-card admin-stack">
    <label class="admin-field"><text class="admin-label">{{words('quota')}}</text><input v-model="quota" class="admin-input" type="number" :maxlength="6" :disabled="saving||loading" :aria-label="words('quota')"/></label>
    <label class="admin-field"><text class="admin-label">{{words('remaining_label')}}</text><input v-model="remaining" class="admin-input" type="number" :maxlength="6" :disabled="saving||loading" :aria-label="words('remaining_label')" @input="remainingEdited=true"/></label>
    <text class="admin-muted">{{words('remaining_help')}}</text>
    <view class="admin-row"><text class="admin-label">{{words('enabled')}}</text><switch :checked="enabled" color="#779bb1" :disabled="saving||loading" :aria-label="words('enabled')" @change="enabled=$event.detail.value"/></view>
   </view>
   <view class="admin-card admin-stack"><text class="admin-name">{{words('rules_label')}}</text><text class="admin-muted">{{words('rules')}}</text><text class="admin-muted">{{words('quota_help')}}</text></view>
  </template>
  <button v-if="error" class="admin-secondary" :disabled="saving||loading" @tap="load(true)">{{words('retry')}}</button>
  <template #actions><button class="admin-primary" hover-class="admin-pressed" :disabled="!offer||!valid||!dirty||saving||loading" @tap="save">{{words(saving?'saving':'save')}}</button></template>
 </StudioAdminShell>
</template>
