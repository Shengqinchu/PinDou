<script setup lang="ts">
defineOptions({options:{styleIsolation:'shared',virtualHost:true}});
import { computed,ref } from 'vue';
import {onViewShow as onShow} from '../../utils/studio-view-lifecycle';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import StudioPatchOffer from '../StudioPatchOffer.vue';
import {usePatchPromotion} from '../../utils/studio-patch-promotion';
import { useStudioNative } from '../../utils/studio-native';
import { refreshStudioContent,studioWords,studioPhoto } from '../../utils/studio-content';
import {pressTo,pressNavigate} from '../../utils/press';
import {readStudioCached} from '../../utils/studio-cache';
import {calendarPath,emptyBooking} from '../../utils/studio-booking';
import {prefetchShop} from '../../utils/shop-catalog';
const {language,width,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const words=(module:Parameters<typeof studioWords>[0],key:string)=>say(studioWords(module,key));
const photo=computed(studioPhoto),imageFailed=ref(false);
const {offer,open,dismiss}=usePatchPromotion(true);
function patchVisit(){dismiss();pressTo('/pages/studio/visit?experience=patch');}
function visit(){pressTo('/pages/studio/visit');}
function bookings(){pressNavigate('/pages/studio/reservations');}
function details(){pressTo('/pages/studio/details');}
function patterns(){pressTo('/pages/tools/pattern');}
function shop(){pressTo('/pages/shop/index');}
// After the home settles, quietly load the next likely pages: open booking times and the shop.
let warmTimer:ReturnType<typeof setTimeout>|undefined;
onShow(()=>{void refreshStudioContent();clearTimeout(warmTimer);warmTimer=setTimeout(()=>{void readStudioCached(calendarPath(emptyBooking()),'',15000).catch(()=>{});prefetchShop();},900);});
</script>
<template>
 <StudioShell id="studio-home-pane" fitted embedded :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle">
  <view class="studio-native-main studio-home">
   <view class="studio-native-heading"><text class="studio-native-site">{{words('home','hamilton_ontario_canada_fbf034')}}</text><text class="studio-native-title">{{words('home','a_little_time_all_yours_9e9d60')}}<text class="studio-home-title-line">{{words('home','make_something_lovely_04db64')}}</text></text></view>
   <image v-if="!imageFailed" class="studio-home-photo" :src="photo" mode="widthFix" :aria-label="words('home','sunlit_worktables_and_a_wall_of_bead_46e326')" @error="imageFailed=true"/>
   <button :hover-stay-time="180" :hover-start-time="0" class="studio-native-primary" hover-class="studio-native-pressed" @tap="visit"><StudioGlyph name="calendar"/><text class="studio-native-primary-label">{{words('home','come_create_2eee81')}}</text><view class="studio-native-button-arrow"><StudioGlyph name="arrow" :size="18"/></view></button>
   <view class="studio-home-shortcuts"><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" @tap="bookings"><StudioGlyph name="clock"/><text>{{words('account','my_reservations')}}</text></button><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" @tap="details"><StudioGlyph name="pin"/><text>{{words('home','studio_details_7c4089')}}</text></button><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" @tap="shop"><StudioGlyph name="bag"/><text>{{words('miniapp','shop_entry')}}</text></button><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" @tap="patterns"><StudioGlyph name="grid"/><text>{{words('miniapp','pattern_entry')}}</text></button></view>
   <text class="studio-native-body studio-native-small">{{words('flow','confirmation_note')}}</text>
  </view>
  <template #overlay><StudioPatchOffer v-if="open&&offer" :offer="offer" :language="language" @dismiss="dismiss" @book="patchVisit"/></template>
 </StudioShell>
</template>
