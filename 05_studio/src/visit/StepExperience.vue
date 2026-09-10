<script setup lang="ts">
import LiftTitle from '../components/LiftTitle.vue';
import { PhClock,PhSun } from '@phosphor-icons/vue';
import { say } from '../state';
import { copy,words,prices } from './copy';
import MoneyText from '../components/MoneyText.vue';
import type { VisitFlow } from './useVisitFlow';
defineProps<{flow:VisitFlow}>();
</script>
<template>
 <div class="visit-stage-title"><LiftTitle as="h2" :text="say(copy.experience)"/></div>
 <fieldset class="visit-plans"><legend class="sr-only">{{say(copy.experience)}}</legend>
  <label :class="{selected:flow.draft.booking.plan==='hourly'}"><input type="radio" name="visit-plan" value="hourly" :checked="flow.draft.booking.plan==='hourly'" @change="flow.choosePlan('hourly')"/><i class="visit-plan-dot" aria-hidden="true"/><PhClock/><strong>{{say(words.by_the_hour_5300b2)}}</strong><span>{{say(words.at_least_two_hours_9f144b)}}</span><div><MoneyText :text="'CAD '+prices.hourly"/><small>{{say(words.hour_person_7ea78f)}}</small></div></label>
  <label :class="{selected:flow.draft.booking.plan==='day'}"><input type="radio" name="visit-plan" value="day" :checked="flow.draft.booking.plan==='day'" @change="flow.choosePlan('day')"/><i class="visit-plan-dot" aria-hidden="true"/><PhSun/><strong>{{say(words.a_day_of_making_01d6e2)}}</strong><span>{{say(copy.day_until_close)}}</span><div><MoneyText :text="'CAD '+prices.day_one"/><small>{{say(words.one_guest_684bef)}}</small></div><dl class="visit-day-prices"><div><dt>{{say(copy.two)}}</dt><dd><MoneyText :text="'CAD '+prices.day_two"/></dd></div><div><dt>{{say(copy.three)}}</dt><dd><MoneyText :text="'CAD '+prices.day_three"/></dd></div></dl></label>
 </fieldset>
 <div class="visit-promotions">
  <article class="visit-prepaid"><h3>{{say(words.prepaid_hours_ask_in_the_studio_f180a7)}}</h3><strong><MoneyText :text="say(words.ca7_hour_c87a20)"/></strong><p>{{say(words.prepay_at_least_10_hours_and_at_8815bf)}}</p></article>
  <article class="visit-school-offer"><h3>{{say(words.backtoschool_until_october_1_42119e)}}</h3><div class="visit-promotion-item"><p>{{say(words.four_hours_of_making_for_two_8bb2b0)}}</p><strong><MoneyText :text="'CAD '+prices.school_two_four_hours"/></strong></div><div class="visit-promotion-item"><p>{{say(words.bead_cardholder_package_no_makingtime_limit_92105b)}}</p><strong><MoneyText :text="'CAD '+prices.school_card_holder"/><small>{{say(words.piece_ef469b)}}</small></strong></div></article>
 </div>
</template>
