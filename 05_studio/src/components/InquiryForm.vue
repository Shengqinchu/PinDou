<script setup lang="ts">
import copyText from "../content/components-InquiryForm.json";
import { say } from "../state";

import { reactive, ref } from "vue";
import { PhArrowRight, PhCheck, PhCopy } from "@phosphor-icons/vue";
import { api, locale, tr, wechat } from "../state";
export type BookingDraft = {
  date: string;
  start: string;
  end: string;
  guests: number;
  plan: "hourly" | "day" | "pair";
};
const props = defineProps<{
  kind: "visit" | "pickup";
  booking?: BookingDraft;
  items?: { id: string; quantity: number }[];
  summary: string[];
  disabled?: boolean;
  submitDisabled?: boolean;
}>();
const emit = defineEmits<{ complete: []; busy: [value: boolean] }>();
const form = reactive({
  name: "",
  contact_method: "wechat",
  contact: "",
  notes: "",
  consent: false,
  website: "",
});
const sending = ref(false);
const error = ref("");
const receipt = ref("");
const receiptSummary = ref<string[]>([]);
const receiptHeading = ref<HTMLElement>();
const copied = ref(false);
let requestKey = "";
let lastPayload = "";

async function submit() {
  if (sending.value || props.disabled || props.submitDisabled) return;
  error.value = "";
  if (props.booking && props.booking.end <= props.booking.start) {
    error.value = say(copyText.please_choose_an_end_time_after_your_e99e5b);
    return;
  }
  const payload = JSON.stringify({
    ...form,
    kind: props.kind,
    locale: locale.value,
    booking: props.booking ?? null,
    items: props.items ?? [],
  });
  if (payload !== lastPayload) {
    requestKey = crypto.randomUUID();
    lastPayload = payload;
  }
  sending.value = true;
  emit("busy", true);
  const snapshot = [...props.summary];
  try {
    const result = await api<{ id: string; status: string }>("/requests", {
      method: "POST",
      headers: { "Idempotency-Key": requestKey },
      body: payload,
    });
    receipt.value = result.id;
    receiptSummary.value = snapshot;
    form.name = "";
    form.contact = "";
    form.notes = "";
    form.consent = false;
    emit("complete");
    setTimeout(() => receiptHeading.value?.focus(), 0);
  } catch (e) {
    error.value =
      e instanceof Error
        ? e.message
        : say(copyText.please_try_again_in_a_moment_d66e30);
  } finally {
    sending.value = false;
    emit("busy", false);
  }
}
async function copyReceipt() {
  try {
    await navigator.clipboard.writeText(
      `${receipt.value}\n${receiptSummary.value.join("\n")}`,
    );
    copied.value = true;
  } catch {
    copied.value = false;
  }
}
</script>
<template>
  <section v-if="receipt" class="receipt" aria-live="polite">
    <div class="receipt-check"><PhCheck :size="28" /></div>
    <h2 ref="receiptHeading" tabindex="-1">
      {{ say(copyText.your_little_plan_is_with_us_04bf13) }}
    </h2>
    <p>
      {{ say(copyText.this_is_a_request_awaiting_the_hosts_5f4744) }}
    </p>
    <div class="receipt-number">
      <span>{{ receipt }}</span
      ><button
        class="icon-button"
        @click="copyReceipt"
        :aria-label="say(copyText.copy_request_reference_f802cb)"
      >
        <PhCheck v-if="copied" /><PhCopy v-else />
      </button>
    </div>
    <ul>
      <li v-for="line in receiptSummary" :key="line">{{ line }}</li>
    </ul>
    <p class="fine-print">
      {{ say(copyText.no_seats_or_stock_have_been_reserved_dd3eb5) }}
      {{ wechat }}
    </p>
    <RouterLink to="/" class="text-link"
      >{{ say(copyText.back_to_the_studio_2d6b10) }}<PhArrowRight
    /></RouterLink>
  </section>
  <form v-else @submit.prevent="submit" class="inquiry-form">
    <fieldset :disabled="sending || disabled">
      <slot name="details" />
      <div class="form-section">
        <h2>{{ say(copyText.a_little_about_you_aaea3d) }}</h2>
        <div class="form-grid">
          <label class="field"
            >{{ say(copyText.your_name_691e1f)
            }}<input
              v-model.trim="form.name"
              name="name"
              autocomplete="name"
              required
              maxlength="80"
              :placeholder="
                say(copyText.what_should_we_call_you_6d8359)
              " /></label
          ><label class="field"
            >{{ say(copyText.contact_me_by_f0e9c0)
            }}<select v-model="form.contact_method" name="contact_method">
              <option value="wechat">{{ say(copyText.wechat_2941d2) }}</option>
              <option value="email">{{ say(copyText.email_b6d15f) }}</option>
              <option value="phone">
                {{ say(copyText.phone_text_b1c5c8) }}
              </option>
            </select></label
          >
        </div>
        <label class="field"
          >{{
            form.contact_method === "wechat"
              ? say(copyText.wechat_id_7a6e86)
              : form.contact_method === "email"
                ? say(copyText.email_address_5e4a2c)
                : say(copyText.phone_number_19a4c0)
          }}<input
            v-model.trim="form.contact"
            name="contact"
            :type="
              form.contact_method === 'email'
                ? 'email'
                : form.contact_method === 'phone'
                  ? 'tel'
                  : 'text'
            "
            :autocomplete="
              form.contact_method === 'email'
                ? 'email'
                : form.contact_method === 'phone'
                  ? 'tel'
                  : 'off'
            "
            required
            minlength="3"
            maxlength="180"
            :placeholder="
              say(copyText.only_used_to_arrange_this_request_828bd2)
            " /></label
        ><label class="field"
          >{{ say(copyText.anything_else_optional_6ee301)
          }}<textarea
            v-model.trim="form.notes"
            name="notes"
            rows="3"
            maxlength="1500"
            :placeholder="
              kind === 'visit'
                ? say(copyText.your_first_visit_a_pattern_you_have_bcba21)
                : say(
                    copyText.colour_codes_preferred_styles_quantities_or_a_e133a6,
                  )
            "
          ></textarea>
        </label>
      </div>
      <div class="honeypot" aria-hidden="true">
        <label
          >Website<input
            v-model="form.website"
            tabindex="-1"
            autocomplete="off"
        /></label>
      </div>
      <div class="request-summary">
        <h3>{{ say(copyText.your_request_at_a_glance_5bba9e) }}</h3>
        <p v-for="line in summary" :key="line">{{ line }}</p>
        <p class="fine-print">
          {{ say(copyText.prices_timing_and_details_are_subject_to_8b7d42) }}
        </p>
      </div>
      <label class="consent"
        ><input v-model="form.consent" type="checkbox" required /><span>{{
          say(copyText.i_understand_this_is_a_request_and_bde9b7)
        }}</span></label
      >
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <button
        class="button button-primary submit-button"
        :disabled="sending || disabled || submitDisabled"
        type="submit"
      >
        {{
          sending
            ? say(copyText.sending_0b6530)
            : kind === "visit"
              ? say(copyText.send_visit_request_3b2fc0)
              : say(copyText.send_pickup_inquiry_9e7c67)
        }}<PhArrowRight v-if="!sending" />
      </button>
      <p class="fine-print privacy-note">
        {{ say(copyText.contact_details_are_only_used_by_the_145329) }}
      </p>
    </fieldset>
  </form>
</template>
