<script setup lang="ts">
import { contentModule } from "../../content-store";
const copyText = contentModule("components-admin-SchedulePanel", copyTextDefault);

import { formatCopy } from "../../state";

import contentLabels from "../../content/data-components-admin-SchedulePanel-labels.json";

import copyTextDefault from "../../content/components-admin-SchedulePanel.json";
import { say } from "../../state";

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
const labels = contentLabels;
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
  return new Intl.DateTimeFormat(say(copyText.enca_9cd218), {
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
          {{ say(copyText.a_place_for_every_guest_4abf35) }}
        </p>
        <h1>{{ say(copyText.studio_schedule_436d7b) }}</h1>
        <p>
          {{
            say(
              copyText.opening_hours_determine_available_times_confirmed_orders_5bec41,
            )
          }}
        </p>
      </div>
      <span class="timezone-label"
        ><PhClock />Hamilton · {{ say(copyText.local_time_28dec1) }}</span
      >
    </header>
    <section class="desk-surface calendar-surface">
      <header class="desk-section-heading">
        <h2>{{ say(copyText.seven_days_at_a_glance_70abf4) }}</h2>
        <div class="calendar-navigation">
          <button
            class="desk-icon-button"
            :aria-label="say(copyText.previous_seven_days_7128fc)"
            @click="shift(-7)"
          >
            <PhArrowLeft /></button
          ><label
            ><span class="sr-only">{{
              say(copyText.calendar_start_date_4d308a)
            }}</span
            ><input v-model="start" type="date" /></label
          ><button
            class="desk-icon-button"
            :aria-label="say(copyText.next_seven_days_8ef1e1)"
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
                : say(copyText.not_open_2cdc61)
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
                {{ say(copyText.guests_24bfb5) }}</span
              ><strong>{{ entry.name }}</strong
              ><small>{{
                entry.fulfillment === "completed"
                  ? say(copyText.visited_f3f354)
                  : entry.status === "paid"
                    ? say(copyText.confirmed_b1c92b)
                    : say(copyText.payment_hold_d762cc)
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
        <span class="legend-dot" />{{ say(copyText.confirmed_visit_be14c6) }}
        <span class="legend-dot hold" />{{
          say(copyText.held_during_payment_94e609)
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
            <h2>{{ say(copyText.weekly_opening_hours_5a17fa) }}</h2>
            <p>
              {{ say(copyText.open_a_day_then_set_its_start_28436a) }}
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
                formatCopy(copyText.message_2570f7b0, {
                  v0: labels[row.day][0],
                  v1: labels[row.day][1],
                })
              "
            />
            <div class="weekly-time">
              <input
                v-model="row.start"
                type="time"
                step="1800"
                :disabled="!row.enabled"
                :aria-label="
                  formatCopy(copyText.message_4c078feb, {
                    v0: labels[row.day][0],
                    v1: labels[row.day][1],
                  })
                "
                required
              /><span>–</span
              ><input
                v-model="row.end"
                type="time"
                step="1800"
                :disabled="!row.enabled"
                :aria-label="
                  formatCopy(copyText.message_dd378f3a, {
                    v0: labels[row.day][0],
                    v1: labels[row.day][1],
                  })
                "
                required
              />
            </div>
            <small>{{
              row.enabled
                ? say(copyText.open_72485d)
                : say(copyText.closed_f28824)
            }}</small>
          </div>
        </div>
      </section>
      <div class="schedule-side">
        <section class="desk-surface capacity-settings">
          <h2>{{ say(copyText.seating_notice_a3af02) }}</h2>
          <label class="desk-field"
            >{{ say(copyText.maximum_guests_at_a_time_9a31d9)
            }}<input
              v-model.number="settings.capacity"
              name="capacity"
              type="number"
              min="0"
              max="100"
              required
            /><small>{{
              say(copyText.leave_at_0_until_decided_no_seats_eb04a3)
            }}</small></label
          ><label class="desk-field"
            >{{ say(copyText.minimum_booking_notice_minutes_6a76ff)
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
            <h2>{{ say(copyText.date_exceptions_b30a54) }}</h2>
            <button
              type="button"
              class="desk-icon-button"
              :aria-label="say(copyText.add_a_date_exception_e95e09)"
              @click="addException"
            >
              <PhPlus />
            </button>
          </header>
          <p v-if="!settings.overrides.length" class="desk-muted">
            {{ say(copyText.add_a_day_off_or_special_opening_08b4dd) }}
          </p>
          <div
            v-for="(row, i) in settings.overrides"
            :key="i"
            class="date-exception"
          >
            <div>
              <label class="desk-field"
                ><span class="sr-only">{{
                  say(copyText.exception_date_9adaf0)
                }}</span
                ><input v-model="row.date" type="date" required /></label
              ><ToggleSwitch
                v-model="row.enabled"
                :label="say(copyText.open_on_this_date_d51331)"
              /><button
                type="button"
                class="desk-icon-button"
                :aria-label="say(copyText.remove_exception_ad1b96)"
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
                :aria-label="say(copyText.special_opening_time_ababdd)"
                required
              /><span>–</span
              ><input
                v-model="row.end"
                type="time"
                step="1800"
                :aria-label="say(copyText.special_closing_time_d82538)"
                required
              />
            </div>
            <small v-else>{{
              say(copyText.bookings_are_closed_on_this_date_baf656)
            }}</small>
          </div>
        </section>
      </div>
      <div class="desk-savebar">
        <div>
          <span :class="['save-state-dot', { dirty: settingsDirty }]" />{{
            settingsDirty
              ? say(copyText.unsaved_schedule_or_checkout_changes_dbb518)
              : say(copyText.all_changes_saved_05df19)
          }}
        </div>
        <button
          type="submit"
          class="desk-button primary"
          :disabled="saving || !settingsDirty"
        >
          <PhCheck />{{
            saving
              ? say(copyText.saving_1bd9fd)
              : say(copyText.save_settings_3a2a2e)
          }}
        </button>
        <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
      </div>
    </form>
  </section>
</template>
