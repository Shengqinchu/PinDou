<script setup lang="ts">
import { computed } from 'vue';
import { PhArrowLeft,PhClock,PhCheck } from '@phosphor-icons/vue';
import { say,locale,formatCopy,prettyDate } from '../state';
import { copy } from './copy';
import PickerTransition from './PickerTransition.vue';
import ReservationHoursNote from '../components/ReservationHoursNote.vue';
import type { VisitFlow } from './useVisitFlow';
const props=defineProps<{flow:VisitFlow}>();
const hours=computed({get:()=>props.flow.duration/60,set:value=>props.flow.duration=Number(value)*60});
</script>
<template>
 <PickerTransition :view="flow.pickerView" :label="say(flow.pickerView==='date'?copy.choose_date:copy.choose_time)">
  <template v-if="flow.pickerView==='date'">
   <div class="visit-stage-title"><h2>{{say(copy.time)}}</h2><small>{{say(copy.next_two_weeks)}}</small></div>
   <fieldset class="visit-dates"><legend class="sr-only">{{say(copy.choose_date)}}</legend><div><button v-for="d in flow.calendar?.days" :key="d.date" type="button" :disabled="flow.loading||!flow.availableStarts(d,true).length" :aria-pressed="flow.draft.booking.date===d.date" :aria-label="prettyDate(d.date)" @click="flow.chooseDate(d.date)"><span>{{new Intl.DateTimeFormat(locale==='zh'?'zh-CN':'en-CA',{weekday:'short'}).format(new Date(d.date+'T12:00:00'))}}</span><strong>{{d.date.slice(8)}}</strong><small>{{d.closed?say(copy.closed):d.date.slice(5,7)+'/'+d.date.slice(8)}}</small></button></div></fieldset>
  </template>
  <template v-else>
   <div class="visit-picked-date"><h2>{{prettyDate(flow.draft.booking.date)}}</h2><button type="button" @click="flow.pickerView='date'"><PhArrowLeft/>{{say(copy.change_date)}}</button></div>
   <p v-if="flow.offer" class="visit-fixed-duration"><PhClock/>{{formatCopy(copy.hour_count,{v0:flow.offer.minutes/60})}}<small>{{say(copy.fixed_duration)}}</small></p>
   <fieldset v-if="flow.draft.booking.plan==='hourly'&&!flow.offer" class="visit-duration"><legend>{{say(copy.how_long)}}</legend><div><button v-for="n in [120,150,180,210,240]" :key="n" type="button" :aria-pressed="flow.duration===n" @click="flow.duration=n">{{formatCopy(copy.hour_count,{v0:n/60})}}</button><label><span>{{say(copy.other_duration)}}</span><input v-model.number="hours" type="number" min="2" max="24" step="0.5" :aria-label="say(copy.hours)"/></label></div></fieldset>
   <fieldset class="visit-times"><legend>{{say(copy.arrive)}}<small class="visit-regular-end">{{say(copy.regular_end)}} {{flow.day?.close}}</small></legend><div><button v-for="s in flow.starts" :key="s.start" type="button" :disabled="flow.loading" :aria-pressed="flow.draft.booking.start===s.start" @click="flow.chooseTime(s.start)">{{s.start}}</button></div><p v-if="!flow.starts.length&&!flow.loading">{{say(flow.offer?copy.no_duo_time:copy.no_time)}}</p></fieldset>
   <p class="visit-chosen" :class="{empty:!flow.selected}" aria-live="polite"><template v-if="flow.selected"><PhCheck/>{{flow.draft.booking.start}}–{{flow.draft.booking.end}}</template></p>
  </template>
 </PickerTransition>
 <ReservationHoursNote/>
</template>
