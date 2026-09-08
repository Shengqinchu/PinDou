<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  PhArrowLeft,
  PhArrowRight,
  PhCalendarDots,
  PhCheck,
  PhPlus,
  PhTrash,
  PhClock,
} from "@phosphor-icons/vue";
import { useDesk } from "../../admin";
import { hamiltonDate, plusDays, prettyDate, tr } from "../../state";
import ToggleSwitch from "../ToggleSwitch.vue";
const {
  settings,
  settingsDirty,
  calendar,
  calendarBusy,
  saving,
  error,
  loadCalendar,
  saveSettings,
  openOrder,
} = useDesk();
const start = ref(hamiltonDate());
const route = useRoute();
watch(
  () => [route.query.scope, route.query.day],
  () => {
    const day = String(route.query.day || "");
    if (
      route.query.scope === "today-visits" &&
      /^\d{4}-\d{2}-\d{2}$/.test(day)
    ) {
      if (start.value === day) loadCalendar(day);
      else start.value = day;
    }
  },
  { immediate: true },
);
const labels = [
  ["周一", "Monday"],
  ["周二", "Tuesday"],
  ["周三", "Wednesday"],
  ["周四", "Thursday"],
  ["周五", "Friday"],
  ["周六", "Saturday"],
  ["周日", "Sunday"],
];
watch(start, (day) => {
  if (day) loadCalendar(day);
});
onMounted(() => {
  if (!calendar.value.length) loadCalendar(start.value);
});
function shift(days: number) {
  start.value = plusDays(start.value || hamiltonDate(), days);
}
function weekday(value: string) {
  return new Intl.DateTimeFormat(tr("zh-CN", "en-CA"), {
    weekday: "short",
    timeZone: "UTC",
  }).format(new Date(value + "T12:00:00Z"));
}
function addException() {
  settings.value?.overrides.push({
    date: hamiltonDate(),
    enabled: false,
    start: "10:00",
    end: "22:00",
  });
}
</script>
<template>
  <section class="desk-schedule">
    <header class="desk-page-heading">
      <div>
        <p class="desk-eyebrow">
          {{ tr("给每一位客人，留好位置", "A PLACE FOR EVERY GUEST") }}
        </p>
        <h1>{{ tr("到店排班", "Studio schedule") }}</h1>
        <p>
          {{
            tr(
              "营业时间决定可选时段，已确认的订单会自动出现在日历里。",
              "Opening hours determine available times. Confirmed orders appear in your calendar automatically.",
            )
          }}
        </p>
      </div>
      <span class="timezone-label"
        ><PhClock />Hamilton · {{ tr("当地时间", "Local time") }}</span
      >
    </header>
    <section class="desk-surface calendar-surface">
      <header class="desk-section-heading">
        <h2>{{ tr("未来七天", "Seven days at a glance") }}</h2>
        <div class="calendar-navigation">
          <button
            class="desk-icon-button"
            :aria-label="tr('前七天', 'Previous seven days')"
            @click="shift(-7)"
          >
            <PhArrowLeft /></button
          ><label
            ><span class="sr-only">{{
              tr("日历开始日期", "Calendar start date")
            }}</span
            ><input v-model="start" type="date" /></label
          ><button
            class="desk-icon-button"
            :aria-label="tr('后七天', 'Next seven days')"
            @click="shift(7)"
          >
            <PhArrowRight />
          </button>
        </div>
      </header>
      <div class="week-calendar" :aria-busy="calendarBusy">
        <div
          v-for="day in calendar"
          :key="day.date"
          :class="['calendar-day', { today: day.date === hamiltonDate() }]"
        >
          <header>
            <small>{{ weekday(day.date) }}</small
            ><strong>{{ Number(day.date.slice(-2)) }}</strong
            ><span>{{
              day.hours
                ? `${day.hours.start}–${day.hours.end}`
                : tr("未开放", "Not open")
            }}</span>
          </header>
          <div class="day-appointments">
            <button
              v-for="(entry, i) in day.entries"
              :key="entry.order_id + i"
              :class="['day-appointment', { hold: entry.status !== 'paid' }]"
              @click="openOrder(entry.order_id)"
            >
              <span
                >{{ entry.start }} · {{ entry.guests }}
                {{ tr("人", "guests") }}</span
              ><strong>{{ entry.name }}</strong
              ><small>{{
                entry.fulfillment === "completed"
                  ? tr("已到店", "Visited")
                  : entry.status === "paid"
                    ? tr("已确认", "Confirmed")
                    : tr("付款中暂留", "Payment hold")
              }}</small></button
            ><span
              v-if="!day.entries.length"
              class="day-empty"
              aria-hidden="true"
              >—</span
            >
          </div>
        </div>
      </div>
      <p class="calendar-footnote">
        <span class="legend-dot" />{{ tr("已确认到店", "Confirmed visit") }}
        <span class="legend-dot hold" />{{
          tr("付款中暂留", "Held during payment")
        }}
      </p>
    </section>
    <form
      v-if="settings"
      class="schedule-edit-grid"
      @submit.prevent="saveSettings"
    >
      <section class="desk-surface weekly-settings">
        <header class="desk-section-heading">
          <div>
            <h2>{{ tr("每周营业安排", "Weekly opening hours") }}</h2>
            <p>
              {{
                tr(
                  "开启营业日，再设定开始与结束时间。",
                  "Open a day, then set its start and finish time.",
                )
              }}
            </p>
          </div>
          <PhCalendarDots :size="22" />
        </header>
        <div class="weekly-settings-list">
          <div
            v-for="row in settings.weekly"
            :key="row.day"
            :class="['weekly-setting', { enabled: row.enabled }]"
          >
            <span>{{
              tr(labels[row.day][0], labels[row.day][1].slice(0, 3))
            }}</span
            ><ToggleSwitch
              v-model="row.enabled"
              :label="
                tr(`${labels[row.day][0]}营业`, `Open on ${labels[row.day][1]}`)
              "
            />
            <div class="weekly-time">
              <input
                v-model="row.start"
                type="time"
                step="1800"
                :disabled="!row.enabled"
                :aria-label="
                  tr(
                    `${labels[row.day][0]}开门时间`,
                    `${labels[row.day][1]} opening time`,
                  )
                "
                required
              /><span>–</span
              ><input
                v-model="row.end"
                type="time"
                step="1800"
                :disabled="!row.enabled"
                :aria-label="
                  tr(
                    `${labels[row.day][0]}打烊时间`,
                    `${labels[row.day][1]} closing time`,
                  )
                "
                required
              />
            </div>
            <small>{{
              row.enabled ? tr("营业", "Open") : tr("不开放", "Closed")
            }}</small>
          </div>
        </div>
      </section>
      <div class="schedule-side">
        <section class="desk-surface capacity-settings">
          <h2>{{ tr("接待安排", "Seating & notice") }}</h2>
          <label class="desk-field"
            >{{ tr("最多同时接待人数", "Maximum guests at a time")
            }}<input
              v-model.number="settings.capacity"
              name="capacity"
              type="number"
              min="0"
              max="100"
              required
            /><small>{{
              tr(
                "还没确定时保持 0，不会开放可购买座位。",
                "Leave at 0 until decided. No seats will be available to buy.",
              )
            }}</small></label
          ><label class="desk-field"
            >{{ tr("至少提前多少分钟预订", "Minimum booking notice (minutes)")
            }}<input
              v-model.number="settings.notice_minutes"
              type="number"
              min="0"
              max="1440"
              required
          /></label>
        </section>
        <section class="desk-surface exception-settings">
          <header class="desk-section-heading">
            <h2>{{ tr("特别日期", "Date exceptions") }}</h2>
            <button
              type="button"
              class="desk-icon-button"
              :aria-label="tr('添加特别日期', 'Add a date exception')"
              @click="addException"
            >
              <PhPlus />
            </button>
          </header>
          <p v-if="!settings.overrides.length" class="desk-muted">
            {{
              tr(
                "临时休息、节假日营业，都可以单独安排。",
                "Add a day off or special opening hours for a holiday.",
              )
            }}
          </p>
          <div
            v-for="(row, i) in settings.overrides"
            :key="i"
            class="date-exception"
          >
            <div>
              <label class="desk-field"
                ><span class="sr-only">{{
                  tr("特别日期", "Exception date")
                }}</span
                ><input v-model="row.date" type="date" required /></label
              ><ToggleSwitch
                v-model="row.enabled"
                :label="tr('该日期营业', 'Open on this date')"
              /><button
                type="button"
                class="desk-icon-button"
                :aria-label="tr('移除特别日期', 'Remove exception')"
                @click="settings.overrides.splice(i, 1)"
              >
                <PhTrash />
              </button>
            </div>
            <div v-if="row.enabled" class="weekly-time">
              <input
                v-model="row.start"
                type="time"
                step="1800"
                :aria-label="tr('特别日期开门时间', 'Special opening time')"
                required
              /><span>–</span
              ><input
                v-model="row.end"
                type="time"
                step="1800"
                :aria-label="tr('特别日期打烊时间', 'Special closing time')"
                required
              />
            </div>
            <small v-else>{{
              tr("这一天不开放预订", "Bookings are closed on this date")
            }}</small>
          </div>
        </section>
      </div>
      <div class="desk-savebar">
        <div>
          <span :class="['save-state-dot', { dirty: settingsDirty }]" />{{
            settingsDirty
              ? tr(
                  "排班／收款设置有未保存的修改",
                  "Unsaved schedule or checkout changes",
                )
              : tr("所有修改已保存", "All changes saved")
          }}
        </div>
        <button
          type="submit"
          class="desk-button primary"
          :disabled="saving || !settingsDirty"
        >
          <PhCheck />{{
            saving ? tr("保存中…", "Saving…") : tr("保存设置", "Save settings")
          }}
        </button>
        <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
      </div>
    </form>
  </section>
</template>
