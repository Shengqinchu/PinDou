<script setup lang="ts">
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
    error.value = tr(
      "请在下单时使用的浏览器中查看这个订单。",
      "Please use the browser in which you placed this order.",
    );
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
      tr("返回购物车", "Back to your bag")
    }}</RouterLink>
    <p v-if="error" class="form-error" role="alert">
      {{ error }}
      <button class="text-link" :disabled="busy" @click="load">
        {{ tr("重试", "Try again") }}
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
          {{ tr("已经为你，", "A little joy,") }}<br /><em>{{
            tr("留好了。", "all yours.")
          }}</em>
        </h1>
        <h1 v-else-if="payable">
          {{ tr("最后一步，", "One last step,") }}<br /><em>{{
            tr("快乐就近了。", "then something lovely.")
          }}</em>
        </h1>
        <h1 v-else class="order-state-title">{{ statusText(order.status) }}</h1>
        <p v-if="order.status === 'paid'">
          {{
            tr(
              hasVisit
                ? "付款已收到，到店座位已确认。带着你的期待，我们工作室见。"
                : "付款已收到，订单已确认。请联系店主安排到店自提。",
              hasVisit
                ? "Payment received and your studio seats are confirmed. Bring a little inspiration. We will see you here."
                : "Payment received and your order is confirmed. Contact the host to arrange studio pickup.",
            )
          }}
        </p>
        <p v-else-if="order.status === 'paid_needs_review'" class="form-error">
          {{
            tr(
              "款项已收到，但付款确认时原时段或库存已不可用。请联系店主安排改期或退款，不要重复付款。",
              "Payment was received, but the original time or stock was no longer available when confirmed. Contact the host to reschedule or arrange a refund. Please do not pay again.",
            )
          }}
        </p>
        <p v-else-if="order.status === 'expired'">
          {{
            tr(
              "付款窗口已关闭，座位已释放。若已经扣款，请联系店主核实后再尝试。",
              "The payment window has closed and the seats have been released. If you were charged, contact the host before trying again.",
            )
          }}
        </p>
        <p
          v-else-if="
            order.status === 'payment_uncertain' ||
            (!payable && order.status === 'pending')
          "
        >
          {{
            tr(
              "正在核实付款结果，请稍候。已付款的话无需再付一次。",
              "We are checking the payment result. If you have already paid, please do not pay again.",
            )
          }}
        </p>
        <p v-else-if="order.status === 'failed'">
          {{
            tr(
              "暂未能创建收银台，可以回到购物车重新尝试。",
              "The cashier could not be created. You can return to your bag and try again.",
            )
          }}
        </p>
        <div v-if="payable" class="cashier-panel">
          <div class="cashier-heading">
            <strong>{{ tr("人民币实付", "Total in Chinese yuan") }}</strong
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
              :alt="tr('虎皮椒付款二维码', 'Hupijiao payment QR code')"
              referrerpolicy="no-referrer"
              @error="qrError = true"
            />
            <p v-if="qrError" class="form-error">
              {{
                tr(
                  "二维码暂时无法加载，请稍后刷新。",
                  "The payment QR could not load. Please refresh shortly.",
                )
              }}
            </p>
            <p>
              {{
                tr(
                  "用手机扫描二维码付款，完成后本页会自动确认。",
                  "Scan with your phone to pay. This page will confirm automatically.",
                )
              }}
            </p></template
          >
          <template v-else-if="order.payment_url"
            ><p v-if="inWeChat" class="form-help">
              {{
                tr(
                  "将在当前微信窗口打开收银台，付款后返回此页查看确认。",
                  "Checkout opens in this WeChat window. Return here after payment to see your confirmation.",
                )
              }}
            </p>
            <a
              :href="order.payment_url"
              class="button button-primary full-button"
              rel="noreferrer"
              >{{ tr("打开虎皮椒收银台", "Open Hupijiao checkout")
              }}<PhArrowRight
            /></a>
            <p class="fine-print">
              {{
                tr(
                  "付款完成后返回此页查看确认。",
                  "Return here after paying to view confirmation.",
                )
              }}
            </p></template
          >
          <p v-else class="form-help">
            {{
              tr(
                "请在电脑端打开此订单，扫描二维码付款。",
                "Open this order on a desktop to scan the payment QR.",
              )
            }}
          </p>
        </div>
        <button
          v-if="['expired', 'failed'].includes(order.status)"
          class="button button-outline"
          @click="tryAgain"
        >
          {{ tr("重新核对购物车", "Review your bag again") }}<PhArrowRight />
        </button>
        <button
          v-if="!terminal"
          class="text-link"
          :disabled="busy"
          @click="load"
        >
          <PhArrowClockwise />{{ tr("刷新付款状态", "Refresh payment status") }}
        </button>
        <div class="order-contact">
          <a :href="mapsUrl" class="text-link" target="_blank" rel="noreferrer"
            ><PhMapPin />8 Hughson St N, Hamilton</a
          >
          <p>
            {{ tr("联系店主 · 微信", "Contact the host · WeChat") }}
            {{ wechat }}
          </p>
        </div>
      </div>
      <aside class="receipt">
        <span class="eyebrow">YOUR LITTLE PLAN</span>
        <h2>{{ tr("订单明细", "Order details") }}</h2>
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
              {{ tr("人", "guests") }}<br />{{
                tr("Hamilton 当地时间", "Hamilton local time")
              }}
            </p>
            <p v-else>
              {{
                tr(
                  "到店自提 · 请联系店主安排取货",
                  "Studio pickup · Contact the host to arrange collection",
                )
              }}
            </p>
          </div>
          <strong>{{ money(line.total_cents) }}</strong>
        </article>
        <dl class="price-breakdown">
          <div v-if="order.quote.tax_mode === 'additional'">
            <dt>{{ tr("税费", "Tax") }}</dt>
            <dd>{{ money(order.quote.tax_cents) }}</dd>
          </div>
          <div>
            <dt>{{ tr("加元合计", "CAD total") }}</dt>
            <dd>{{ money(order.quote.total_cents) }}</dd>
          </div>
          <div>
            <dt>{{ tr("人民币实付", "Payment in CNY") }}</dt>
            <dd>{{ money(order.quote.cny_fen, "CNY") }}</dd>
          </div>
        </dl>
        <p class="fine-print">
          1 CAD = {{ Number(order.quote.fx_cny_per_cad) }} CNY ·
          {{ tr("汇率已固定", "Rate locked for this order") }}
        </p>
      </aside>
    </div>
    <p v-else-if="!error" class="form-help" role="status">
      {{ tr("正在读取订单…", "Loading your order…") }}
    </p>
  </section>
</template>
