<script setup lang="ts">
import copyText from "../content/pages-ReservationReceipt.json";
import { say } from "../state";

import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import {
  PhCheck,
  PhClock,
  PhArrowRight,
  PhArrowClockwise,
} from "@phosphor-icons/vue";
import { commerceApi } from "../commerce";
import { prettyDate, tr, wechat, phone, phoneHref } from "../state";
import type { Reservation } from "../reservations";
const route = useRoute(),
  result = ref<Reservation>(),
  busy = ref(false),
  error = ref("");
let timer: ReturnType<typeof setInterval>,
  alive = true;
async function refresh() {
  if (busy.value) return;
  busy.value = true;
  try {
    const data = await commerceApi<Reservation>(
      "/reservations/" + encodeURIComponent(String(route.params.id)),
    );
    if (alive) {
      result.value = data;
      error.value = "";
    }
  } catch (e) {
    if (alive) error.value = (e as Error).message;
  } finally {
    if (alive) busy.value = false;
  }
}
function visible() {
  if (!document.hidden) refresh();
}
onMounted(() => {
  refresh();
  timer = setInterval(() => {
    if (result.value?.status === "pending") visible();
  }, 15000);
  window.addEventListener("pageshow", visible);
  document.addEventListener("visibilitychange", visible);
});
onBeforeUnmount(() => {
  alive = false;
  clearInterval(timer);
  window.removeEventListener("pageshow", visible);
  document.removeEventListener("visibilitychange", visible);
});
</script>
<template>
  <section class="reservation-receipt container">
    <template v-if="result"
      ><div class="reservation-seal">
        <PhCheck
          v-if="['confirmed', 'completed'].includes(result.status)"
          :size="33"
        /><PhClock v-else :size="33" />
      </div>
      <p class="vision-eyebrow">{{ result.id }}</p>
      <h1 v-if="result.status === 'pending'">
        {{ say(copyText.your_request_is_in_4ebd77) }}<br /><em>{{
          say(copyText.the_host_will_confirm_it_ae62ce)
        }}</em>
      </h1>
      <h1 v-else-if="result.status === 'confirmed'">
        {{ say(copyText.your_visit_is_confirmed_94453d) }}<br /><em>{{
          say(copyText.see_you_at_the_studio_add3a5)
        }}</em>
      </h1>
      <h1 v-else-if="result.status === 'completed'">
        {{ say(copyText.thank_you_for_coming_285672) }}<br /><em>{{
          say(copyText.lets_make_again_soon_12f0b9)
        }}</em>
      </h1>
      <h1 v-else>
        {{ say(copyText.this_reservation_was_cancelled_54b1d2) }}
      </h1>
      <p v-if="result.status === 'pending'">
        {{ say(copyText.the_host_will_review_your_plans_as_fec716) }}
      </p>
      <p v-if="result.status === 'pending'" class="reservation-urgent">
        {{ say(copyText.if_your_visit_starts_in_less_than_4b8a93) }}
      </p>
      <dl>
        <div>
          <dt>{{ say(copyText.guest_9302c0) }}</dt>
          <dd>{{ result.name }}</dd>
        </div>
        <div>
          <dt>{{ say(copyText.visit_time_9fc550) }}</dt>
          <dd>
            {{ prettyDate(result.booking.date) }}<br />{{
              result.booking.start
            }}–{{ result.booking.end }} ·
            {{ say(copyText.hamilton_local_time_496f95) }}
          </dd>
        </div>
        <div>
          <dt>{{ say(copyText.guests_c77186) }}</dt>
          <dd>{{ result.booking.guests }} {{ say(copyText.guests_24bfb5) }}</dd>
        </div>
        <div>
          <dt>{{ say(copyText.experience_cc25a0) }}</dt>
          <dd>
            {{
              result.booking.plan === "day"
                ? say(copyText.day_visit_aad886)
                : say(copyText.hourly_visit_681491)
            }}
          </dd>
        </div>
      </dl>
      <p class="reservation-details-link">
        {{ say(copyText.come_along_and_read_our_ad449d)
        }}<RouterLink to="/details">{{
          say(copyText.studio_details_fbed84)
        }}</RouterLink
        >{{ say(copyText.before_your_visit_1e5e77) }}
      </p>
    </template>
    <p v-else-if="busy" role="status">
      {{ say(copyText.loading_your_reservation_9f91f7) }}
    </p>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <button type="button" class="text-link" :disabled="busy" @click="refresh">
      <PhArrowClockwise :class="{ spinning: busy }" />{{
        say(copyText.refresh_reservation_30af18)
      }}
    </button>
    <p class="fine-print">
      {{ say(copyText.for_changes_contact_the_host_on_wechat_2921d8)
      }}{{ wechat }} · {{ say(copyText.phone_0614da)
      }}<a :href="phoneHref">{{ phone }}</a>
    </p>
  </section>
</template>
