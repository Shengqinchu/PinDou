<script setup lang="ts">
import {
  computed,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from "vue";
import { PhArrowUpRight, PhCheck, PhMapPin } from "@phosphor-icons/vue";
import InquiryForm, { type BookingDraft } from "../components/InquiryForm.vue";
import {
  hamiltonDate,
  mapsUrl,
  media,
  plusDays,
  prettyDate,
  tr,
} from "../state";
const clock = ref(new Date());
const localNow = computed(() => {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Toronto",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(clock.value);
  const part = (name: string) =>
    parts.find((value) => value.type === name)?.value;
  return {
    date: `${part("year")}-${part("month")}-${part("day")}`,
    time: `${part("hour")}:${part("minute")}`,
  };
});
const today = computed(() => localNow.value.date);
const booking = reactive<BookingDraft>({
  date: plusDays(hamiltonDate(), 1),
  start: "14:00",
  end: "16:00",
  guests: 1,
  plan: "hourly",
});
const times = Array.from(
  { length: 27 },
  (_, i) =>
    `${String(10 + Math.floor(i / 2)).padStart(2, "0")}:${i % 2 ? "30" : "00"}`,
);
const startTimes = computed(() => {
  if (!booking.date || booking.date < today.value) return [];
  return times
    .slice(0, -1)
    .filter(
      (time) => booking.date !== today.value || time > localNow.value.time,
    );
});
const endTimes = computed(() =>
  booking.start ? times.filter((time) => time > booking.start) : [],
);
watch(
  [startTimes, () => booking.start],
  () => {
    if (!startTimes.value.includes(booking.start))
      booking.start = startTimes.value[0] || "";
    if (!endTimes.value.includes(booking.end))
      booking.end =
        endTimes.value[Math.min(1, endTimes.value.length - 1)] || "";
  },
  { immediate: true },
);
let clockTimer: ReturnType<typeof setInterval> | undefined;
onMounted(() => {
  clockTimer = setInterval(() => (clock.value = new Date()), 30000);
});
onBeforeUnmount(() => clearInterval(clockTimer));
const plans = computed(() => [
  {
    id: "hourly" as const,
    name: tr("按时体验", "By the hour"),
    value: "8",
    unit: tr("/ 人 / 小时", "/ person / hour"),
  },
  {
    id: "day" as const,
    name: tr("单人全天", "A day for one"),
    value: "49.9",
    unit: tr("/ 人", "/ person"),
  },
  {
    id: "pair" as const,
    name: tr("双人全天", "A day for two"),
    value: "88.8",
    unit: tr("/ 两人", "/ pair"),
  },
]);
watch(
  () => booking.plan,
  (value) => {
    if (value === "pair") booking.guests = 2;
    if (value === "day") booking.guests = 1;
  },
);
const summary = computed(() => [
  booking.date
    ? prettyDate(booking.date) + ` · ${booking.start}–${booking.end}`
    : tr("请选择日期", "Choose a date"),
  `${booking.guests} ${tr("人", booking.guests === 1 ? "guest" : "guests")} · ${plans.value.find((p) => p.id === booking.plan)?.name}`,
  tr(
    "Hamilton 当地时间 · 等待店主确认",
    "Hamilton local time · Awaiting host confirmation",
  ),
]);
</script>
<template>
  <div class="container booking-layout section-bottom">
    <aside class="booking-story">
      <h1>
        {{ tr("给自己，", "Make room") }}<br /><em>{{
          tr("留一个下午。", "for a little joy.")
        }}</em>
      </h1>
      <p>
        {{
          tr(
            "带着喜欢的图案来，或者来了再慢慢挑。先告诉我们你的计划，剩下的，一起安排。",
            "Bring a pattern you love, or find one when you arrive. Share your little plan and we will take care of the details together.",
          )
        }}
      </p>
      <img
        :src="media('studio-04')"
        width="1080"
        height="1440"
        :alt="
          tr(
            '工作室里等待客人的窗边座位',
            'A sunlit seat waiting for a visitor',
          )
        "
      />
      <ul class="inclusion-list">
        <li>
          <PhCheck />{{
            tr("独立座位与拼豆工具", "Your own seat and bead tools")
          }}
        </li>
        <li>
          <PhCheck />{{
            tr("图案与配色帮助", "Help with patterns and colours")
          }}
        </li>
        <li>
          <PhCheck />{{
            tr("烫豆与成品制作建议", "Finishing help for your creation")
          }}
        </li>
      </ul>
      <a class="text-link" :href="mapsUrl" target="_blank" rel="noreferrer"
        ><PhMapPin />8 Hughson St N, Hamilton<PhArrowUpRight
      /></a>
      <p class="fine-print">
        {{
          tr(
            "以预约确认时间到访。楼层、停车及特殊制作需求请提前联系店主。",
            "Visits are by confirmed appointment. Check arrival, parking and special requests with the host.",
          )
        }}
      </p>
    </aside>
    <div class="booking-panel">
      <InquiryForm
        kind="visit"
        :booking="booking"
        :summary="summary"
        :submit-disabled="!startTimes.length"
        ><template #details>
          <div class="form-section">
            <h2>
              {{
                tr("想怎样度过这段时间？", "How would you like to spend it?")
              }}
            </h2>
            <div class="plan-options">
              <label
                v-for="plan in plans"
                :key="plan.id"
                :class="['plan-option', { selected: booking.plan === plan.id }]"
                ><input
                  v-model="booking.plan"
                  type="radio"
                  name="plan"
                  :value="plan.id"
                /><span>{{ plan.name }}</span
                ><strong><sup>CA$</sup>{{ plan.value }}</strong
                ><small>{{ plan.unit }}</small></label
              >
            </div>
            <p class="fine-print">
              {{
                tr(
                  "参考店内公开价目表。实际费用、税费及套餐细节由店主确认。",
                  "Based on the published studio price list. The host will confirm current prices, taxes and pass details.",
                )
              }}
            </p>
          </div>
          <div class="form-section">
            <h2>
              {{
                tr("日期、时间，再到同行人数", "Your date, time and company.")
              }}
            </h2>
            <p class="form-help">
              {{
                tr(
                  "选择期望时间，并非实时空位。店主会再与你确认。",
                  "These are preferred times, not live availability. The host will confirm with you.",
                )
              }}
            </p>
            <div class="form-grid">
              <label class="field field-full"
                >{{ tr("希望到店的日期", "Preferred visit date")
                }}<input
                  v-model="booking.date"
                  type="date"
                  name="date"
                  :min="today"
                  :max="plusDays(today, 90)"
                  required /></label
              ><label class="field"
                >{{ tr("希望开始的时间", "Preferred start")
                }}<select v-model="booking.start" name="start" required>
                  <option v-for="time in startTimes" :key="time">
                    {{ time }}
                  </option>
                </select></label
              ><label class="field"
                >{{ tr("预计结束的时间", "Estimated finish")
                }}<select v-model="booking.end" name="end" required>
                  <option v-for="time in endTimes" :key="time">
                    {{ time }}
                  </option>
                </select></label
              ><label class="field field-full"
                >{{ tr("同行人数", "Number of guests")
                }}<input
                  v-model.number="booking.guests"
                  type="number"
                  name="guests"
                  min="1"
                  max="20"
                  step="1"
                  :readonly="booking.plan !== 'hourly'"
                  required
              /></label>
            </div>
            <p v-if="!startTimes.length" class="form-error" role="status">
              {{
                tr(
                  "这一天已没有可选的到访时间，请换一个日期。",
                  "There are no remaining times for this date. Please choose another day.",
                )
              }}
            </p>
            <p class="fine-print">
              {{
                tr(
                  "所有时间均为 Hamilton 当地时间。多人到访的座位安排需要店主确认。",
                  "All times are local to Hamilton. Seating for groups is subject to the host’s confirmation.",
                )
              }}
            </p>
          </div>
        </template></InquiryForm
      >
    </div>
  </div>
</template>
