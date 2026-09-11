<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import { useStudioNative } from '../../utils/studio-native';
import { refreshStudioContent,studioWords,studioProfile } from '../../utils/studio-content';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const words=(key:string)=>say(studioWords('details',key));
function phone(){uni.makePhoneCall({phoneNumber:studioProfile.phone.replace(/\s/g,'')});}
function copyWechat(){uni.setClipboardData({data:studioProfile.wechat});}
function copyAddress(){uni.setClipboardData({data:studioProfile.address});}
function visit(){uni.navigateTo({url:'/pages/studio/visit'});}
onShow(()=>void refreshStudioContent());
</script>
<template>
 <StudioShell id="studio-shell" fitted :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" @language="changeLanguage">
  <view class="studio-native-main studio-details">
   <view class="studio-native-section"><text class="studio-native-subtitle">{{words('studio_address_171634')}}</text><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-secondary studio-address" hover-class="studio-native-pressed" @tap="copyAddress"><StudioGlyph name="pin"/><text>{{studioProfile.address}}</text><StudioGlyph name="copy" :size="17"/></button></view>
   <view class="studio-native-section"><text class="studio-native-subtitle">{{say(studioWords('cancellation','contact'))}}</text><view class="studio-contact-shortcuts"><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-secondary" hover-class="studio-native-pressed" @tap="copyWechat"><StudioGlyph name="wechat" :size="18"/><text>{{studioProfile.wechat}}</text></button><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-secondary" hover-class="studio-native-pressed" @tap="phone"><StudioGlyph name="phone" :size="18"/><text>{{studioProfile.phone}}</text></button></view></view>
   <view class="studio-native-section"><text class="studio-native-subtitle">{{words('parking_8188de')}}</text><text class="studio-native-body">{{words('free_visitor_parking_is_available_downstairs_usually_7daf39')}}</text><text class="studio-native-label">{{words('nearby_parking_options_1a311a')}}</text><text v-for="address in studioProfile.nearby_parking" :key="address" class="studio-native-body" selectable>{{address}}</text></view>
   <view class="studio-native-section"><text class="studio-native-subtitle">{{words('seats_and_tools_4b0a0a')}}</text><text class="studio-native-body">{{words('a_comfortable_chair_an_individual_seat_and_f15251')}}</text></view>
  </view>
  <template #actions><view class="studio-visit-actions"><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-primary" hover-class="studio-native-pressed" @tap="visit"><StudioGlyph name="calendar"/><text class="studio-native-primary-label">{{say(studioWords('home','come_create_2eee81'))}}</text><StudioGlyph name="arrow"/></button></view></template>
 </StudioShell>
</template>
