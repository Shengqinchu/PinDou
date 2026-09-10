<script setup lang="ts">
import LiftTitle from '../components/LiftTitle.vue';
import { ref } from 'vue';
import { PhClock,PhSun,PhUser,PhUsers,PhArrowRight,PhArrowLeft } from '@phosphor-icons/vue';
import { say,formatCopy } from '../state';
import { copy,words,prices,guestCount } from './copy';
import MoneyText from '../components/MoneyText.vue';
import InfoTip from '../components/InfoTip.vue';
import PickerTransition from './PickerTransition.vue';
import type { VisitFlow } from './useVisitFlow';
defineProps<{flow:VisitFlow}>();
const details=ref(false);
</script>
<template>
 <PickerTransition :view="details?'details':'experience'" :label="say(details?copy.prepaid:copy.experience)">
  <template v-if="!details">
   <div class="visit-stage-title"><LiftTitle as="h2" :text="say(copy.experience)"/></div>
   <fieldset class="visit-plans"><legend class="sr-only">{{say(copy.experience)}}</legend>
    <label :class="{selected:flow.draft.booking.plan==='hourly'&&!flow.draft.offer}"><input type="radio" name="visit-plan" value="hourly" :checked="flow.draft.booking.plan==='hourly'&&!flow.draft.offer" @change="flow.choosePlan('hourly')"/><PhClock/><strong>{{say(words.by_the_hour_5300b2)}}</strong><span>{{say(words.at_least_two_hours_9f144b)}}</span><div><MoneyText :text="'CAD '+prices.hourly"/><small>{{say(words.hour_person_7ea78f)}}</small></div></label>
    <label :class="{selected:flow.draft.booking.plan==='day'&&!flow.draft.offer}"><input type="radio" name="visit-plan" value="day" :checked="flow.draft.booking.plan==='day'&&!flow.draft.offer" @change="flow.choosePlan('day')"/><PhSun/><strong>{{say(words.a_day_of_making_01d6e2)}}</strong><span>{{say(copy.day_until_close)}}</span><div><MoneyText v-if="flow.draft.booking.guests<=3" :text="'CAD '+(flow.draft.booking.guests===2?prices.day_two:flow.draft.booking.guests===3?prices.day_three:prices.day_one)"/><small v-else>{{say(copy.more_guests)}}</small><InfoTip :label="say(copy.group_prices)"><p>{{say(copy.two)}} <MoneyText :text="'CAD '+prices.day_two"/></p><p>{{say(copy.three)}} <MoneyText :text="'CAD '+prices.day_three"/></p><p>{{say(copy.more_guests)}}</p></InfoTip></div></label>
   </fieldset>
   <fieldset class="visit-guests" :class="{many:(flow.calendar?.max_guests_per_group||4)>4}"><legend class="sr-only">{{say(copy.guests)}}</legend><div><button v-for="n in ((flow.calendar?.max_guests_per_group||4)>6?4:flow.calendar?.max_guests_per_group||4)" :key="n" type="button" :aria-label="guestCount(n)" :aria-pressed="flow.draft.booking.guests===n" @click="flow.chooseGuests(n)"><PhUser/><span class="visit-guest-word">{{guestCount(n)}}</span><span class="visit-guest-number" aria-hidden="true">{{n}}</span></button><label v-if="(flow.calendar?.max_guests_per_group||4)>6">{{say(copy.guests)}}<input type="number" min="1" :max="flow.calendar?.max_guests_per_group" :value="flow.draft.booking.guests" @input="flow.chooseGuests(Number(($event.target as HTMLInputElement).value))"/></label></div></fieldset>
   <button v-for="offer in flow.calendar?.offers" :key="offer.id" class="visit-duo-offer" type="button" :disabled="!!flow.loadError" :aria-pressed="flow.draft.offer===offer.id" @click="flow.chooseOffer(offer)"><span><small>{{say(words.backtoschool_until_october_1_42119e)}}</small><strong>{{say(offer.label)}}</strong><span class="visit-offer-facts"><span><PhUsers/>{{guestCount(offer.guests)}}</span><span><PhClock/>{{formatCopy(copy.hour_count,{v0:offer.minutes/60})}}</span></span></span><span class="visit-offer-price"><MoneyText :text="offer.currency+' '+offer.amount"/><PhArrowRight/></span></button>
   <button type="button" class="visit-details-toggle" @click="details=true">{{say(copy.prepaid)}}<PhArrowRight/></button>
  </template>
  <template v-else>
   <div class="visit-stage-title"><LiftTitle as="h2" :text="say(copy.prepaid)"/></div>
   <div class="visit-prepaid"><article><div><h3>{{say(copy.prepaid_hours)}}</h3><p>{{say(words.prepay_at_least_10_hours_and_at_8815bf)}}</p></div><strong><MoneyText :text="say(words.ca7_hour_c87a20)"/></strong></article><article><p>{{say(words.bead_cardholder_package_no_makingtime_limit_92105b)}}</p><strong><MoneyText :text="'CAD '+prices.school_card_holder"/><small>{{say(words.piece_ef469b)}}</small></strong></article></div>
   <button type="button" class="visit-details-toggle" @click="details=false"><PhArrowLeft/>{{say(copy.back_experience)}}</button>
  </template>
 </PickerTransition>
</template>
