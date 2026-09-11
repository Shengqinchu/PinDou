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
 <StudioShell id="studio-shell" :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" nav="home" @language="changeLanguage">
  <view class="studio-native-main">
   <text class="studio-native-title">{{words('a_little_guide_to_the_studio_1b38da')}}</text>
   <view class="studio-native-section"><text class="studio-native-subtitle">{{words('studio_address_171634')}}</text><button class="studio-native-secondary studio-address" hover-class="studio-native-pressed" @tap="copyAddress"><StudioGlyph name="pin"/><text>{{studioProfile.address}}</text><StudioGlyph name="copy" :size="17"/></button><text class="studio-native-body">{{words('visits_are_by_appointment_you_are_welcome_008328')}}</text><text class="studio-native-body">{{words('the_host_will_meet_you_downstairs_when_aeec4f')}}</text></view>
   <view class="studio-native-section"><text class="studio-native-subtitle">{{say(studioWords('cancellation','contact'))}}</text><button class="studio-native-secondary" hover-class="studio-native-pressed" @tap="copyWechat"><StudioGlyph name="wechat"/><text>{{studioProfile.wechat}}</text><StudioGlyph name="copy" :size="17"/></button><button class="studio-native-secondary" hover-class="studio-native-pressed" @tap="phone"><StudioGlyph name="phone"/><text>{{studioProfile.phone}}</text></button></view>
   <view class="studio-native-section"><text class="studio-native-subtitle">{{words('parking_8188de')}}</text><text class="studio-native-body">{{words('free_visitor_parking_is_available_downstairs_usually_7daf39')}}</text><text class="studio-native-label">{{words('nearby_parking_options_1a311a')}}</text><text v-for="address in studioProfile.nearby_parking" :key="address" class="studio-native-body" selectable>{{address}}</text></view>
   <view class="studio-native-section"><text class="studio-native-subtitle">{{words('seats_and_tools_4b0a0a')}}</text><text class="studio-native-body">{{words('a_comfortable_chair_an_individual_seat_and_f15251')}}</text></view>
   <button class="studio-native-primary" hover-class="studio-native-pressed" @tap="visit"><text class="studio-native-primary-label">{{say(studioWords('home','come_create_2eee81'))}}</text><StudioGlyph name="arrow"/></button>
  </view>
 </StudioShell>
</template>
