<script setup lang="ts">
import CopyContact from "../components/CopyContact.vue";
import LiftTitle from '../components/LiftTitle.vue';
import MoneyText from '../components/MoneyText.vue';
import { contentModule } from "../content-store";
const copyText = contentModule("pages-Visit", copyTextDefault);

import rateDefaults from "../content/experience-rates.json";
import { contentValues } from "../content-store";
const rates = contentValues("rate-fields",rateDefaults);
import copyTextDefault from "../content/pages-Visit.json";
import { say, formatCopy } from "../state";

import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  PhArrowRight,
  PhArrowClockwise,
  PhClock,
  PhSun,
} from "@phosphor-icons/vue";
import { commerceApi, CommerceError } from "../commerce";
import { locale, prettyDate, tr, wechat, phone, phoneHref } from "../state";
import {
  reservationDraft as draft,
  readSession,
  saveSession,
  validSelection,
  type ReservationCalendar as Calendar,
  type ReservationPayload,
  type Reservation,
} from "../reservations";
import ReservationCalendar from "../components/ReservationCalendar.vue";
import AutoHeight from "../components/AutoHeight.vue";
import { accountCopy,accountUser,ensureCustomer,closeAccount } from "../account";
const checkingAccount=ref(false);
const router = useRouter(),
  calendar = ref<Calendar | null>(null),
  loading = ref(false),
  sending = ref(false),
  error = ref("");
const attempt = ref(
  readSession<{ key: string; body: ReservationPayload }>(
    "puppy-reservation-attempt-v1",
  ),
);
const locked = computed(() => sending.value || !!attempt.value);
const selected = computed(() => validSelection(calendar.value, draft.booking));
const selectedDay = computed(() => draft.booking.plan === 'day' && selected.value
  ? calendar.value?.days.find(d => d.date === draft.booking.date) : undefined);
const dayClosing = computed(() => selectedDay.value?.close ||
  calendar.value?.weekly_hours.filter(d=>d.enabled).map(d=>d.close).sort().at(-1) || '22:00');
watch(
  () => draft.booking.guests,
  () => {
    if (!locked.value) load();
  },
);
let sequence = 0,
  timer: ReturnType<typeof setInterval>,
  alive = true;
async function load() {
  const seq = ++sequence;
  loading.value = true;
  try {
    const value = await commerceApi<Calendar>(
      "/reservation-calendar?guests=" +
        (Number.isInteger(draft.booking.guests) && draft.booking.guests > 0
          ? draft.booking.guests
          : 1),
    );
    if (!alive || seq !== sequence) return;
    calendar.value = value;
    if (
      !attempt.value &&
      draft.booking.start &&
      !validSelection(value, draft.booking)
    ) {
      draft.booking.start = "";
      draft.booking.end = "";
      error.value = say(
        copyText.your_previous_time_is_no_longer_available_9b5681,
      );
    }
  } catch (e) {
    if (alive && seq === sequence) error.value = (e as Error).message;
  } finally {
    if (alive && seq === sequence) loading.value = false;
  }
}
function refreshVisible() {
  if (!document.hidden && !sending.value) load();
}
onMounted(() => {
  load();
  timer = setInterval(refreshVisible, 60000);
  window.addEventListener("pageshow", refreshVisible);
  document.addEventListener("visibilitychange", refreshVisible);
});
onBeforeUnmount(() => {
  closeAccount();
  alive = false;
  sequence++;
  clearInterval(timer);
  window.removeEventListener("pageshow", refreshVisible);
  document.removeEventListener("visibilitychange", refreshVisible);
});
watch(
  () => draft.booking.plan,
  () => {
    if (!locked.value) {
      draft.booking.start = "";
      draft.booking.end = "";
    }
  },
);
function select(value: { date: string; start: string; end: string }) {
  Object.assign(draft.booking, value);
  error.value = "";
}
async function submit() {
  if (sending.value||checkingAccount.value) return;
  if (!attempt.value && (!selected.value || !draft.consent)) return;
  checkingAccount.value=true;
  try{if(!await ensureCustomer()||!alive)return;}
  catch(e){error.value=(e as Error).message;return;}
  finally{checkingAccount.value=false;}
  if (!attempt.value) {
    attempt.value = {
      key: crypto.randomUUID(),
      body: {
        booking: { ...draft.booking },
        name: draft.name,
        contact_method: draft.contact_method,
        contact: draft.contact,
        notes: draft.notes,
        consent: draft.consent,
        locale: locale.value,
        website: "",
      },
    };
    saveSession("puppy-reservation-attempt-v1", attempt.value);
  }
  sending.value = true;
  error.value = "";
  try {
    const receipt = await commerceApi<Reservation>("/reservations", {
      method: "POST",
      headers: { "Idempotency-Key": attempt.value.key },
      body: JSON.stringify(attempt.value.body),
    });
    saveSession("puppy-reservation-attempt-v1", null);
    attempt.value = null;
    saveSession("puppy-last-reservation", receipt.id);
    draft.booking.start = "";
    draft.booking.end = "";
    draft.consent = false;
    await router.push("/reservation/" + receipt.id);
  } catch (e) {
    error.value = (e as Error).message;
    if (e instanceof CommerceError && e.code === "reservation_session_missing")
      await load();
    if (
      e instanceof CommerceError &&
      e.status >= 400 &&
      e.status < 500 &&
      !["reservation_session_missing", "reservation_request_changed", "account_login_required"].includes(
        e.code || "",
      )
    ) {
      attempt.value = null;
      saveSession("puppy-reservation-attempt-v1", null);
      if (e.status === 409) await load();
    }
  } finally {
    sending.value = false;
  }
}
</script>
<template>
  <section class="reservation-page container">
    <header class="reservation-heading">
      <LiftTitle :text="say(copyText.come_make_something_f834ec)"/>
      <p>
        {{ say(copyText.choose_your_time_and_group_size_once_a1fdf7) }}
      </p>
    </header>
    <form @submit.prevent="submit" class="reservation-form">
      <fieldset class="reservation-plans" :disabled="locked">
        <legend>{{ say(copyText.choose_your_experience_3c37df) }}</legend>
        <label :class="{ selected: draft.booking.plan === 'hourly' }"
          ><input
            v-model="draft.booking.plan"
            type="radio"
            value="hourly"
          /><PhClock :size="28" weight="light" /><strong>{{
            say(copyText.by_the_hour_5300b2)
          }}</strong
          ><span>{{ say(copyText.at_least_two_hours_9f144b) }}</span
          ><AutoHeight class="plan-price-reveal"
            ><div
              v-if="draft.booking.plan === 'hourly'"
              class="reservation-plan-price"
            >
              <strong><MoneyText :text="'CAD '+rates.hourly"/></strong
              ><span>{{ say(copyText.hour_person_7ea78f) }}</span>
            </div></AutoHeight
          ></label
        ><label :class="{ selected: draft.booking.plan === 'day' }"
          ><input v-model="draft.booking.plan" type="radio" value="day" /><PhSun
            :size="28"
            weight="light"
          /><strong>{{ say(copyText.a_day_of_making_01d6e2) }}</strong
          ><span
            >{{ formatCopy(copyText.make_from_your_chosen_arrival_until_37196a,{v0:dayClosing}) }}<small v-if="selectedDay" class="selected-day-context">{{ formatCopy(copyText.selected_day_hours,{v0:selectedDay.date,v1:selectedDay.close}) }}</small></span
          ><AutoHeight class="plan-price-reveal"
            ><dl
              v-if="draft.booking.plan === 'day'"
              class="reservation-day-prices"
            >
              <div>
                <dt>{{ say(copyText.one_guest_684bef) }}</dt>
                <dd><MoneyText :text="'CAD '+rates.day_one"/></dd>
              </div>
              <div>
                <dt>{{ say(copyText.two_guests_65a259) }}</dt>
                <dd><MoneyText :text="'CAD '+rates.day_two"/></dd>
              </div>
              <div>
                <dt>{{ say(copyText.three_guests_032d3f) }}</dt>
                <dd><MoneyText :text="'CAD '+rates.day_three"/></dd>
              </div>
            </dl></AutoHeight
          ></label
        >
        <div class="reservation-offers">
          <aside class="reservation-credit">
            <span class="vision-eyebrow">{{
              say(copyText.prepaid_hours_ask_in_the_studio_f180a7)
            }}</span
            ><strong><MoneyText :text="say(copyText.ca7_hour_c87a20)"/></strong>
            <p>
              {{ say(copyText.prepay_at_least_10_hours_and_at_8815bf) }}
            </p>
            <small>{{
              say(copyText.for_information_only_this_is_not_a_09a580)
            }}</small>
          </aside>
          <aside class="reservation-credit reservation-school">
            <span class="vision-eyebrow">{{
              say(copyText.backtoschool_until_october_1_42119e)
            }}</span
            ><strong><MoneyText :text="'CAD '+rates.school_two_four_hours"/></strong>
            <p>{{ say(copyText.four_hours_of_making_for_two_8bb2b0) }}</p>
            <strong
              ><MoneyText :text="'CAD '+rates.school_card_holder"/>
              <small>{{ say(copyText.piece_ef469b) }}</small></strong
            >
            <p>
              {{
                say(copyText.bead_cardholder_package_no_makingtime_limit_92105b)
              }}
            </p>
            <small>{{
              say(copyText.for_information_only_this_is_not_a_09a580)
            }}</small>
          </aside>
        </div>
      </fieldset>
      <section class="reservation-time">
        <div class="reservation-section-title">
          <div>
            <span>01</span>
            <h2>
              {{ say(copyText.pick_a_time_that_feels_right_4b2e92) }}
            </h2>
          </div>
          <button
            type="button"
            class="icon-button"
            :disabled="loading || locked"
            :aria-label="say(copyText.refresh_timetable_491b53)"
            @click="load"
          >
            <PhArrowClockwise :class="{ spinning: loading }" />
          </button>
        </div>
        <p
          v-if="loading && !calendar"
          class="reservation-loading"
          role="status"
        >
          {{ say(copyText.loading_the_next_two_weeks_842416) }}
        </p>
        <ReservationCalendar
          v-if="calendar"
          :calendar="calendar"
          :booking="draft.booking"
          :disabled="loading || locked || !draft.booking.plan"
          @select="select"
        />
        <p v-if="!calendar && !loading" class="form-error" role="alert">
          {{ error }}
          <button type="button" class="text-link" @click="load">
            {{ say(copyText.try_again_014aa4) }}
          </button>
        </p>
        <div class="reservation-selection" aria-live="polite">
          <span>{{ say(copyText.your_time_278568) }}</span
          ><strong v-if="selected"
            >{{ prettyDate(draft.booking.date) }} · {{ draft.booking.start }}–{{
              draft.booking.end
            }}</strong
          ><strong v-else>{{
            say(copyText.choose_a_time_in_the_timetable_d988a8)
          }}</strong>
        </div>
      </section>
      <section class="reservation-guest">
        <div class="reservation-section-title">
          <div>
            <span>02</span>
            <h2>{{ say(copyText.who_is_coming_along_aa3fd9) }}</h2>
          </div>
        </div>
        <label class="field reservation-guests"
          >{{ say(copyText.number_of_guests_including_you_fadbc4)
          }}<input
            v-model.number="draft.booking.guests"
            type="number"
            min="1"
            :max="calendar?.max_guests_per_group || 4"
            required
            :disabled="locked"
        /></label>

        <div class="reservation-contact-fields">
          <label class="field"
            >{{ say(copyText.guest_name_e468f6)
            }}<input
              v-model.trim="draft.name"
              autocomplete="name"
              maxlength="80"
              required
              :disabled="locked"
            /><small>{{
              say(copyText.if_you_have_added_the_host_on_e3e883)
            }}</small></label
          ><label class="field"
            >{{ say(copyText.contact_method_73d70a)
            }}<select v-model="draft.contact_method" :disabled="locked">
              <option value="wechat">{{ say(copyText.wechat_2941d2) }}</option>
              <option value="phone">{{ say(copyText.phone_ac7a62) }}</option>
              <option value="email">{{ say(copyText.email_b6d15f) }}</option>
              <option value="other">
                {{ say(copyText.another_way_f489b4) }}
              </option>
            </select></label
          ><label class="field"
            >{{
              draft.contact_method === "wechat"
                ? say(copyText.wechat_id_7a6e86)
                : draft.contact_method === "phone"
                  ? say(copyText.phone_number_15447d)
                  : draft.contact_method === "email"
                    ? say(copyText.email_address_a61e0e)
                    : say(copyText.contact_details_3b7403)
            }}<input
              v-model.trim="draft.contact"
              :type="
                draft.contact_method === 'email'
                  ? 'email'
                  : draft.contact_method === 'phone'
                    ? 'tel'
                    : 'text'
              "
              minlength="3"
              maxlength="180"
              required
              :disabled="locked" /></label
          ><label class="field"
            >{{ say(copyText.anything_you_would_like_us_to_know_eef3ab)
            }}<textarea
              v-model="draft.notes"
              rows="3"
              maxlength="1500"
              :disabled="locked"
            />
          </label>
        </div>
        <label class="reservation-consent"
          ><input
            v-model="draft.consent"
            type="checkbox"
            required
            :disabled="locked"
          /><span>{{
            say(copyText.i_agree_to_use_these_details_to_5469c9)
          }}</span></label
        >
      </section>
      <div class="reservation-submit">
        <p v-if="!accountUser" class="reservation-account-note">{{ say(accountCopy.login_notice) }}</p>
        <p v-if="error && calendar" class="form-error" role="alert">
          {{ error }}
        </p>
        <p v-if="attempt && !sending" role="status">
          {{ say(copyText.your_submission_is_saved_recover_its_result_8504a5) }}
        </p>
        <button
          class="button button-primary"
          :disabled="
            sending || checkingAccount || loading || (!attempt && (!selected || !draft.consent))
          "
        >
          {{
            checkingAccount
              ? say(accountCopy.checking)
              : sending
              ? say(copyText.sending_c40370)
              : attempt
                ? say(copyText.recover_reservation_12c189)
                : say(copyText.request_this_visit_611e11)
          }}<PhArrowRight />
        </button>
        <p>
          {{ say(copyText.your_request_will_wait_for_the_hosts_cd36bf) }}
        </p>
        <span v-if="attempt" class="fine-print"
          >{{ say(copyText.host_wechat_ac7b7e) }}<CopyContact :value="wechat" /> ·
          <a :href="phoneHref">{{ phone }}</a></span
        >
      </div>
    </form>
  </section>
</template>
