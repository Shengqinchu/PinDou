<script setup lang="ts">
import {pressTo} from '../../utils/press';
import {computed,nextTick,ref} from 'vue';
import {onShow} from '@dcloudio/uni-app';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import StudioDetailPhoto from '../../components/StudioDetailPhoto.vue';
import {useStudioNative} from '../../utils/studio-native';
import {refreshStudioContent,studioWords,studioMedia} from '../../utils/studio-content';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const words=(key:string)=>say(studioWords('details',key));
const processWords=(key:string)=>say(studioWords('process',key));
const contact=(key:string)=>say(studioWords('contacts',key));
const scrollTo=ref('');
const photoKeys=['arrival-entrance','parking-entrance','parking-location','process-pattern','process-tools','process-making','process-ironing','process-findings','process-finishes','process-packaging'] as const;
type PhotoKey=typeof photoKeys[number];
const photos=computed(()=>Object.fromEntries(photoKeys.map(key=>[key,studioMedia(key)])) as Record<PhotoKey,ReturnType<typeof studioMedia>>);
const arrivalPhotos=[
 {key:'arrival-entrance',alt:'lightfilled_worktables_by_the_studio_window_148082'},
 {key:'parking-entrance',alt:'visitor_parking_entrance_30c573'},
 {key:'parking-location',alt:'visitor_parking_location_c046e2'},
] as const;
const sections=[{id:'arrival',key:'getting_here_1f608d'},{id:'parking',key:'parking_8188de'},{id:'services',key:'at_the_studio_0bc0c9'},{id:'notes',key:'good_to_know_fc4515'},{id:'process',key:''}];
const services=[
 ['seats_and_tools_4b0a0a','a_comfortable_chair_an_individual_seat_and_f15251'],
 ['textures_and_finishing_touches_6d3e7b','we_keep_exploring_different_ironing_techniques_small_659fdb'],
 ['little_things_to_take_with_you_a9cf30','standard_magnets_phone_straps_and_charms_are_c11f4d'],
 ['take_your_time_512353','snacks_fruit_and_drinking_water_are_available_746405'],
];
const notes=[
 ['beads_and_handmade_finishes_cdb69f','some_beads_may_have_mixed_colours_burrs_ac08b3'],
 ['keeping_the_worktable_lovely_4b7731','place_beads_individually_rather_than_scattering_them_2535e2'],
 ['time_and_payment_a87618','time_is_measured_by_actual_making_time_8a7c82'],
];
const steps=[
 {title:'patternTitle',body:'patternIntro',extra:'patternDetail',photos:['pattern']},
 {title:'toolsTitle',body:'toolsBody',extra:'',photos:['tools']},
 {title:'makingTitle',body:'makingBody',extra:'',photos:['making']},
 {title:'ironingTitle',body:'ironingBody',extra:'',photos:['ironing']},
 {title:'finishingTitle',body:'finishingBody',extra:'packaging',photos:['findings','finishes','packaging']},
];
const processPhoto=(key:string)=>photos.value[('process-'+key) as PhotoKey];
function preview(key:PhotoKey){uni.previewImage({current:photos.value[key].src,urls:photoKeys.map(name=>photos.value[name].src)});}
function previewProcess(key:string){preview(('process-'+key) as PhotoKey);}
function copyAddress(value=contact('address')){uni.setClipboardData({data:value});}
function phone(){uni.makePhoneCall({phoneNumber:contact('phone').replace(/\s/g,'')});}
function copyWechat(){uni.setClipboardData({data:contact('wechat')});}
function copyTools(){const url=processWords('toolsUrl');if(/^https:\/\//.test(url))uni.setClipboardData({data:url});}
async function jump(id:string){scrollTo.value='';await nextTick();scrollTo.value='studio-detail-'+id;}
function visit(){pressTo('/pages/studio/visit');}
onShow(()=>void refreshStudioContent());
</script>
<template>
 <StudioShell id="studio-shell" fitted :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" :scroll-to="scrollTo" @language="changeLanguage">
  <view class="studio-native-main studio-details">
   <view class="studio-native-section"><text class="studio-native-label">{{words('a_little_knowhow_before_you_visit_b1dd61')}}</text><text class="studio-native-title">{{words('a_little_guide_to_the_studio_1b38da')}}</text><text class="studio-native-body">{{words('getting_here_finding_parking_and_the_little_0ec5c9')}}</text></view>
   <view class="studio-detail-nav" :aria-label="words('studio_information_sections_45baee')"><button v-for="section in sections" :key="section.id" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="jump(section.id)">{{section.key?words(section.key):processWords('title')}}</button></view>
   <view id="studio-detail-arrival" class="studio-native-section studio-detail-section">
    <text class="studio-native-subtitle">{{words('studio_address_171634')}}</text>
    <button class="studio-native-secondary studio-address" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="copyAddress()"><StudioGlyph name="pin"/><text>{{contact('address')}}</text><StudioGlyph name="copy" :size="17"/></button>
    <text v-for="key in ['in_downtown_hamilton_accessible_by_local_buses_657f96','visits_are_by_appointment_you_are_welcome_008328','the_host_will_meet_you_downstairs_when_aeec4f']" :key="key" class="studio-native-body">{{words(key)}}</text>
    <StudioDetailPhoto :photo="photos['arrival-entrance']" :alt="words(arrivalPhotos[0].alt)" :language="language" eager @open="preview('arrival-entrance')"/>
    <view class="studio-contact-shortcuts"><button class="studio-native-secondary" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="copyWechat"><StudioGlyph name="wechat" :size="18"/><text>{{contact('wechat')}}</text></button><button class="studio-native-secondary" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="phone"><StudioGlyph name="phone" :size="18"/><text>{{contact('phone')}}</text></button></view>
   </view>
   <view id="studio-detail-parking" class="studio-native-section studio-detail-section">
    <text class="studio-native-subtitle">{{words('a_place_to_park_fcb8e3')}}</text><text class="studio-native-body">{{words('free_visitor_parking_is_available_downstairs_usually_7daf39')}}</text>
    <StudioDetailPhoto v-for="photo in arrivalPhotos.slice(1)" :key="photo.key" :photo="photos[photo.key]" :alt="words(photo.alt)" :language="language" @open="preview(photo.key)"/>
    <text class="studio-plan-name">{{words('nearby_parking_options_1a311a')}}</text><button v-for="key in ['parking_1','parking_2']" :key="key" class="studio-native-secondary studio-address" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="copyAddress(contact(key))"><StudioGlyph name="pin" :size="18"/><text>{{contact(key)}}</text><StudioGlyph name="copy" :size="17"/></button>
   </view>
   <view id="studio-detail-services" class="studio-native-section studio-detail-section"><text class="studio-native-subtitle">{{words('made_comfortable_made_yours_0c8904')}}</text><view v-for="item in services" :key="item[0]" class="studio-native-section studio-detail-article"><text class="studio-plan-name">{{words(item[0])}}</text><text class="studio-native-body">{{words(item[1])}}</text></view></view>
   <view id="studio-detail-notes" class="studio-native-section studio-detail-section"><text class="studio-native-subtitle">{{words('a_few_little_notes_7bbea4')}}</text><view v-for="item in notes" :key="item[0]" class="studio-native-section studio-detail-article"><text class="studio-plan-name">{{words(item[0])}}</text><text class="studio-native-body">{{words(item[1])}}</text></view></view>
   <view id="studio-detail-process" class="studio-native-section studio-detail-section">
    <text class="studio-native-subtitle">{{processWords('title')}}</text>
    <view v-for="(step,index) in steps" :key="step.title" class="studio-native-section studio-detail-step">
     <text class="studio-native-label">{{String(index+1).padStart(2,'0')}}</text><text class="studio-native-subtitle">{{processWords(step.title)}}</text><text class="studio-native-body">{{processWords(step.body)}}</text><text v-if="step.extra" class="studio-native-body">{{processWords(step.extra)}}</text>
     <button v-if="index===1" class="studio-native-link studio-detail-tools" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="copyTools"><text>{{processWords('toolsLink')}}</text><StudioGlyph name="copy" :size="17"/></button>
     <StudioDetailPhoto v-for="key in step.photos" :key="key" :photo="processPhoto(key)" :alt="processWords(key+'Alt')" :language="language" @open="previewProcess(key)"/>
    </view>
    <text class="studio-native-body">{{processWords('booked')}}</text><text class="studio-native-body">{{processWords('notBooked')}}</text>
   </view>
  </view>
  <template #actions><view class="studio-visit-actions"><button class="studio-native-primary" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="visit"><StudioGlyph name="calendar"/><text class="studio-native-primary-label">{{processWords('visit')}}</text><StudioGlyph name="arrow"/></button></view></template>
 </StudioShell>
</template>
<style>
.studio-details .studio-native-body{white-space:pre-line}
.studio-details .studio-detail-section{padding-top:18px;border-top:1px solid #e3ebef;gap:13px}
.studio-detail-article+.studio-detail-article,.studio-detail-step+.studio-detail-step{margin-top:12px}
.studio-native .studio-detail-nav{display:flex;flex-wrap:wrap;gap:5px 9px}
.studio-native .studio-detail-nav button{min-height:40px;font-size:12px;padding:7px 9px;background:#f2f7fa;border-radius:10px}
.studio-native .studio-detail-tools{align-self:flex-start;text-align:left}
</style>
