<script setup lang="ts">
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
    <h1>
      {{ tr("把快乐，", "A little joy,")
      }}<em>{{ tr("装进购物车。", "all together.") }}</em>
    </h1>
    <p>
      {{
        tr(
          "一个下午，几件小物。所有期待，一起结账。",
          "An afternoon, a few little things. Everything you are looking forward to, together.",
        )
      }}
    </p>
  </section>
  <div v-if="retryPayload && !bag.length" class="container admin-feedback">
    <p>
      {{
        tr(
          "上次结账尚未返回结果，请先恢复订单。",
          "Your previous checkout has not returned a result. Please recover it first.",
        )
      }}
    </p>
    <button
      class="button button-outline"
      :disabled="checkoutBusy"
      @click="pay(true)"
    >
      {{ tr("恢复刚才的结账", "Resume checkout") }}<PhArrowRight />
    </button>
  </div>
  <section v-if="!bag.length" class="container empty-bag section-bottom">
    <div class="empty-bag-photo">
      <img
        :src="media('studio-11')"
        width="1080"
        height="1440"
        :alt="tr('可爱的拼豆作品', 'Little handmade bead creations')"
      />
    </div>
    <div>
      <PhShoppingBagOpen :size="38" weight="light" />
      <h2>{{ tr("还空着，刚刚好。", "Room for something lovely.") }}</h2>
      <p>
        {{
          tr(
            "从一次到店体验，或一件喜欢的小物开始。",
            "Start with a studio visit, or a little thing you love.",
          )
        }}
      </p>
      <div class="empty-actions">
        <RouterLink to="/visit" class="button button-primary"
          >{{ tr("选到店体验", "Choose a visit") }}<PhArrowRight /></RouterLink
        ><RouterLink to="/shop" class="text-link"
          >{{ tr("逛逛小店", "Browse the shop") }}<PhArrowRight
        /></RouterLink>
      </div>
      <RouterLink
        v-if="recentOrder"
        :to="`/order/${recentOrder}`"
        class="text-link"
        >{{ tr("查看最近的订单", "View your recent order") }}<PhArrowRight
      /></RouterLink>
    </div>
  </section>
  <div v-else class="container cart-layout section-bottom">
    <div class="cart-details">
      <div class="cart-list-title">
        <h2>{{ tr("我的购物车", "Your bag") }}</h2>
        <span>{{ bagCount }} {{ tr("项心意", "little things") }}</span>
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
                ? tr("到店体验", "STUDIO VISIT")
                : tr("到店自提", "STUDIO PICKUP")
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
                {{ tr("人", "guests") }}
              </p>
              <RouterLink class="text-link small-link" to="/visit">{{
                tr("选择其他时段", "Choose another time")
              }}</RouterLink></template
            >
            <div v-else class="quantity-stepper">
              <button
                :disabled="checkoutBusy || line.quantity <= 1"
                :aria-label="tr('减少数量', 'Decrease quantity')"
                @click="quantityChange(line.key, -1)"
              >
                <PhMinus /></button
              ><span>{{ line.quantity }}</span
              ><button
                :disabled="checkoutBusy || line.quantity >= 20"
                :aria-label="tr('增加数量', 'Increase quantity')"
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
              :aria-label="tr('从购物车移除', 'Remove from bag')"
              @click="removeLine(line.key)"
            >
              <PhTrash :size="18" />
            </button>
          </div></article
      ></TransitionGroup>
      <RouterLink to="/shop" class="text-link"
        >{{ tr("再逛一会儿", "Keep looking around") }}<PhArrowRight
      /></RouterLink>
      <form id="checkout-form" class="checkout-contact" @submit.prevent="pay()">
        <fieldset :disabled="checkoutBusy">
          <legend>
            {{
              tr(
                "留个名字，见面时好认出你。",
                "A name, so we know who to welcome.",
              )
            }}
          </legend>
          <div class="form-grid">
            <label class="field"
              >{{ tr("你的称呼", "Your name")
              }}<input
                v-model="contact.name"
                name="name"
                autocomplete="name"
                maxlength="80"
                required /></label
            ><label class="field"
              >{{ tr("联系方式", "Contact method")
              }}<select v-model="contact.contact_method">
                <option value="wechat">{{ tr("微信", "WeChat") }}</option>
                <option value="email">{{ tr("电子邮箱", "Email") }}</option>
                <option value="phone">{{ tr("电话", "Phone") }}</option>
              </select></label
            ><label class="field field-full"
              >{{
                contact.contact_method === "wechat"
                  ? tr("微信号", "WeChat ID")
                  : contact.contact_method === "email"
                    ? tr("邮箱地址", "Email address")
                    : tr("电话号码", "Phone number")
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
              >{{
                tr(
                  "想提前告诉我们的事（选填）",
                  "Anything you would like us to know? (Optional)",
                )
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
            {{
              tr(
                "小物采用到店自提；购买后联系店主安排取货。",
                "Shop items are for studio pickup. Contact the host after purchase to arrange collection.",
              )
            }}
          </p>
          <label class="consent-label"
            ><input
              v-model="contact.consent"
              type="checkbox"
              required
            /><span>{{
              tr(
                "我已核对时段、商品及实付金额，同意使用以上联系方式处理本次订单。",
                "I have checked the time, items and payment total, and agree to be contacted about this order.",
              )
            }}</span></label
          >
        </fieldset>
      </form>
    </div>
    <aside class="checkout-summary">
      <span class="eyebrow">A LOVELY LITTLE PLAN</span>
      <h2>{{ tr("准备好，就出发。", "Ready when you are.") }}</h2>
      <p class="summary-caption">
        {{ tr("加元标价 · 人民币付款", "Priced in CAD · Paid in CNY") }}
      </p>
      <template v-if="quote"
        ><dl class="price-breakdown">
          <div>
            <dt>{{ tr("商品与体验", "Items & experiences") }}</dt>
            <dd>{{ money(quote.subtotal_cents) }}</dd>
          </div>
          <div v-if="quote.tax_mode === 'additional'">
            <dt>{{ tr("税费", "Tax") }} ({{ quote.tax_bps / 100 }}%)</dt>
            <dd>{{ money(quote.tax_cents) }}</dd>
          </div>
          <div>
            <dt>
              {{ tr("合计", "Total")
              }}<small v-if="quote.tax_mode === 'included'">{{
                tr("（已含税）", " (tax included)")
              }}</small>
            </dt>
            <dd>{{ money(quote.total_cents) }}</dd>
          </div>
        </dl>
        <div class="payable-total">
          <span>{{ tr("本次实付 · 人民币", "You pay · Chinese yuan") }}</span
          ><strong>{{ money(quote.cny_fen, "CNY") }}</strong
          ><small>1 CAD = {{ Number(quote.fx_cny_per_cad) }} CNY</small>
        </div></template
      >
      <p v-else-if="loading" class="form-help" role="status">
        {{ tr("正在核对价格与空位…", "Checking prices and availability…") }}
      </p>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <button
        v-if="error && !retryPayload"
        class="text-link"
        @click="updateQuote"
      >
        {{ tr("重新核对", "Check again") }}</button
      ><button
        class="button button-primary full-button"
        form="checkout-form"
        type="submit"
        :disabled="!quote || loading || checkoutBusy || !!retryPayload"
      >
        {{
          checkoutBusy
            ? tr("正在准备收银台…", "Preparing your payment…")
            : tr("去付款", "Continue to payment")
        }}<PhArrowRight /></button
      ><button
        v-if="retryPayload"
        class="button button-outline full-button"
        :disabled="checkoutBusy"
        @click="pay(true)"
      >
        {{ tr("恢复刚才的结账", "Resume checkout") }}<PhArrowRight />
      </button>
      <p class="payment-provider">
        <PhLockSimple :size="16" />{{ tr("虎皮椒收银台", "Hupijiao checkout") }}
      </p>
      <p class="fine-print">
        {{
          tr(
            "座位在付款期间短暂保留。付款成功后，订单和到店时段立即确认。",
            "Your seats are held briefly during payment. Successful payment confirms your order and visit time.",
          )
        }}
      </p>
    </aside>
  </div>
</template>
