<script setup lang="ts">
import { PhArrowClockwise,PhCheck } from '@phosphor-icons/vue';
import { say,prettyDate } from '../state';
import { copy,words } from './copy';
import ReservationCalendar from '../components/ReservationCalendar.vue';
import GuestCountPicker from './GuestCountPicker.vue';
import type { VisitFlow } from './useVisitFlow';
defineProps<{flow:VisitFlow}>();
</script>
<template>
 <div class="visit-time-tools"><GuestCountPicker :model-value="flow.draft.booking.guests" :maximum="flow.calendar?.max_guests_per_group||6" :disabled="flow.locked" @update:model-value="flow.chooseGuests"/><button class="icon-button" type="button" :disabled="flow.loading||flow.locked" :aria-label="say(words.refresh_timetable_491b53)" @click="flow.load"><PhArrowClockwise :class="{spinning:flow.loading}"/></button><p class="visit-time-selection" aria-live="polite"><template v-if="flow.draft.booking.start"><PhCheck/>{{prettyDate(flow.draft.booking.date)}} · {{flow.draft.booking.start}}–{{flow.draft.booking.end}}</template><template v-else>{{say(words.choose_a_time_in_the_timetable_d988a8)}}</template></p></div>

 <ReservationCalendar v-if="flow.calendar" compact :calendar="flow.calendar" :booking="flow.draft.booking" :disabled="flow.loading||flow.locked" @select="flow.chooseInterval"/>
 <p v-else class="visit-table-loading">{{say(copy.checking)}}</p>
</template>
