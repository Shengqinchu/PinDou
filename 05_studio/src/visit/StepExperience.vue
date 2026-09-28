<script setup lang="ts">
import LiftTitle from '../components/LiftTitle.vue';
import { PhClock,PhSun,PhFlower } from '@phosphor-icons/vue';
import { patchCopy } from '../patch-reservations';
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
  <label :class="{selected:flow.draft.booking.plan==='patch'}"><input type="radio" name="visit-plan" value="patch" :checked="flow.draft.booking.plan==='patch'" @change="flow.choosePlan('patch')"/><i class="visit-plan-dot" aria-hidden="true"/><PhFlower/><strong>{{say(patchCopy.patch)}}</strong><span>{{say(patchCopy.description)}}</span></label>
 <div class="visit-promotions visit-combined-offers">
  <article class="visit-prepaid"><h3>{{say(words.prepaid_hours_ask_in_the_studio_f180a7)}}</h3><strong><MoneyText :text="say(words.ca7_hour_c87a20)"/></strong><p>{{say(words.prepay_at_least_10_hours_and_at_8815bf)}}</p></article>
  <article class="visit-school-offer"><h3>{{say(words.backtoschool_until_october_1_42119e)}}</h3><div class="visit-promotion-item"><p>{{say(words.four_hours_of_making_for_two_8bb2b0)}}</p><strong><MoneyText :text="'CAD '+prices.school_two_four_hours"/></strong></div><div class="visit-promotion-item"><p>{{say(words.bead_cardholder_package_no_makingtime_limit_92105b)}}</p><strong><MoneyText :text="'CAD '+prices.school_card_holder"/><small>{{say(words.piece_ef469b)}}</small></strong></div></article>
 </div>
 </fieldset>
</template>
<style>
/* One informational offer card shares the same grid as the three choices. */
.visit-plans>.visit-combined-offers{display:flex;flex-direction:column;gap:0;margin:0;background:#f5f7f5;border:1px solid #e0e6e2;border-radius:14px;min-width:0;padding:17px 20px}
.visit-plans .visit-combined-offers>article{border:0;border-radius:0;padding:0;background:transparent}
.visit-plans .visit-combined-offers>article+article{border-top:1px solid #dfe5e1;margin-top:14px;padding-top:14px}
.visit-combined-offers h3{margin-bottom:6px}
.visit-combined-offers strong{font-size:22px}
.visit-combined-offers .visit-promotion-item+.visit-promotion-item{margin-top:8px}
@media(min-width:1400px) and (min-height:850px){.visit-plans>.visit-combined-offers{padding:22px 28px;border-radius:18px}.visit-combined-offers strong{font-size:26px}}
@media(max-width:700px){.visit-flow-page .visit-plans{grid-template-columns:1fr}.visit-flow-page .visit-plans>label{padding:16px}.visit-flow-page .visit-plans label>span{min-height:0;font-size:13px}.visit-plans>.visit-combined-offers{padding:16px}.visit-combined-offers p{font-size:12px}.visit-combined-offers .visit-promotion-item{display:flex}.visit-combined-offers .visit-promotion-item p{max-width:65%}.visit-combined-offers .visit-promotion-item strong{font-size:21px}}
</style>
