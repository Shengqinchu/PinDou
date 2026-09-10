<script setup lang="ts">
import LiftTitle from '../components/LiftTitle.vue';
import CopyContact from "../components/CopyContact.vue";
import OfferLabel from '../visit/OfferLabel.vue';
import { contentModule } from "../content-store";
const copyText = contentModule("pages-ReservationReceipt", copyTextDefault);

import copyTextDefault from "../content/pages-ReservationReceipt.json";
import { say,formatCopy } from "../state";
import { walletCopy,duration } from '../wallet';

import { onBeforeUnmount, onMounted, ref,watch } from "vue";
import { useRoute } from "vue-router";
import {
  PhCheck,
  PhClock,
  PhArrowRight,
  PhArrowClockwise,
} from "@phosphor-icons/vue";
import { commerceApi,CommerceError } from "../commerce";
import { accountCopy,ensureCustomer,accountUser } from "../account";
const needsSignIn=ref(false);
import { prettyDate, tr, wechat, phone, phoneHref } from "../state";
import type { Reservation } from "../reservations";
const route = useRoute(),
  result = ref<Reservation>(),
  busy = ref(false),
  error = ref("");
let timer: ReturnType<typeof setInterval>,
  alive = true;
let sequence=0;
async function refresh() {
  if (busy.value) return;
  busy.value = true;
  const seq=++sequence;
  needsSignIn.value=false;
  try {
    const data = await commerceApi<Reservation>(
      "/reservations/" + encodeURIComponent(String(route.params.id)),
    );
    if (alive&&seq===sequence) {
      result.value = data;
      error.value = "";
    }
  } catch (e) {
    if (alive&&seq===sequence) {error.value = (e as Error).message;needsSignIn.value=e instanceof CommerceError&&e.status===401;if(e instanceof CommerceError&&[401,403,404].includes(e.status))result.value=undefined;}
  } finally {
    if (alive&&seq===sequence) busy.value = false;
  }
}
function visible() {
  if (!document.hidden) refresh();
}
async function loginAndRefresh(){try{if(await ensureCustomer()&&alive)await refresh();}catch(e){error.value=(e as Error).message;}}
watch(()=>[route.params.id,accountUser.value?.id],()=>{sequence++;result.value=undefined;busy.value=false;void refresh();});
onMounted(() => {
  refresh();
  timer = setInterval(() => {
    visible();
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
      <LiftTitle v-else as="h1" :text="say(copyText.this_reservation_was_cancelled_54b1d2)"/>
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
            <OfferLabel v-if="result.offer" :offer="result.offer"/><template v-else>{{
              result.booking.plan === "day"
                ? say(copyText.day_visit_aad886)
                : say(copyText.hourly_visit_681491)
            }}</template>
          </dd>
        </div>
        <div><dt>{{say(walletCopy.booked)}}</dt><dd>{{duration(result.booked_minutes)}}</dd></div>
        <div><dt>{{say(walletCopy.actual)}}</dt><dd>{{result.actual_minutes==null?say(walletCopy.unrecorded):formatCopy(walletCopy.per_guest,{v0:duration(result.actual_minutes),v1:result.actual_guests||result.booking.guests})}}</dd></div>
        <div v-if="result.public_note"><dt>{{say(walletCopy.public_note)}}</dt><dd>{{result.public_note}}</dd></div>
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
    <button v-if="needsSignIn" class="button button-primary" @click="loginAndRefresh">{{ say(accountCopy.sign_in) }}</button>
    <button type="button" class="text-link" :disabled="busy" @click="refresh">
      <PhArrowClockwise :class="{ spinning: busy }" />{{
        say(copyText.refresh_reservation_30af18)
      }}
    </button>
    <p class="fine-print">
      {{ say(copyText.for_changes_contact_the_host_on_wechat_2921d8)
      }}<CopyContact :value="wechat" /> · {{ say(copyText.phone_0614da)
      }}<a :href="phoneHref">{{ phone }}</a>
    </p>
  </section>
</template>
