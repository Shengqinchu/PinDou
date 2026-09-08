<script setup lang="ts">
import copyText from "../../content/components-admin-ReservationSettings.json";
import { say } from "../../state";

import { computed, ref, watch } from "vue";
import {
  PhSlidersHorizontal,
  PhClock,
  PhUsers,
  PhCheck,
} from "@phosphor-icons/vue";
import { useDesk } from "../../admin";
import { tr } from "../../state";
import SlideOver from "../SlideOver.vue";
import ToggleSwitch from "../ToggleSwitch.vue";
type Hours = { weekday: number; enabled: boolean; open: string; close: string };
type Settings = {
  version: number;
  exclusive_groups: boolean;
  max_guests_per_group: number;
  max_concurrent_groups: number | null;
  max_concurrent_guests: number | null;
  weekly_hours: Hours[];
};
const props = defineProps<{ active: boolean }>();
const emit = defineEmits<{ saved: [] }>();
const { request } = useDesk();
const saved = ref<Settings>();
const draft = ref<Settings>();
const open = ref(false),
  busy = ref(false),
  loading = ref(false),
  error = ref(""),
  success = ref(false);
const weekdays = computed(() => [
  say(copyText.monday_c0af44),
  say(copyText.tuesday_b7e702),
  say(copyText.wednesday_ae3438),
  say(copyText.thursday_17b143),
  say(copyText.friday_5c2815),
  say(copyText.saturday_89cac3),
  say(copyText.sunday_c768eb),
]);
const times = Array.from(
  { length: 48 },
  (_, i) =>
    String(Math.floor(i / 2)).padStart(2, "0") + (i % 2 ? ":30" : ":00"),
);
async function load() {
  if (loading.value) return false;
  loading.value = true;
  error.value = "";
  try {
    saved.value = await request<Settings>("/manage/reservation-policy");
    return true;
  } catch (e) {
    error.value = (e as Error).message;
    return false;
  } finally {
    loading.value = false;
  }
}
async function edit() {
  success.value = false;
  if (!(await load())) return;
  if (!saved.value) return;
  draft.value = JSON.parse(JSON.stringify(saved.value));
  if (draft.value!.exclusive_groups) {
    draft.value!.max_concurrent_groups = 1;
    draft.value!.exclusive_groups = false;
  }
  error.value = "";
  open.value = true;
}
async function save() {
  if (!draft.value || busy.value) return;
  busy.value = true;
  error.value = "";
  const value = JSON.parse(JSON.stringify(draft.value));
  for (const key of ["max_concurrent_groups", "max_concurrent_guests"])
    value[key] = value[key] === "" ? null : Number(value[key]) || null;
  try {
    saved.value = await request<Settings>("/manage/reservation-policy", {
      method: "PUT",
      body: JSON.stringify(value),
    });
    open.value = false;
    success.value = true;
    emit("saved");
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
watch(
  () => props.active,
  (active) => {
    if (active && !open.value) load();
  },
  { immediate: true },
);
</script>
<template>
  <div class="reservation-settings-entry">
    <div>
      <PhSlidersHorizontal :size="22" /><strong>{{
        say(copyText.hours_and_capacity_74e6d9)
      }}</strong>
      <p v-if="saved">
        {{ say(copyText.up_to_bbd6b1) }} {{ saved.max_guests_per_group }}
        {{ say(copyText.guests_per_group_522fa9) }} ·
        {{
          saved.max_concurrent_groups || saved.exclusive_groups
            ? say(copyText.group_capacity_set_83fa08)
            : say(copyText.no_total_group_limit_d1d059)
        }}
        ·
        {{
          saved.max_concurrent_guests
            ? say(copyText.guest_capacity_set_dba600)
            : say(copyText.no_total_guest_limit_d480a4)
        }}
      </p>
    </div>
    <button
      type="button"
      class="desk-button secondary"
      :disabled="loading"
      @click="edit"
    >
      <PhSlidersHorizontal />{{ say(copyText.edit_reservation_rules_ea43c9) }}
    </button>
    <span v-if="success" class="reservation-settings-saved" role="status"
      ><PhCheck />{{
        say(copyText.saved_the_customer_timetable_is_updated_3d6687)
      }}</span
    >
    <p v-if="error && !open" class="desk-error" role="alert">{{ error }}</p>
  </div>
  <SlideOver
    v-model="open"
    :title="say(copyText.hours_and_capacity_74e6d9)"
    :busy="busy"
  >
    <form v-if="draft" class="reservation-settings-form" @submit.prevent="save">
      <section>
        <h3><PhUsers />{{ say(copyText.capacity_d705b2) }}</h3>
        <label class="desk-field"
          >{{ say(copyText.maximum_guests_per_group_8220ef)
          }}<input
            v-model.number="draft.max_guests_per_group"
            name="max_guests_per_group"
            type="number"
            min="1"
            max="99"
            required
            :disabled="busy"
        /></label>
        <label class="desk-field"
          >{{ say(copyText.maximum_simultaneous_groups_c08860)
          }}<input
            v-model.number="draft.max_concurrent_groups"
            name="max_concurrent_groups"
            type="number"
            min="1"
            max="999"
            :placeholder="say(copyText.leave_blank_for_no_limit_e87065)"
            :disabled="busy"
        /></label>
        <label class="desk-field"
          >{{ say(copyText.maximum_simultaneous_guests_1b4f9f)
          }}<input
            v-model.number="draft.max_concurrent_guests"
            name="max_concurrent_guests"
            type="number"
            min="1"
            max="999"
            :placeholder="say(copyText.leave_blank_for_no_limit_e87065)"
            :disabled="busy"
        /></label>
        <p>
          {{
            say(
              copyText.confirmed_reservations_count_toward_capacity_pending_requests_a5fb9b,
            )
          }}
        </p>
      </section>
      <section>
        <h3><PhClock />{{ say(copyText.weekly_opening_hours_d55313) }}</h3>
        <p>{{ say(copyText.hamilton_local_time_turn_off_a_day_b50f66) }}</p>
        <div
          v-for="day in draft.weekly_hours"
          :key="day.weekday"
          class="reservation-hours-row"
        >
          <ToggleSwitch
            v-model="day.enabled"
            :label="weekdays[day.weekday]"
            :disabled="busy"
          />
          <strong>{{ weekdays[day.weekday] }}</strong>
          <div class="reservation-hours-inputs">
            <label
              ><span>{{ say(copyText.open_281aec) }}</span
              ><select
                v-model="day.open"
                :aria-label="
                  weekdays[day.weekday] + say(copyText.opening_time_c36b8f)
                "
                :disabled="busy || !day.enabled"
              >
                <option v-for="time in times" :key="time" :value="time">
                  {{ time }}
                </option>
              </select></label
            >
            <label
              ><span>{{ say(copyText.close_15f8ae) }}</span
              ><select
                v-model="day.close"
                :aria-label="
                  weekdays[day.weekday] + say(copyText.closing_time_57b7cd)
                "
                :disabled="busy || !day.enabled"
              >
                <option v-for="time in times" :key="time" :value="time">
                  {{ time }}
                </option>
              </select></label
            >
          </div>
        </div>
      </section>
      <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
      <button v-if="error" class="desk-button secondary" type="button" :disabled="busy || loading" @click="edit">{{ say(copyText.reload_saved_rules) }}</button>
      <p>
        {{
          say(copyText.saving_does_not_change_confirmed_reservations_if_824304)
        }}
      </p>
      <button class="desk-button" :disabled="busy">
        {{
          busy
            ? say(copyText.saving_f3d3eb)
            : say(copyText.save_reservation_rules_70acc7)
        }}
      </button>
    </form>
  </SlideOver>
</template>
