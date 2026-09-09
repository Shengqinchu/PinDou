<script setup lang="ts">
import CopyContact from "../components/CopyContact.vue";
import { contentModule } from "../content-store";
const copyText = contentModule("pages-Order", copyTextDefault);

import copyTextDefault from "../content/pages-Order.json";
import { say } from "../state";

import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  PhArrowRight,
  PhArrowClockwise,
  PhCheck,
  PhClock,
  PhMapPin,
} from "@phosphor-icons/vue";
import { handheldCashier, inWeChat } from "../browser";
import { mapsUrl, prettyDate, tr, wechat } from "../state";
import {
  addToBag,
  bag,
  commerceApi,
  money,
  orderKey,
  statusText,
  type Order,
} from "../commerce";
const route = useRoute();
const router = useRouter();
const order = ref<Order>();
const error = ref("");
const busy = ref(false);
const now = ref(Date.now() / 1000);
const qrError = ref(false);
const mobile = ref(handheldCashier || matchMedia("(max-width: 767px)").matches);
const id = String(route.params.id);
const access = orderKey(id);
const seconds = computed(() =>
  Math.max(0, Math.ceil((order.value?.expires_at || 0) - now.value)),
);
const countdown = computed(
  () =>
    `${Math.floor(seconds.value / 60)}:${String(seconds.value % 60).padStart(2, "0")}`,
);
const payable = computed(
  () => order.value?.status === "pending" && seconds.value > 0,
);
const terminal = computed(() =>
  ["paid", "paid_needs_review", "failed", "refunded"].includes(
    order.value?.status || "",
  ),
);
const hasVisit = computed(() =>
  order.value?.quote.lines.some((line) => line.booking),
);
let timer: ReturnType<typeof setInterval>;
let polling: ReturnType<typeof setTimeout>;
let alive = true;
async function load() {
  if (busy.value || !alive) return;
  if (!access) {
    error.value = say(copyText.please_use_the_browser_in_which_you_972d7e);
    return;
  }
  busy.value = true;
  try {
    const data = await commerceApi<Order>(`/orders/${id}`, {
      headers: { "X-Order-Key": access },
    });
    if (alive) {
      order.value = data;
      error.value = "";
    }
  } catch (e) {
    if (alive) error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
async function poll() {
  await load();
  if (alive && !terminal.value) polling = setTimeout(poll, 8000);
}
function resume() {
  now.value = Date.now() / 1000;
  if (!document.hidden && !terminal.value) load();
}
onMounted(() => {
  window.addEventListener("pageshow", resume);
  document.addEventListener("visibilitychange", resume);
  poll();
  timer = setInterval(() => (now.value = Date.now() / 1000), 1000);
});
onBeforeUnmount(() => {
  alive = false;
  window.removeEventListener("pageshow", resume);
  document.removeEventListener("visibilitychange", resume);
  clearInterval(timer);
  clearTimeout(polling);
});
async function tryAgain() {
  if (!order.value || !["failed", "expired"].includes(order.value.status))
    return;
  for (const line of order.value.quote.lines) {
    addToBag(line.product_id, line.booking || undefined);
    const added = bag.value.find(
      (b) => b.product_id === line.product_id && !b.booking,
    );
    if (added) added.quantity = Math.max(added.quantity, line.quantity);
  }
  await router.push("/cart");
}
</script>
<template>
  <section class="container order-page section-bottom">
    <RouterLink to="/cart" class="text-link">{{
      say(copyText.back_to_your_bag_1d6e14)
    }}</RouterLink>
    <p v-if="error" class="form-error" role="alert">
      {{ error }}
      <button class="text-link" :disabled="busy" @click="load">
        {{ say(copyText.try_again_c3273b) }}
      </button>
    </p>
    <div v-if="order" class="order-layout">
      <div class="order-main">
        <div :class="['order-seal', { confirmed: order.status === 'paid' }]">
          <PhCheck v-if="order.status === 'paid'" :size="30" /><PhClock
            v-else
            :size="30"
          />
        </div>
        <span class="eyebrow">{{ statusText(order.status) }}</span>
        <h1 v-if="order.status === 'paid'">
          {{ say(copyText.a_little_joy_dd360a) }}<br /><em>{{
            say(copyText.all_yours_a7d095)
          }}</em>
        </h1>
        <h1 v-else-if="payable">
          {{ say(copyText.one_last_step_c893db) }}<br /><em>{{
            say(copyText.then_something_lovely_98b831)
          }}</em>
        </h1>
        <h1 v-else class="order-state-title">{{ statusText(order.status) }}</h1>
        <p v-if="order.status === 'paid'">
          {{
            tr(
              hasVisit ? copyText.literal_77352916 : copyText.literal_ee5000bb,
              hasVisit ? copyText.literal_2f14e161 : copyText.literal_975ac3ac,
            )
          }}
        </p>
        <p v-else-if="order.status === 'paid_needs_review'" class="form-error">
          {{ say(copyText.payment_was_received_but_the_original_time_b82219) }}
        </p>
        <p v-else-if="order.status === 'expired'">
          {{ say(copyText.the_payment_window_has_closed_and_the_327666) }}
        </p>
        <p
          v-else-if="
            order.status === 'payment_uncertain' ||
            (!payable && order.status === 'pending')
          "
        >
          {{ say(copyText.we_are_checking_the_payment_result_if_c5b772) }}
        </p>
        <p v-else-if="order.status === 'failed'">
          {{ say(copyText.the_cashier_could_not_be_created_you_81cadc) }}
        </p>
        <div v-if="payable" class="cashier-panel">
          <div class="cashier-heading">
            <strong>{{ say(copyText.total_in_chinese_yuan_175a2f) }}</strong
            ><span><PhClock />{{ countdown }}</span>
          </div>
          <strong class="cashier-amount">{{
            money(order.quote.cny_fen, "CNY")
          }}</strong>
          <template v-if="!mobile && order.qr_url"
            ><img
              v-if="!qrError"
              class="payment-qr"
              :src="order.qr_url"
              :alt="say(copyText.hupijiao_payment_qr_code_5f9260)"
              referrerpolicy="no-referrer"
              @error="qrError = true"
            />
            <p v-if="qrError" class="form-error">
              {{ say(copyText.the_payment_qr_could_not_load_please_383cf4) }}
            </p>
            <p>
              {{ say(copyText.scan_with_your_phone_to_pay_this_8d75b2) }}
            </p></template
          >
          <template v-else-if="order.payment_url"
            ><p v-if="inWeChat" class="form-help">
              {{
                say(copyText.checkout_opens_in_this_wechat_window_return_ad1e2a)
              }}
            </p>
            <a
              :href="order.payment_url"
              class="button button-primary full-button"
              rel="noreferrer"
              >{{ say(copyText.open_hupijiao_checkout_d57642) }}<PhArrowRight
            /></a>
            <p class="fine-print">
              {{
                say(
                  copyText.return_here_after_paying_to_view_confirmation_9e3a3b,
                )
              }}
            </p></template
          >
          <p v-else class="form-help">
            {{ say(copyText.open_this_order_on_a_desktop_to_a8ae91) }}
          </p>
        </div>
        <button
          v-if="['expired', 'failed'].includes(order.status)"
          class="button button-outline"
          @click="tryAgain"
        >
          {{ say(copyText.review_your_bag_again_293dbb) }}<PhArrowRight />
        </button>
        <button
          v-if="!terminal"
          class="text-link"
          :disabled="busy"
          @click="load"
        >
          <PhArrowClockwise />{{ say(copyText.refresh_payment_status_18e1f5) }}
        </button>
        <div class="order-contact">
          <a :href="mapsUrl" class="text-link" target="_blank" rel="noreferrer"
            ><PhMapPin />8 Hughson St N, Hamilton</a
          >
          <p>
            {{ say(copyText.contact_the_host_wechat_11a64c) }}
            <CopyContact :value="wechat" />
          </p>
        </div>
      </div>
      <aside class="receipt">
        <span class="eyebrow">YOUR LITTLE PLAN</span>
        <h2>{{ say(copyText.order_details_ef4c47) }}</h2>
        <p class="order-number">{{ order.id }}</p>
        <article
          v-for="(line, i) in order.quote.lines"
          :key="i"
          class="receipt-line"
        >
          <div>
            <h3>
              {{ tr(line.zh, line.en)
              }}<span v-if="!line.booking"> × {{ line.quantity }}</span>
            </h3>
            <p v-if="line.booking">
              {{ prettyDate(line.booking.date) }}<br />{{
                line.booking.start
              }}–{{ line.booking.end }} · {{ line.booking.guests }}
              {{ say(copyText.guests_24bfb5) }}<br />{{
                say(copyText.hamilton_local_time_b04d8a)
              }}
            </p>
            <p v-else>
              {{
                say(copyText.studio_pickup_contact_the_host_to_arrange_0cf43a)
              }}
            </p>
          </div>
          <strong>{{ money(line.total_cents) }}</strong>
        </article>
        <dl class="price-breakdown">
          <div v-if="order.quote.tax_mode === 'additional'">
            <dt>{{ say(copyText.tax_d7bdd7) }}</dt>
            <dd>{{ money(order.quote.tax_cents) }}</dd>
          </div>
          <div>
            <dt>{{ say(copyText.cad_total_0fc8b6) }}</dt>
            <dd>{{ money(order.quote.total_cents) }}</dd>
          </div>
          <div>
            <dt>{{ say(copyText.payment_in_cny_66e946) }}</dt>
            <dd>{{ money(order.quote.cny_fen, "CNY") }}</dd>
          </div>
        </dl>
        <p class="fine-print">
          1 CAD = {{ Number(order.quote.fx_cny_per_cad) }} CNY ·
          {{ say(copyText.rate_locked_for_this_order_114f47) }}
        </p>
      </aside>
    </div>
    <p v-else-if="!error" class="form-help" role="status">
      {{ say(copyText.loading_your_order_d79415) }}
    </p>
  </section>
</template>
