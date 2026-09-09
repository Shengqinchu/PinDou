<script setup lang="ts">
import MoneyText from '../src/components/MoneyText.vue';
import { PhArrowRight,PhUsers,PhClock } from '@phosphor-icons/vue';
import { locale,say } from '../src/state';
import visit from '../src/content/pages-Visit.json';
import rates from '../src/content/experience-rates.json';
defineProps<{selected:boolean;disabled?:boolean}>();
defineEmits<{choose:[]}>();
const t=(zh:string,en:string)=>locale.value==='zh'?zh:en;
</script>
<template>
 <section class="flow-offer-section" :aria-label="t('套餐与储值','Offers and prepaid hours')">
  <button class="flow-duo-offer" type="button" :aria-pressed="selected" :disabled="disabled" @click="$emit('choose')">
   <span class="flow-offer-copy"><small>{{say(visit.backtoschool_until_october_1_42119e)}}</small><strong>{{say(visit.four_hours_of_making_for_two_8bb2b0)}}</strong><span class="flow-offer-facts"><span><PhUsers/>{{t('2 人','2 guests')}}</span><span><PhClock/>{{t('4 小时','4 hours')}}</span></span></span>
   <span class="flow-offer-price"><MoneyText :text="'CAD '+rates.school_two_four_hours"/><PhArrowRight/></span>
  </button>
  <details class="flow-prepaid-details"><summary>{{t('储值与其他体验','Prepaid hours & other experiences')}}</summary><div class="flow-prepaid-content">
   <article class="flow-prepaid-row"><div><h3>{{t('储值时长','Prepaid hours')}}</h3><p>{{say(visit.prepay_at_least_10_hours_and_at_8815bf)}}</p></div><strong><MoneyText :text="say(visit.ca7_hour_c87a20)"/></strong></article>
   <article class="flow-cardholder-row"><p>{{say(visit.bead_cardholder_package_no_makingtime_limit_92105b)}}</p><strong><MoneyText :text="'CAD '+rates.school_card_holder"/><small>{{say(visit.piece_ef469b)}}</small></strong></article>
  </div></details>
 </section>
</template>
