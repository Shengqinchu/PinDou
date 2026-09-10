<script setup lang="ts">
import { contentModule } from "../content-store";
const copyText = contentModule("components-ReservationCalendar", copyTextDefault);

import copyTextDefault from "../content/components-ReservationCalendar.json";
import ReservationHoursNote from './ReservationHoursNote.vue';
import InfoTip from './InfoTip.vue';
import { say } from "../state";

import {
  computed,
  nextTick,
  ref,
  watch,
  onMounted,
  onBeforeUnmount,
} from "vue";
import { PhArrowLeft, PhArrowRight } from "@phosphor-icons/vue";
import { prettyDate, tr } from "../state";
import {
  clock,
  minutes,
  validSelection,
  type ReservationBooking,
  type ReservationCalendar,
} from "../reservations";
const props = defineProps<{
  calendar: ReservationCalendar;
  booking: ReservationBooking;
  disabled?: boolean;
  compact?: boolean;
}>();
const emit = defineEmits<{
  select: [value: { date: string; start: string; end: string }];
}>();
const offset = ref(0),
  pageSize = ref(7),
  focusIndex = ref(-1),
  choosingEnd = ref(false),
  message = ref("");
const table = ref<HTMLElement>();
const days = computed(() =>
  props.calendar.days.slice(offset.value, offset.value + pageSize.value),
);
const columns = computed(() => days.value.length);
const rows = computed(
  () => props.calendar.days[0]?.slots.map((s) => s.start) || [],
);
const endBoundary=computed(()=>props.calendar.days[0]?.slots.at(-1)?.end||'');
let resize: ResizeObserver | undefined;
onMounted(() => {
  resize = new ResizeObserver(([entry]) => {
    const size =
      entry.contentRect.width < 420 ? 3 : entry.contentRect.width < 720 ? 4 : 7;
    if (size !== pageSize.value) {
      offset.value = Math.floor(offset.value / size) * size;
      pageSize.value = size;
      revealSelected();
    }
  });
  if (table.value) resize.observe(table.value);
});
onBeforeUnmount(() => resize?.disconnect());
function weekday(day: string) {
  const date = new Date(day + "T12:00:00Z");
  return new Intl.DateTimeFormat(say(copyText.enca_9cd218), {
    weekday: "short",
    timeZone: "UTC",
  }).format(date);
}
function selected(day: string, time: string) {
  return (
    props.booking.date === day &&
    minutes(time) >= minutes(props.booking.start) &&
    minutes(time) < minutes(props.booking.end)
  );
}
function available(di: number, ri: number) {
  return !!days.value[di]?.slots[ri]?.available && !props.disabled;
}
function choose(di: number, ri: number) {
  if (!available(di, ri)) return;
  const day = days.value[di],
    start = day.slots[ri].start;
  let booking = {
    ...props.booking,
    date: day.date,
    start,
    end: clock(minutes(start) + 120),
  };
  if (props.booking.plan === "day") booking.end = day.close;
  else if (
    choosingEnd.value &&
    props.booking.date === day.date &&
    minutes(start) + 30 - minutes(props.booking.start) >= 120
  ) {
    booking = { ...props.booking, end: day.slots[ri].end };
    choosingEnd.value = false;
  } else choosingEnd.value = true;
  if (!validSelection(props.calendar, booking)) {
    message.value = say(
      copyText.choose_an_earlier_or_another_available_time_f98d07,
    );
    return;
  }
  message.value = "";
  emit("select", {
    date: booking.date,
    start: booking.start,
    end: booking.end,
  });
}
async function moveWeek(delta: number) {
  offset.value = Math.max(
    0,
    Math.min(
      Math.floor((props.calendar.days.length - 1) / pageSize.value) *
        pageSize.value,
      offset.value + delta * pageSize.value,
    ),
  );
  await nextTick();
  resetFocus();
}
function resetFocus() {
  focusIndex.value =
    Array.from({ length: rows.value.length * columns.value }, (_, i) => i).find(
      (i) => available(i % columns.value, Math.floor(i / columns.value)),
    ) ?? -1;
}
function revealSelected(){const index=props.calendar.days.findIndex(d=>d.date===props.booking.date);if(index>=0)offset.value=Math.floor(index/pageSize.value)*pageSize.value;}
watch(()=>props.booking.date,revealSelected,{immediate:true});
function keyboard(event: KeyboardEvent, index: number) {
  const delta =
    event.key === "ArrowRight"
      ? 1
      : event.key === "ArrowLeft"
        ? -1
        : event.key === "ArrowDown"
          ? columns.value
          : event.key === "ArrowUp"
            ? -columns.value
            : 0;
  if (!delta) return;
  event.preventDefault();
  let target = index + delta;
  while (target >= 0 && target < rows.value.length * columns.value) {
    if (
      Math.abs(delta) === 1 &&
      Math.floor(target / columns.value) !== Math.floor(index / columns.value)
    )
      break;
    if (available(target % columns.value, Math.floor(target / columns.value))) {
      focusIndex.value = target;
      table.value
        ?.querySelector<HTMLButtonElement>('[data-cell="' + target + '"]')
        ?.focus();
      return;
    }
    target += delta;
  }
}
watch(() => [props.calendar, props.disabled, columns.value], resetFocus, {
  immediate: true,
});
watch(
  () => props.booking.plan,
  () => {
    choosingEnd.value = false;
    message.value = "";
  },
);
</script>
<template>
  <div class="reservation-calendar" :class="{'is-compact':compact}">
    <div class="reservation-legend">
      <span><i />{{ say(copyText.available_to_book_9bb918) }}</span
      ><span><i class="chosen" />{{ say(copyText.your_selection_0fc834) }}</span
      ><span><i class="closed" />{{ say(copyText.unavailable_fb3489) }}</span>
    </div>
    <div class="reservation-week-nav">
      <button
        type="button"
        class="icon-button"
        :disabled="offset === 0 || disabled"
        :aria-label="say(copyText.previous_dates_314fc5)"
        @click="moveWeek(-1)"
      >
        <PhArrowLeft />
      </button>
      <div class="reservation-date-range">
        <strong>{{ say(copyText.the_next_two_weeks_59cce3) }}</strong
        ><span
          >{{ days[0]?.date.slice(5).replace("-", "/") }} —
          {{ days[days.length - 1]?.date.slice(5).replace("-", "/") }}</span
        >
      </div>
      <InfoTip v-if="compact" :label="say(copyText.reservation_timetable_use_arrow_keys_to_move_3bb451)"><p>{{say(booking.plan==='day'?copyText.day_selection_help:copyText.choose_a_start_time_for_a_twohour_a3470d)}}</p><p>{{say(copyText.all_times_are_local_to_hamilton_the_8a3607)}}</p></InfoTip>
      <button
        type="button"
        class="icon-button"
        :disabled="offset + pageSize >= calendar.days.length || disabled"
        :aria-label="say(copyText.next_dates_4c8209)"
        @click="moveWeek(1)"
      >
        <PhArrowRight />
      </button>
    </div>
    <p v-if="!compact" class="reservation-grid-help">
      {{ say(copyText.choose_a_start_time_for_a_twohour_a3470d) }}
    </p>
    <div ref="table" class="reservation-grid-scroll">
      <table
        class="reservation-grid"
        role="grid"
        :aria-label="
          say(copyText.reservation_timetable_use_arrow_keys_to_move_3bb451)
        "
      >
        <thead>
          <tr>
            <th scope="col">{{ say(copyText.time_296653) }}</th>
            <th v-for="day in days" :key="day.date" scope="col">
              <span>{{ weekday(day.date) }}</span
              ><strong>{{ day.date.slice(5).replace("-", "/") }}</strong>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(time, ri) in rows" :key="time">
            <th scope="row">{{ time }}</th>
            <td
              v-for="(day, di) in days"
              :key="day.date"
              :aria-selected="selected(day.date, time)"
            >
              <button
                type="button"
                :data-cell="ri * columns + di"
                :data-date="day.date"
                :data-time="time"
                :tabindex="focusIndex === ri * columns + di ? 0 : -1"
                :disabled="!available(di, ri)"
                :class="{
                  chosen: selected(day.date, time),
                  unavailable: !day.slots[ri]?.available,
                  start: selected(day.date, time) && booking.start === time,
                }"
                :aria-label="
                  prettyDate(day.date) +
                  ' ' +
                  time +
                  '—' +
                  day.slots[ri]?.end +
                  ' ' +
                  (day.slots[ri]?.available
                    ? say(copyText.available_d07da8)
                    : say(copyText.unavailable_e939b7))
                "
                @focus="focusIndex = ri * columns + di"
                @keydown="keyboard($event, ri * columns + di)"
                @click="choose(di, ri)"
              >
                <span
                  v-if="selected(day.date, time) && booking.start === time"
                  >{{ say(copyText.start_ba3401) }}</span
                ><span
                  v-else-if="
                    selected(day.date, time) &&
                    booking.end === day.slots[ri]?.end
                  "
                  >{{ booking.end }} {{ say(copyText.end_c4265b) }}</span
                ><span v-else aria-hidden="true">{{
                  day.slots[ri]?.available ? "·" : "—"
                }}</span>
              </button>
            </td>
          </tr>
          <tr v-if="endBoundary" class="reservation-end-boundary"><th scope="row">{{endBoundary}}</th><td v-for="day in days" :key="day.date">{{!day.closed&&day.close===endBoundary?say(copyText.end_c4265b):'—'}}</td></tr>
        </tbody>
      </table>
    </div>
    <ReservationHoursNote/>
    <p v-if="message" class="form-error" role="alert">{{ message }}</p>
    <p v-if="!compact" class="reservation-hours">
      {{ say(copyText.all_times_are_local_to_hamilton_the_8a3607) }}
    </p>
  </div>
</template>
