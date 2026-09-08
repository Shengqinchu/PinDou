<script setup lang="ts">
import { formatCopy } from "../../state";

import copyText from "../../content/components-admin-OrdersPanel.json";
import { say } from "../../state";

import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import {
  PhArrowUpRight,
  PhMagnifyingGlass,
  PhReceipt,
  PhArrowLeft,
  PhArrowRight,
  PhX,
  PhArrowClockwise,
} from "@phosphor-icons/vue";
import { useRoute } from "vue-router";
import { useDesk, localTime } from "../../admin";
import { type Order, money, statusText } from "../../commerce";
import { prettyDate, tr } from "../../state";
import SegmentedControl from "../SegmentedControl.vue";
const { request, openOrder, orderRevision } = useDesk();
const orders = ref<Order[]>([]);
const total = ref(0);
const loading = ref(false);
const error = ref("");
const search = ref("");
const status = ref("all");
const kind = ref("all");
const day = ref("");
const dayKind = ref("visit");
const fulfillment = ref("all");
const route = useRoute();
let applyingIntent = false;
const dayLabel = computed(() =>
  dayKind.value === "paid"
    ? say(copyText.payment_date_046349)
    : dayKind.value === "created"
      ? say(copyText.order_date_af2fcf)
      : say(copyText.visit_date_270402),
);
const page = ref(1);
let sequence = 0;
let debounce: ReturnType<typeof setTimeout>;
async function load() {
  const seq = ++sequence;
  loading.value = true;
  error.value = "";
  const params = new URLSearchParams({
    page: String(page.value),
    status: status.value,
    search: search.value,
    kind: kind.value,
    day_kind: dayKind.value,
    fulfillment: fulfillment.value,
  });
  if (day.value) params.set("day", day.value);
  try {
    const result = await request<{ items: Order[]; total: number }>(
      `/manage/orders?${params}`,
    );
    if (seq === sequence) {
      orders.value = result.items;
      total.value = result.total;
    }
  } catch (e) {
    if (seq === sequence) error.value = (e as Error).message;
  } finally {
    if (seq === sequence) loading.value = false;
  }
}
watch([status, kind, day, dayKind, fulfillment], () => {
  if (applyingIntent) return;
  page.value = 1;
  load();
});
watch(search, () => {
  if (applyingIntent) return;
  page.value = 1;
  clearTimeout(debounce);
  debounce = setTimeout(load, 300);
});
watch(orderRevision, load);
watch(
  () => [route.query.scope, route.query.day],
  async () => {
    const scope = String(route.query.scope || "");
    if (
      ![
        "today-orders",
        "today-received",
        "awaiting",
        "needs-review",
        "all-orders",
      ].includes(scope)
    )
      return;
    applyingIntent = true;
    clearTimeout(debounce);
    search.value = "";
    kind.value = "all";
    day.value = "";
    dayKind.value = "visit";
    fulfillment.value = "all";
    status.value = "all";
    page.value = 1;
    const selectedDay = String(route.query.day || "");
    if (scope === "today-orders" || scope === "today-received") {
      day.value = /^\d{4}-\d{2}-\d{2}$/.test(selectedDay) ? selectedDay : "";
      dayKind.value = scope === "today-orders" ? "created" : "paid";
      status.value = scope === "today-orders" ? "all" : "received";
    } else if (scope === "awaiting") {
      status.value = "received";
      fulfillment.value = "confirmed";
    } else if (scope === "needs-review") status.value = "paid_needs_review";
    await nextTick();
    applyingIntent = false;
    load();
  },
  { immediate: true },
);
onMounted(() => {
  if (!applyingIntent) load();
});
onBeforeUnmount(() => {
  clearTimeout(debounce);
  sequence++;
});
function move(delta: number) {
  page.value += delta;
  load();
}
function visit(order: Order) {
  return order.quote.lines.find((line) => line.booking)?.booking;
}
function reset() {
  search.value = "";
  status.value = "all";
  kind.value = "all";
  day.value = "";
  dayKind.value = "visit";
  fulfillment.value = "all";
}
</script>
<template>
  <section class="desk-orders">
    <header class="desk-page-heading">
      <div>
        <p class="desk-eyebrow">
          {{ say(copyText.every_little_plan_d56b7b) }}
        </p>
        <h1>{{ say(copyText.orders_9499a1) }}</h1>
        <p>
          {{ say(copyText.find_an_order_check_a_visit_or_99d0a8) }}
        </p>
      </div>
      <button class="desk-button secondary" :disabled="loading" @click="load">
        <PhArrowClockwise :class="{ spinning: loading }" />{{
          say(copyText.refresh_45153b)
        }}
      </button>
    </header>
    <div class="desk-surface order-workspace">
      <div class="order-filterbar">
        <SegmentedControl
          v-model="status"
          :label="say(copyText.order_status_ec140f)"
          :options="[
            { value: 'all', label: say(copyText.all_902ec4) },
            { value: 'received', label: say(copyText.paid_571199) },
            { value: 'pending', label: say(copyText.unpaid_20b341) },
            {
              value: 'paid_needs_review',
              label: say(copyText.followup_37bef2),
            },
          ]"
        /><label class="desk-search"
          ><PhMagnifyingGlass /><input
            v-model="search"
            :aria-label="say(copyText.search_orders_or_customers_de1a23)"
            :placeholder="say(copyText.order_name_or_contact_fbb5e2)"
            maxlength="120" /><button
            v-if="search"
            :aria-label="say(copyText.clear_search_79db5a)"
            @click="search = ''"
          >
            <PhX /></button
        ></label>
      </div>
      <div class="order-secondary-filters">
        <label
          >{{ say(copyText.type_a30db3)
          }}<select
            v-model="kind"
            :aria-label="say(copyText.order_type_04c7f1)"
          >
            <option value="all">{{ say(copyText.all_orders_442e68) }}</option>
            <option value="visit">
              {{ say(copyText.studio_visit_7d3186) }}
            </option>
            <option value="pickup">
              {{ say(copyText.pickup_items_13e9b1) }}
            </option>
          </select></label
        ><label
          >{{ say(copyText.date_basis_86ba44)
          }}<select
            v-model="dayKind"
            :aria-label="say(copyText.date_basis_86ba44)"
          >
            <option value="visit">{{ say(copyText.visit_date_270402) }}</option>
            <option value="created">
              {{ say(copyText.order_date_af2fcf) }}
            </option>
            <option value="paid">
              {{ say(copyText.payment_date_046349) }}
            </option>
          </select></label
        ><label
          >{{ dayLabel
          }}<input v-model="day" type="date" :aria-label="dayLabel" /></label
        ><label
          >{{ say(copyText.fulfillment_819fae)
          }}<select
            v-model="fulfillment"
            :aria-label="say(copyText.fulfillment_status_357064)"
          >
            <option value="all">{{ say(copyText.all_902ec4) }}</option>
            <option value="confirmed">
              {{ say(copyText.awaiting_visit_pickup_1345f1) }}
            </option>
            <option value="completed">
              {{ say(copyText.completed_ff8af6) }}
            </option>
          </select></label
        ><button
          v-if="
            search ||
            status !== 'all' ||
            kind !== 'all' ||
            day ||
            fulfillment !== 'all'
          "
          class="desk-link"
          @click="reset"
        >
          {{ say(copyText.clear_filters_0a6c6f) }}</button
        ><span>{{
          loading
            ? say(copyText.finding_orders_84576e)
            : formatCopy(copyText.message_27173e79, { v0: total })
        }}</span>
      </div>
      <p v-if="error" class="desk-error" role="alert">
        {{ error
        }}<button class="desk-link" @click="load">
          {{ say(copyText.try_again_c3273b) }}
        </button>
      </p>
      <div
        v-else-if="loading && !orders.length"
        class="order-skeletons"
        aria-busy="true"
      >
        <div v-for="n in 4" :key="n" class="desk-skeleton" />
      </div>
      <div v-else-if="!orders.length" class="desk-empty orders-empty">
        <PhReceipt :size="34" weight="light" />
        <h2>
          {{
            search || status !== "all" || kind !== "all" || day
              ? say(copyText.no_matching_orders_80085b)
              : say(copyText.the_first_little_plan_is_on_its_5a73c4)
          }}
        </h2>
        <p>
          {{
            say(
              copyText.new_orders_appear_here_payment_automatically_confirms_9920cd,
            )
          }}
        </p>
      </div>
      <template v-else
        ><div class="orders-table-wrap" :aria-busy="loading">
          <table class="desk-table">
            <thead>
              <tr>
                <th>{{ say(copyText.customer_order_0709d1) }}</th>
                <th>{{ say(copyText.items_visit_fd0411) }}</th>
                <th>{{ say(copyText.status_6c4e92) }}</th>
                <th class="money-cell">
                  {{ say(copyText.paid_amount_cny_bd0d44) }}
                </th>
                <th>
                  <span class="sr-only">{{
                    say(copyText.view_order_cf9a8a)
                  }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in orders" :key="item.id">
                <td>
                  <button class="customer-link" @click="openOrder(item.id)">
                    <span class="customer-monogram">{{
                      item.customer?.name.slice(0, 1)
                    }}</span
                    ><span
                      ><strong>{{ item.customer?.name }}</strong
                      ><small
                        >{{ item.id.slice(-10) }} ·
                        {{ localTime(item.created_at) }}</small
                      ></span
                    >
                  </button>
                </td>
                <td>
                  <strong class="order-items-title"
                    >{{ tr(item.quote.lines[0].zh, item.quote.lines[0].en)
                    }}<small v-if="item.quote.lines.length > 1">
                      +{{ item.quote.lines.length - 1 }}</small
                    ></strong
                  ><span v-if="visit(item)" class="table-subline"
                    >{{ prettyDate(visit(item)!.date) }} ·
                    {{ visit(item)!.start }} · {{ visit(item)!.guests }}
                    {{ say(copyText.guests_24bfb5) }}</span
                  ><span v-else class="table-subline">{{
                    say(copyText.studio_pickup_c13b87)
                  }}</span>
                </td>
                <td>
                  <span :class="['desk-status', item.status]">{{
                    item.fulfillment === "completed"
                      ? say(copyText.fulfilled_bf1ec7)
                      : statusText(item.status)
                  }}</span>
                </td>
                <td class="money-cell">
                  <strong>{{ money(item.quote.cny_fen, "CNY") }}</strong
                  ><small class="table-subline">{{
                    money(item.quote.total_cents)
                  }}</small>
                </td>
                <td>
                  <button
                    class="desk-icon-button"
                    :aria-label="
                      formatCopy(copyText.message_a88a0e90, {
                        v0: item.customer?.name,
                      })
                    "
                    @click="openOrder(item.id)"
                  >
                    <PhArrowUpRight />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="mobile-order-list">
          <button
            v-for="item in orders"
            :key="item.id"
            class="mobile-order"
            @click="openOrder(item.id)"
          >
            <span class="mobile-order-top"
              ><strong>{{ item.customer?.name }}</strong
              ><span :class="['desk-status', item.status]">{{
                item.fulfillment === "completed"
                  ? say(copyText.fulfilled_bf1ec7)
                  : statusText(item.status)
              }}</span></span
            ><span>{{
              tr(item.quote.lines[0].zh, item.quote.lines[0].en)
            }}</span
            ><small v-if="visit(item)"
              >{{ prettyDate(visit(item)!.date) }} · {{ visit(item)!.start }} ·
              {{ visit(item)!.guests }} {{ say(copyText.guests_24bfb5) }}</small
            ><span class="mobile-order-bottom"
              ><small>{{ localTime(item.created_at) }}</small
              ><strong
                >{{ money(item.quote.cny_fen, "CNY") }}
                <PhArrowUpRight /></strong
            ></span>
          </button></div
      ></template>
      <footer class="desk-pagination">
        <span
          >{{ say(copyText.page_0bd3e3) }} {{ page }} /
          {{ Math.max(1, Math.ceil(total / 30)) }}</span
        >
        <div>
          <button
            class="desk-icon-button"
            :disabled="page <= 1 || loading"
            :aria-label="say(copyText.previous_page_e70a7e)"
            @click="move(-1)"
          >
            <PhArrowLeft /></button
          ><button
            class="desk-icon-button"
            :disabled="page * 30 >= total || loading"
            :aria-label="say(copyText.next_page_5354f3)"
            @click="move(1)"
          >
            <PhArrowRight />
          </button>
        </div>
      </footer>
    </div>
  </section>
</template>
