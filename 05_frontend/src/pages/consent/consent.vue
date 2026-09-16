<script setup lang="ts">
import {computed,ref} from 'vue';
import {onLoad} from '@dcloudio/uni-app';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import copy from '../../../../05_studio/src/content/studio-miniapp-legal.json';
import {useStudioNative} from '../../utils/studio-native';
import {studioProfile} from '../../utils/studio-content';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const kind=ref<'privacy'|'agreement'>('privacy'),contractFailed=ref(false),opening=ref(false);
const words=(key:keyof typeof copy)=>say(copy[key]);
const privacy=['identity','booking','images','permissions','providers','storage','choices'] as const;
const agreement=['service','cancellation','materials','security'] as const;
const sections=computed(()=>(kind.value==='privacy'?privacy:agreement).map(key=>({key,title:words((key+'_title') as keyof typeof copy),body:words((key+'_body') as keyof typeof copy)})));
let platformContract=false;
// #ifdef MP-WEIXIN
platformContract=true;
// #endif
onLoad(options=>{kind.value=options?.type==='agreement'?'agreement':'privacy';});
function back(){if(getCurrentPages().length>1)uni.navigateBack();else uni.redirectTo({url:'/pages/studio/home'});}
function viewContract(){
 if(opening.value)return;contractFailed.value=false;
 if(typeof uni.openPrivacyContract!=='function'){contractFailed.value=true;return;}
 opening.value=true;
 uni.openPrivacyContract({fail:()=>{contractFailed.value=true;},complete:()=>{opening.value=false;}});
}
function wechat(){uni.setClipboardData({data:studioProfile.wechat});}
function phone(){uni.makePhoneCall({phoneNumber:studioProfile.phone.replace(/\s/g,'')});}
</script>
<template>
 <StudioShell fitted :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" @language="changeLanguage">
  <view class="studio-native-main studio-legal-page">
   <text class="studio-native-title">{{words(kind==='privacy'?'privacy_title':'agreement_title')}}</text>
   <text class="studio-native-label">{{words('updated')}}</text>
   <text class="studio-legal-body" selectable>{{words(kind==='privacy'?'privacy_intro':'terms_intro')}}</text>
   <view v-for="section in sections" :key="section.key" class="studio-legal-section"><text class="studio-legal-heading">{{section.title}}</text><text class="studio-legal-body" selectable>{{section.body}}</text></view>
   <button v-if="platformContract&&kind==='privacy'" id="wechat-privacy-contract" class="studio-native-secondary studio-legal-contract" :disabled="opening" hover-class="studio-native-pressed" :hover-start-time="0" :hover-stay-time="180" @tap="viewContract">{{words('wechat_contract')}}</button>
   <text v-if="contractFailed" class="studio-native-error" role="alert">{{words('contract_unavailable')}}</text>
   <view class="studio-legal-section"><text class="studio-legal-heading">{{words('support_title')}}</text><text class="studio-legal-body" selectable>{{words('support_body')}}</text><view class="studio-contact-shortcuts"><button class="studio-native-secondary" hover-class="studio-native-pressed" :hover-start-time="0" :hover-stay-time="180" @tap="wechat"><StudioGlyph name="wechat" :size="18"/><text>{{studioProfile.wechat}}</text></button><button class="studio-native-secondary" hover-class="studio-native-pressed" :hover-start-time="0" :hover-stay-time="180" @tap="phone"><StudioGlyph name="phone" :size="18"/><text>{{studioProfile.phone}}</text></button></view></view>
  </view>
  <template #actions><view class="studio-visit-actions"><button class="studio-native-primary" hover-class="studio-native-pressed" :hover-start-time="0" :hover-stay-time="180" @tap="back">{{words('back')}}</button></view></template>
 </StudioShell>
</template>
<style scoped>
.studio-legal-page{padding-bottom:10px}.studio-legal-section{display:flex;flex-direction:column;gap:7px;margin-top:5px}.studio-legal-heading{font-size:16px;font-weight:600;line-height:1.5}.studio-legal-body{font-size:14px;line-height:1.85;overflow-wrap:anywhere;color:#41545d;white-space:pre-line}.studio-legal-contract{min-height:48px;white-space:normal;line-height:1.5}.studio-legal-page .studio-contact-shortcuts{flex-wrap:wrap}.studio-legal-page .studio-contact-shortcuts button{flex:1 1 165px}
</style>
