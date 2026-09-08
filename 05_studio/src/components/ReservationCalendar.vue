<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
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
}>();
const emit = defineEmits<{
  select: [value: { date: string; start: string; end: string }];
}>();
const week = ref(0),
  focusIndex = ref(-1),
  choosingEnd = ref(false),
  message = ref("");
const table = ref<HTMLElement>();
const days = computed(() =>
  props.calendar.days.slice(week.value * 7, week.value * 7 + 7),
);
const rows = Array.from({ length: 24 }, (_, i) => clock(600 + i * 30));
function weekday(day: string) {
  const date = new Date(day + "T12:00:00Z");
  return new Intl.DateTimeFormat(tr("zh-CN", "en-CA"), {
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
    message.value = tr(
      "这里无法安排至少两小时，请选择更早或其他可用时段。",
      "Choose an earlier or another available time for a visit of at least two hours.",
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
  week.value = Math.max(0, Math.min(1, week.value + delta));
  await nextTick();
  resetFocus();
}
function resetFocus() {
  focusIndex.value =
    Array.from({ length: 168 }, (_, i) => i).find((i) =>
      available(i % 7, Math.floor(i / 7)),
    ) ?? -1;
}
function keyboard(event: KeyboardEvent, index: number) {
  const delta =
    event.key === "ArrowRight"
      ? 1
      : event.key === "ArrowLeft"
        ? -1
        : event.key === "ArrowDown"
          ? 7
          : event.key === "ArrowUp"
            ? -7
            : 0;
  if (!delta) return;
  event.preventDefault();
  let target = index + delta;
  while (target >= 0 && target < 168) {
    if (
      Math.abs(delta) === 1 &&
      Math.floor(target / 7) !== Math.floor(index / 7)
    )
      break;
    if (available(target % 7, Math.floor(target / 7))) {
      focusIndex.value = target;
      table.value
        ?.querySelector<HTMLButtonElement>('[data-cell="' + target + '"]')
        ?.focus();
      return;
    }
    target += delta;
  }
}
watch(() => [props.calendar, props.disabled], resetFocus, { immediate: true });
watch(
  () => props.booking.plan,
  () => {
    choosingEnd.value = false;
    message.value = "";
  },
);
</script>
<template>
  <div class="reservation-calendar">
    <div class="reservation-week-nav">
      <button
        class="icon-button"
        :disabled="week === 0 || disabled"
        :aria-label="tr('上一周', 'Previous week')"
        @click="moveWeek(-1)"
      >
        <PhArrowLeft />
      </button>
      <div>
        <strong>{{ tr("未来两周", "The next two weeks") }}</strong
        ><span
          >{{ days[0]?.date.slice(5).replace("-", "/") }} —
          {{ days[6]?.date.slice(5).replace("-", "/") }}</span
        >
      </div>
      <button
        class="icon-button"
        :disabled="week === 1 || disabled"
        :aria-label="tr('下一周', 'Next week')"
        @click="moveWeek(1)"
      >
        <PhArrowRight />
      </button>
    </div>
    <div class="reservation-legend">
      <span><i />{{ tr("可以申请", "Available to request") }}</span
      ><span><i class="chosen" />{{ tr("已选时段", "Your selection") }}</span
      ><span><i class="closed" />{{ tr("不可预约", "Unavailable") }}</span>
    </div>
    <p class="reservation-grid-help">
      {{
        tr(
          "点击开始时间，默认选择两小时；再点同一天较晚的格子可延长。手机可左右滑动查看日期。",
          "Choose a start time for a two-hour visit, then a later cell to extend it. Swipe sideways on a phone to see more dates.",
        )
      }}
    </p>
    <div ref="table" class="reservation-grid-scroll">
      <table
        class="reservation-grid"
        role="grid"
        :aria-label="
          tr(
            '预约时间表，使用方向键移动，回车选择',
            'Reservation timetable. Use arrow keys to move and Enter to select.',
          )
        "
      >
        <thead>
          <tr>
            <th scope="col">{{ tr("时间", "Time") }}</th>
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
                :data-cell="ri * 7 + di"
                :tabindex="focusIndex === ri * 7 + di ? 0 : -1"
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
                    ? tr('可选', 'available')
                    : tr('不可预约', 'unavailable'))
                "
                @focus="focusIndex = ri * 7 + di"
                @keydown="keyboard($event, ri * 7 + di)"
                @click="choose(di, ri)"
              >
                <span
                  v-if="selected(day.date, time) && booking.start === time"
                  >{{ tr("开始", "Start") }}</span
                ><span
                  v-else-if="
                    selected(day.date, time) &&
                    booking.end === day.slots[ri]?.end
                  "
                  >{{ tr("结束", "End") }}</span
                ><span v-else aria-hidden="true">{{
                  day.slots[ri]?.available ? "·" : "—"
                }}</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="message" class="form-error" role="alert">{{ message }}</p>
    <p class="reservation-hours">
      {{
        tr(
          "均为汉密尔顿当地时间。每天 10:00–22:00；周三 16:00 后、周四 18:00 后不可预约。",
          "All times are local to Hamilton. Daily 10am–10pm; unavailable after 4pm on Wednesdays and 6pm on Thursdays.",
        )
      }}
    </p>
  </div>
</template>
