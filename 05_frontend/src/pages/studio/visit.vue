<script setup lang="ts">
import { computed,reactive,ref } from 'vue';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import StudioCalendar from '../../components/StudioCalendar.vue';
import StudioSubmitConfirm from '../../components/StudioSubmitConfirm.vue';
import StudioNotificationChoices from '../../components/StudioNotificationChoices.vue';
import { useUserStore } from '../../store/studio-user';
import { useStudioNative } from '../../utils/studio-native';
import { useStudioVisit } from '../../utils/use-studio-visit';
import { studioWords,studioRate,bookingError,fillWords,studioPlanWords } from '../../utils/studio-content';
import { shortDate } from '../../utils/studio-booking';
import {usePatchPromotion} from '../../utils/studio-patch-promotion';
const {offer}=usePatchPromotion();
const user=useUserStore();
const {language,width,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const flow=reactive(useStudioVisit(language)),showNotes=ref(false);
const words=(module:Parameters<typeof studioWords>[0],key:string)=>say(studioWords(module,key));
const steps=['step_experience','step_time','step_contact'];
const methods=[{value:'wechat',key:'wechat_2941d2',field:'wechat_id_7a6e86'},{value:'email',key:'email_b6d15f',field:'email_address_a61e0e'},{value:'phone',key:'phone_ac7a62',field:'phone_number_15447d'},{value:'other',key:'another_way_f489b4',field:'contact_details_3b7403'}] as const;
const contacts=computed(()=>methods.map(item=>({...item,label:words('visit',item.key)})));
const contactIndex=computed(()=>Math.max(0,methods.findIndex(item=>item.value===flow.contact.contact_method)));
const guests=computed(()=>Array.from({length:flow.calendar?.max_guests_per_group||6},(_,i)=>({value:i+1,label:fillWords(studioWords('flow','guest_count'),language.value,{v0:i+1})})));
const guestLabel=computed(()=>guests.value.find(item=>item.value===flow.booking.guests)?.label||String(flow.booking.guests));
const error=computed(()=>['choose_first','choose_available'].includes(flow.errorCode)?words('flow',flow.errorCode):say(bookingError(flow.errorCode)));
const canContinue=computed(()=>!flow.locked&&(flow.step===0?!!flow.booking.plan:flow.selected));
function guestChange(event:{detail:{value:string}}){void flow.chooseGuests(guests.value[Number(event.detail.value)].value);}
function methodChange(event:{detail:{value:string}}){flow.contact.contact_method=methods[Number(event.detail.value)].value;flow.editing=true;}
function next(){if(flow.step<2)flow.navigate(flow.step+1);else void flow.submit();}
function editContact(){flow.editing=true;}
function offerInfo(){uni.showModal({title:words('flow','prepaid_details'),content:words('visit','prepay_at_least_10_hours_and_at_8815bf'),showCancel:false});}
</script>
<template>
 <StudioShell id="studio-shell" fitted :reset-key="flow.step" :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" @language="changeLanguage">
  <view :key="flow.step" class="studio-native-main studio-visit" :class="{'studio-visit--time':flow.step===1}">
   <view class="studio-visit-steps" :aria-label="words('flow','progress')"><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" v-for="(key,index) in steps" :key="key" :class="{'studio-visit-step--active':flow.step===index,'studio-visit-step--done':flow.step>index}" :disabled="flow.locked||index>flow.step" :aria-current="flow.step===index?'step':undefined" @tap="flow.navigate(index)"><text class="studio-visit-number">{{String(index+1).padStart(2,'0')}}</text><text>{{words('flow',key)}}</text></button></view>
   <text class="studio-native-title studio-visit-title">{{words('flow',flow.step===0?'experience':flow.step===1?'time':'contact')}}</text>
   <template v-if="flow.step===0">
    <view class="studio-visit-plans" role="radiogroup">
     <button :hover-stay-time="180" :hover-start-time="0" class="studio-plan" :class="{'studio-plan--selected':flow.booking.plan==='hourly'}" role="radio" :aria-checked="flow.booking.plan==='hourly'" hover-class="studio-native-pressed" @tap="flow.choosePlan('hourly')"><view class="studio-plan-top"><StudioGlyph name="clock" :size="19"/><text class="studio-plan-name">{{words('visit','by_the_hour_5300b2')}}</text><view class="studio-plan-radio"/></view><text class="studio-native-small studio-native-body">{{words('visit','at_least_two_hours_9f144b')}}</text><view class="studio-price"><text>{{studioRate('hourly')}}</text><text class="studio-price-currency">CAD</text><text class="studio-price-unit">{{words('visit','hour_person_7ea78f')}}</text></view></button>
     <button :hover-stay-time="180" :hover-start-time="0" class="studio-plan" :class="{'studio-plan--selected':flow.booking.plan==='day'}" role="radio" :aria-checked="flow.booking.plan==='day'" hover-class="studio-native-pressed" @tap="flow.choosePlan('day')"><view class="studio-plan-top"><StudioGlyph name="sun" :size="19"/><text class="studio-plan-name">{{words('visit','a_day_of_making_01d6e2')}}</text><view class="studio-plan-radio"/></view><text class="studio-native-small studio-native-body">{{words('flow','day_until_close')}}</text><view class="studio-price"><text>{{studioRate('day_one')}}</text><text class="studio-price-currency">CAD</text><text class="studio-price-unit">{{words('visit','one_guest_684bef')}}</text></view></button>

     <button class="studio-plan studio-plan-patch" :class="{'studio-plan--selected':flow.booking.plan==='patch'}" role="radio" :aria-checked="flow.booking.plan==='patch'" hover-class="studio-native-pressed" @tap="flow.choosePlan('patch')">
      <view class="studio-plan-top"><StudioGlyph name="patch" :size="19"/><text class="studio-plan-name">{{words('patch','patch')}}</text><view class="studio-plan-radio"/></view>
      <text class="studio-native-body studio-native-small">{{words('patch','description')}}</text>
      <view v-if="offer?.enabled" class="studio-patch-card-offer"><text>{{words('promotion','launch')}}</text><text>{{words('promotion',offer.remaining>0?'card':'exhausted')}}</text><text v-if="offer.remaining>0">{{fillWords(studioWords('promotion','remaining'),language,{v0:offer.remaining,v1:offer.quota})}}</text><text>{{words('promotion','bonus')}}</text></view>
     </button>
     <view class="studio-plan studio-plan-offers">
      <view class="studio-plan-top"><view class="studio-offer-prepaid"><text class="studio-native-label studio-native-small">{{words('flow','prepaid_title')}}</text><text class="studio-offer-price">{{words('visit','ca7_hour_c87a20')}}</text></view><button class="studio-offer-info studio-native-eye" hover-class="studio-native-pressed" :aria-label="words('flow','prepaid_details')" @tap="offerInfo"><StudioGlyph name="info" :size="19"/></button></view>
      <view class="studio-offer-divider"/>
      <text class="studio-native-label studio-native-small">{{words('flow','holiday_offer_title')}}</text>
      <text class="studio-native-small studio-offer-highlight">{{words('flow','holiday_new_guests')}}</text>
      <text class="studio-native-body studio-native-small">{{words('flow','holiday_bring_friends')}}</text>
     </view>
    </view>
    <view v-if="flow.booking.plan==='day'" class="studio-group-prices"><text>{{words('flow','two')}} · {{studioRate('day_two')}} CAD</text><text>{{words('flow','three')}} · {{studioRate('day_three')}} CAD</text></view>
    </template>
   <template v-else-if="flow.step===1">
    <view class="studio-visit-time-tools"><picker :range="guests" range-key="label" :value="Math.min(guests.length-1,Math.max(0,flow.booking.guests-1))" :disabled="flow.locked||flow.loading" @change="guestChange"><view class="studio-guest-control"><StudioGlyph name="user" :size="19"/><text>{{words('flow','guests')}} · {{guestLabel}}</text><text>⌄</text></view></picker><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-eye" :disabled="flow.loading||flow.locked" :aria-label="words('visit','refresh_timetable_491b53')" @tap="flow.loadCalendar(true)"><view v-if="flow.loading" class="studio-native-progress"/><StudioGlyph v-else name="refresh" :size="20"/></button></view>
    <text v-if="flow.calendarError" class="studio-native-error">{{words('flow','calendar_error')}}</text><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" v-if="flow.calendarError" class="studio-native-link" @tap="flow.loadCalendar(true)">{{words('flow','retry')}}</button>
    <StudioCalendar id="booking-calendar" v-if="flow.calendar" :calendar="flow.calendar" :booking="flow.booking" :disabled="flow.loading||flow.locked" :language="language" :width="width" @select="flow.select"/><text v-else class="studio-native-body">{{words('flow','checking')}}</text>
    <view v-if="flow.booking.start" class="studio-visit-selection"><StudioGlyph name="check" :size="18"/><text>{{shortDate(flow.booking.date,language)}} · {{flow.booking.start}}–{{flow.booking.end}}</text></view>
   </template>
   <template v-else>
    <view class="studio-visit-review"><view><text class="studio-native-label">{{words('flow','step_experience')}}</text><text>{{say(studioPlanWords(flow.booking.plan))}}</text><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-link" :disabled="flow.locked" @tap="flow.navigate(0)">{{words('flow','edit')}}</button></view><view><text class="studio-native-label">{{words('flow','step_time')}}</text><text>{{guestLabel}} · {{shortDate(flow.booking.date,language)}}<text class="studio-review-time">{{flow.booking.start}}–{{flow.booking.end}}</text></text><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-link" :disabled="flow.locked" @tap="flow.navigate(1)">{{words('flow','edit')}}</button></view></view>
    <template v-if="user.token">
     <text v-if="flow.contactLoading" class="studio-native-body">{{words('booking','loading')}}</text>
     <view v-if="flow.contactError"><text class="studio-native-error">{{words('booking','load_error')}}</text><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-link" @tap="flow.loadContact">{{words('booking','retry')}}</button></view>
     <view v-if="flow.profileConflict"><text class="studio-native-error">{{words('booking','changed')}}</text><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-link" :disabled="flow.locked" @tap="flow.useSaved">{{words('booking','use_latest')}}</button></view>
     <view v-if="flow.savedContact&&!flow.attempt" class="studio-saved-contact"><view><text class="studio-plan-name">{{flow.contact.name}}</text><text class="studio-native-body">{{contacts[contactIndex].label}} · {{flow.contact.contact}}</text></view><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-link" :disabled="flow.locked" @tap="editContact">{{words('flow','edit')}}</button></view>
     <view v-else-if="!flow.contactLoading||flow.attempt" class="studio-native-form">
      <label class="studio-native-field"><text>{{words('visit','guest_name_e468f6')}}</text><view class="studio-native-input"><input v-model="flow.contact.name" :disabled="flow.locked" :maxlength="80" :cursor-spacing="80" :adjust-position="true" :aria-label="words('visit','guest_name_e468f6')" @input="flow.editing=true"/></view></label>
      <view class="studio-contact-card"><picker :range="contacts" range-key="label" :value="contactIndex" :disabled="flow.locked" @change="methodChange"><view class="studio-contact-choice"><text class="studio-native-label">{{words('visit','contact_method_73d70a')}}</text><text>{{contacts[contactIndex].label}} ⌄</text></view></picker><label class="studio-native-field"><text>{{words('visit',contacts[contactIndex].field)}}</text><view class="studio-native-input"><input v-model="flow.contact.contact" :disabled="flow.locked" :maxlength="180" :cursor-spacing="80" :adjust-position="true" :aria-label="words('visit',contacts[contactIndex].field)" @input="flow.editing=true"/></view></label></view>
      <button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" v-if="flow.context?.profile.complete&&!flow.attempt" class="studio-native-link" @tap="flow.useSaved">{{words('booking','cancel')}}</button>
     </view>
     <button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-visit-notes-toggle" :aria-expanded="showNotes" :disabled="flow.locked" @tap="showNotes=!showNotes">{{showNotes?'−':'+'}} {{words('visit','anything_you_would_like_us_to_know_eef3ab')}}</button><textarea v-if="showNotes" v-model="flow.notes" class="studio-visit-notes" :disabled="flow.locked" :maxlength="1500" :cursor-spacing="90" :adjust-position="true" :aria-label="words('visit','anything_you_would_like_us_to_know_eef3ab')"/>
    </template>
    <view v-else class="studio-native-section"><text class="studio-native-subtitle">{{words('account','reservation_title')}}</text><text class="studio-native-body">{{words('account','draft_saved')}}</text></view>
    <text class="studio-native-body studio-native-small">{{words('flow','confirmation_note')}}</text>
    <StudioNotificationChoices v-if="user.token" compact :language="language" :method="flow.contact.contact_method" :contact="flow.contact.contact"/>
   </template>
   <text v-if="flow.errorCode" class="studio-native-error" role="alert">{{error}}</text>
  </view>
  <template #actions><view class="studio-visit-actions"><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" v-if="flow.step>0" class="studio-native-link" :disabled="flow.locked" @tap="flow.navigate(flow.step-1)"><StudioGlyph name="back" :size="18"/>{{words('flow','back')}}</button><button :hover-stay-time="180" :hover-start-time="0" class="studio-native-primary" :disabled="flow.sending||(flow.step<2&&!canContinue)||flow.contactLoading" hover-class="studio-native-pressed" @tap="next"><view v-if="flow.sending" class="studio-native-progress"/><text class="studio-native-primary-label">{{flow.sending?words('visit','sending_c40370'):flow.step===0?words('flow','next_time'):flow.step===1?words('flow','next_contact'):flow.attempt?words('visit','recover_reservation_12c189'):!user.token?words('account','continue_reservation'):words('visit','request_this_visit_611e11')}}</text><StudioGlyph v-if="!flow.sending" name="arrow" :size="19"/></button></view></template>
  <template #overlay><StudioSubmitConfirm id="submission-confirm" v-if="flow.confirmation" :review="flow.confirmation" :notification-loading="flow.notificationLoading" :notification-note="flow.notificationNote" :confirming="flow.confirming" @confirm="flow.confirmSubmission" @without-wechat="flow.confirmWithoutWechat" @dismiss="flow.dismissSubmission"/></template>
 </StudioShell>
</template>
