<script setup lang="ts">
import { contentModule } from "../content-store";
const copyText = contentModule("pages-Cart", copyTextDefault);

import copyTextDefault from "../content/pages-Cart.json";
import { say } from "../state";

import {
  computed,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from "vue";
import { useRouter } from "vue-router";
import {
  PhArrowRight,
  PhLockSimple,
  PhMinus,
  PhPlus,
  PhShoppingBagOpen,
  PhTrash,
} from "@phosphor-icons/vue";
import { locale, media, prettyDate, tr } from "../state";
import {
  bag,
  bagCount,
  cartPayload,
  catalog,
  checkoutBusy,
  CommerceError,
  commerceApi,
  loadCatalog,
  money,
  quantityChange,
  recentOrder,
  rememberOrder,
  removeLine,
  type Order,
  type Quote,
} from "../commerce";
const router = useRouter();
const quote = ref<Quote>();
const lastQuote = ref<Quote>();
const shownQuote = computed(() => quote.value || lastQuote.value);
watch(quote, (value) => {
  if (value) lastQuote.value = value;
});
const loading = ref(false);
const error = ref("");
const contact = reactive({
  name: "",
  contact_method: "wechat",
  contact: "",
  notes: "",
  consent: false,
  website: "",
});
const rows = computed(() =>
  bag.value.map((line) => ({
    ...line,
    product: catalog.value?.products.find((p) => p.id === line.product_id),
    priced: quote.value?.lines.find(
      (q) =>
        q.product_id === line.product_id &&
        JSON.stringify(q.booking || null) ===
          JSON.stringify(line.booking || null),
    ),
  })),
);
const containsGoods = computed(() => bag.value.some((line) => !line.booking));
let sequence = 0;
let debounce: ReturnType<typeof setTimeout>;
let attempt:
  | { key: string; access: string; payload: string; snapshot: string[] }
  | undefined;
const retryPayload = ref<string>();
async function updateQuote() {
  const seq = ++sequence;
  quote.value = undefined;
  error.value = "";
  if (!bag.value.length) {
    lastQuote.value = undefined;
    loading.value = false;
    return;
  }
  loading.value = true;
  try {
    const result = await commerceApi<Quote>("/cart/quote", {
      method: "POST",
      body: JSON.stringify({ items: cartPayload() }),
    });
    if (seq === sequence) quote.value = result;
  } catch (e) {
    if (seq === sequence) error.value = (e as Error).message;
  } finally {
    if (seq === sequence) loading.value = false;
  }
}
watch(
  bag,
  () => {
    quote.value = undefined;
    sequence++;
    clearTimeout(debounce);
    debounce = setTimeout(updateQuote, 250);
  },
  { deep: true },
);
onMounted(async () => {
  try {
    const saved = sessionStorage.getItem("puppy-checkout-attempt");
    if (saved) {
      attempt = JSON.parse(saved);
      retryPayload.value = attempt?.payload;
    }
  } catch {
    /* Use a new checkout attempt. */
  }
  try {
    await loadCatalog();
    await updateQuote();
  } catch (e) {
    error.value = (e as Error).message;
  }
});
onBeforeUnmount(() => {
  clearTimeout(debounce);
  sequence++;
});
function newSecret() {
  return [...crypto.getRandomValues(new Uint8Array(32))]
    .map((n) => n.toString(16).padStart(2, "0"))
    .join("");
}
async function pay(retry = false) {
  if (checkoutBusy.value || (!retry && (!quote.value || !contact.consent)))
    return;
  checkoutBusy.value = true;
  error.value = "";
  const snapshot = bag.value.map((v) => v.key);
  try {
    let payload: string;
    if (retry && attempt) payload = attempt.payload;
    else {
      const access = newSecret();
      payload = JSON.stringify({
        items: cartPayload(),
        ...contact,
        locale: locale.value,
        quote_id: quote.value!.quote_id,
        access_key: access,
      });
      attempt = { key: crypto.randomUUID(), access, payload, snapshot };
    }
    try {
      sessionStorage.setItem("puppy-checkout-attempt", JSON.stringify(attempt));
    } catch {
      /* Retry remains available in memory. */
    }
    const order = await commerceApi<Order>("/orders", {
      method: "POST",
      body: payload,
      headers: { "Idempotency-Key": attempt!.key },
    });
    rememberOrder(order.id, attempt!.access);
    // These items have become a durable order. New additions from elsewhere remain.
    const sent = JSON.parse(attempt!.payload).items as typeof order.quote.lines;
    bag.value = bag.value.flatMap((line) => {
      if (!attempt!.snapshot.includes(line.key)) return [line];
      const purchased = sent.find(
        (item) =>
          item.product_id === line.product_id &&
          JSON.stringify(item.booking || null) ===
            JSON.stringify(line.booking || null),
      );
      if (!purchased) return [line];
      const remaining = line.quantity - purchased.quantity;
      return remaining > 0 ? [{ ...line, quantity: remaining }] : [];
    });
    retryPayload.value = undefined;
    try {
      sessionStorage.removeItem("puppy-checkout-attempt");
    } catch {
      /* No persisted attempt. */
    }
    await router.push(`/order/${order.id}`);
  } catch (e) {
    if (e instanceof CommerceError && e.status >= 400 && e.status < 500) {
      retryPayload.value = undefined;
      attempt = undefined;
      try {
        sessionStorage.removeItem("puppy-checkout-attempt");
      } catch {
        /* No pending request. */
      }
      await updateQuote();
    } else retryPayload.value = attempt?.payload;
    error.value = (e as Error).message;
  } finally {
    checkoutBusy.value = false;
  }
}
</script>
<template>
  <section class="container cart-intro">
    <span class="eyebrow">YOUR LITTLE COLLECTION</span>
    <h1>{{ say(copyText.your_bag_fe50f1) }}</h1>
    <p>
      {{ say(copyText.an_afternoon_a_few_little_things_everything_f3f96f) }}
    </p>
  </section>
  <div v-if="retryPayload && !bag.length" class="container admin-feedback">
    <p>
      {{ say(copyText.your_previous_checkout_has_not_returned_a_b40b17) }}
    </p>
    <button
      class="button button-outline"
      :disabled="checkoutBusy"
      @click="pay(true)"
    >
      {{ say(copyText.resume_checkout_b2cc6f) }}<PhArrowRight />
    </button>
  </div>
  <section v-if="!bag.length" class="container empty-bag section-bottom">
    <div class="empty-bag-photo">
      <img
        :src="media('studio-11')"
        width="1080"
        height="1440"
        :alt="say(copyText.little_handmade_bead_creations_d6f442)"
      />
    </div>
    <div>
      <PhShoppingBagOpen :size="38" weight="light" />
      <h2>{{ say(copyText.room_for_something_lovely_ded35b) }}</h2>
      <p>
        {{ say(copyText.start_with_a_studio_visit_or_a_becf32) }}
      </p>
      <div class="empty-actions">
        <RouterLink to="/visit" class="button button-primary"
          >{{ say(copyText.choose_a_visit_6a7efd) }}<PhArrowRight /></RouterLink
        ><RouterLink to="/shop" class="text-link"
          >{{ say(copyText.browse_the_shop_b03c6f) }}<PhArrowRight
        /></RouterLink>
      </div>
      <RouterLink
        v-if="recentOrder"
        :to="`/order/${recentOrder}`"
        class="text-link"
        >{{ say(copyText.view_your_recent_order_d58124) }}<PhArrowRight
      /></RouterLink>
    </div>
  </section>
  <div v-else class="container cart-layout section-bottom">
    <div class="cart-details">
      <div class="cart-list-title">
        <h2>{{ say(copyText.your_bag_5af126) }}</h2>
        <span>{{ bagCount }} {{ say(copyText.little_things_5d8e28) }}</span>
      </div>
      <TransitionGroup name="bag-list" tag="div" class="bag-line-list"
        ><article v-for="line in rows" :key="line.key" class="bag-line">
          <img
            :src="media(line.product?.image || 'studio-04')"
            width="1080"
            height="1440"
            :alt="line.product ? tr(line.product.zh, line.product.en) : ''"
          />
          <div class="bag-line-info">
            <span class="eyebrow">{{
              line.booking
                ? say(copyText.studio_visit_6ac62b)
                : say(copyText.studio_pickup_b0a250)
            }}</span>
            <h3>
              {{
                line.product
                  ? tr(line.product.zh, line.product.en)
                  : line.product_id
              }}
            </h3>
            <template v-if="line.booking"
              ><p>
                {{ prettyDate(line.booking.date) }}<br />{{
                  line.booking.start
                }}–{{ line.booking.end }} · {{ line.booking.guests }}
                {{ say(copyText.guests_24bfb5) }}
              </p>
              <RouterLink class="text-link small-link" to="/visit">{{
                say(copyText.choose_another_time_08ddad)
              }}</RouterLink></template
            >
            <div v-else class="quantity-stepper">
              <button
                :disabled="checkoutBusy || line.quantity <= 1"
                :aria-label="say(copyText.decrease_quantity_4c6078)"
                @click="quantityChange(line.key, -1)"
              >
                <PhMinus /></button
              ><span>{{ line.quantity }}</span
              ><button
                :disabled="checkoutBusy || line.quantity >= 20"
                :aria-label="say(copyText.increase_quantity_bf2b16)"
                @click="quantityChange(line.key, 1)"
              >
                <PhPlus />
              </button>
            </div>
          </div>
          <div class="bag-line-end">
            <strong>{{
              line.priced ? money(line.priced.total_cents) : "—"
            }}</strong
            ><button
              class="icon-button"
              :disabled="checkoutBusy"
              :aria-label="say(copyText.remove_from_bag_6e3287)"
              @click="removeLine(line.key)"
            >
              <PhTrash :size="18" />
            </button>
          </div></article
      ></TransitionGroup>
      <RouterLink to="/shop" class="text-link"
        >{{ say(copyText.keep_looking_around_d52bb5) }}<PhArrowRight
      /></RouterLink>
      <form id="checkout-form" class="checkout-contact" @submit.prevent="pay()">
        <fieldset :disabled="checkoutBusy">
          <legend>
            {{ say(copyText.a_name_so_we_know_who_to_5eae58) }}
          </legend>
          <div class="form-grid">
            <label class="field"
              >{{ say(copyText.your_name_691e1f)
              }}<input
                v-model="contact.name"
                name="name"
                autocomplete="name"
                maxlength="80"
                required /></label
            ><label class="field"
              >{{ say(copyText.contact_method_73d70a)
              }}<select v-model="contact.contact_method">
                <option value="wechat">
                  {{ say(copyText.wechat_2941d2) }}
                </option>
                <option value="email">{{ say(copyText.email_b6d15f) }}</option>
                <option value="phone">{{ say(copyText.phone_ac7a62) }}</option>
              </select></label
            ><label class="field field-full"
              >{{
                contact.contact_method === "wechat"
                  ? say(copyText.wechat_id_7a6e86)
                  : contact.contact_method === "email"
                    ? say(copyText.email_address_1f1559)
                    : say(copyText.phone_number_15447d)
              }}<input
                v-model="contact.contact"
                name="contact"
                :type="
                  contact.contact_method === 'email'
                    ? 'email'
                    : contact.contact_method === 'phone'
                      ? 'tel'
                      : 'text'
                "
                maxlength="180"
                minlength="3"
                required /></label
            ><label class="field field-full"
              >{{ say(copyText.anything_you_would_like_us_to_know_4e9264)
              }}<textarea v-model="contact.notes" rows="3" maxlength="1500" />
            </label>
          </div>
          <label class="honey-field" aria-hidden="true"
            >Website<input
              v-model="contact.website"
              tabindex="-1"
              autocomplete="off"
          /></label>
          <p v-if="containsGoods" class="pickup-note">
            {{ say(copyText.shop_items_are_for_studio_pickup_contact_74d4c2) }}
          </p>
          <label class="consent-label"
            ><input
              v-model="contact.consent"
              type="checkbox"
              required
            /><span>{{
              say(copyText.i_have_checked_the_time_items_and_2a0218)
            }}</span></label
          >
        </fieldset>
      </form>
    </div>
    <aside class="checkout-summary">
      <span class="eyebrow">A LOVELY LITTLE PLAN</span>
      <h2>{{ say(copyText.ready_when_you_are_408829) }}</h2>
      <p class="summary-caption">
        {{ say(copyText.priced_in_cad_paid_in_cny_53d8c7) }}
      </p>
      <div
        v-if="shownQuote"
        :class="['pricing-frame', { stale: !quote }]"
        :aria-busy="!quote"
      >
        <dl class="price-breakdown">
          <div>
            <dt>{{ say(copyText.items_experiences_f45837) }}</dt>
            <dd>{{ money(shownQuote.subtotal_cents) }}</dd>
          </div>
          <div v-if="shownQuote.tax_mode === 'additional'">
            <dt>
              {{ say(copyText.tax_d7bdd7) }} ({{ shownQuote.tax_bps / 100 }}%)
            </dt>
            <dd>{{ money(shownQuote.tax_cents) }}</dd>
          </div>
          <div>
            <dt>
              {{ say(copyText.total_fe87d0)
              }}<small v-if="shownQuote.tax_mode === 'included'">{{
                say(copyText.tax_included_991ba9)
              }}</small>
            </dt>
            <dd>{{ money(shownQuote.total_cents) }}</dd>
          </div>
        </dl>
        <div class="payable-total">
          <span>{{
            quote
              ? say(copyText.you_pay_chinese_yuan_0f3d48)
              : say(copyText.previous_quote_updating_d762aa)
          }}</span
          ><strong>{{ money(shownQuote.cny_fen, "CNY") }}</strong
          ><small>1 CAD = {{ Number(shownQuote.fx_cny_per_cad) }} CNY</small>
        </div>
      </div>
      <p class="price-check-status" role="status">
        {{
          !quote && bag.length && !error
            ? say(copyText.checking_prices_and_availability_af0663)
            : ""
        }}
      </p>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <button
        v-if="error && !retryPayload"
        class="text-link"
        @click="updateQuote"
      >
        {{ say(copyText.check_again_4ba3ee) }}</button
      ><button
        class="button button-primary full-button"
        form="checkout-form"
        type="submit"
        :disabled="!quote || loading || checkoutBusy || !!retryPayload"
      >
        {{
          checkoutBusy
            ? say(copyText.preparing_your_payment_d4dce2)
            : say(copyText.continue_to_payment_f29c00)
        }}<PhArrowRight /></button
      ><button
        v-if="retryPayload"
        class="button button-outline full-button"
        :disabled="checkoutBusy"
        @click="pay(true)"
      >
        {{ say(copyText.resume_checkout_b2cc6f) }}<PhArrowRight />
      </button>
      <p class="payment-provider">
        <PhLockSimple :size="16" />{{ say(copyText.hupijiao_checkout_017d75) }}
      </p>
      <p class="fine-print">
        {{ say(copyText.your_seats_are_held_briefly_during_payment_7f7bb0) }}
      </p>
    </aside>
  </div>
</template>
