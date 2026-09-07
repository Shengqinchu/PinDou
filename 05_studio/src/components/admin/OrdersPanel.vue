<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  PhArrowUpRight,
  PhMagnifyingGlass,
  PhReceipt,
  PhArrowLeft,
  PhArrowRight,
  PhX,
  PhArrowClockwise,
} from "@phosphor-icons/vue";
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
watch([status, kind, day], () => {
  page.value = 1;
  load();
});
watch(search, () => {
  page.value = 1;
  clearTimeout(debounce);
  debounce = setTimeout(load, 300);
});
watch(orderRevision, load);
onMounted(load);
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
}
</script>
<template>
  <section class="desk-orders">
    <header class="desk-page-heading">
      <div>
        <p class="desk-eyebrow">
          {{ tr("每一份期待，都在这里", "EVERY LITTLE PLAN") }}
        </p>
        <h1>{{ tr("订单管理", "Orders") }}</h1>
        <p>
          {{
            tr(
              "找到一笔订单，查看到店安排，或记录一次顺利的自提。",
              "Find an order, check a visit, or mark a happy pickup complete.",
            )
          }}
        </p>
      </div>
      <button class="desk-button secondary" :disabled="loading" @click="load">
        <PhArrowClockwise :class="{ spinning: loading }" />{{
          tr("刷新订单", "Refresh")
        }}
      </button>
    </header>
    <div class="desk-surface order-workspace">
      <div class="order-filterbar">
        <SegmentedControl
          v-model="status"
          :label="tr('订单状态', 'Order status')"
          :options="[
            { value: 'all', label: tr('全部', 'All') },
            { value: 'paid', label: tr('已付款', 'Paid') },
            { value: 'pending', label: tr('待付款', 'Unpaid') },
            { value: 'paid_needs_review', label: tr('需跟进', 'Follow-up') },
          ]"
        /><label class="desk-search"
          ><PhMagnifyingGlass /><input
            v-model="search"
            :aria-label="tr('搜索订单或顾客', 'Search orders or customers')"
            :placeholder="
              tr('搜索订单号、名字、联系方式', 'Order, name or contact')
            "
            maxlength="120" /><button
            v-if="search"
            :aria-label="tr('清除搜索', 'Clear search')"
            @click="search = ''"
          >
            <PhX /></button
        ></label>
      </div>
      <div class="order-secondary-filters">
        <label
          >{{ tr("内容", "Type")
          }}<select v-model="kind" aria-label="Order type">
            <option value="all">{{ tr("全部订单", "All orders") }}</option>
            <option value="visit">{{ tr("到店体验", "Studio visit") }}</option>
            <option value="pickup">{{ tr("实物自提", "Pickup items") }}</option>
          </select></label
        ><label
          >{{ tr("到店日期", "Visit date")
          }}<input
            v-model="day"
            type="date"
            :aria-label="tr('按到店日期筛选', 'Filter by visit date')" /></label
        ><button
          v-if="search || status !== 'all' || kind !== 'all' || day"
          class="desk-link"
          @click="reset"
        >
          {{ tr("清除筛选", "Clear filters") }}</button
        ><span>{{
          loading
            ? tr("正在查找…", "Finding orders…")
            : tr(`${total} 笔订单`, `${total} orders`)
        }}</span>
      </div>
      <p v-if="error" class="desk-error" role="alert">
        {{ error
        }}<button class="desk-link" @click="load">
          {{ tr("重试", "Try again") }}
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
              ? tr("没有找到匹配的订单", "No matching orders")
              : tr(
                  "第一份期待，还在路上。",
                  "The first little plan is on its way.",
                )
          }}
        </h2>
        <p>
          {{
            tr(
              "新订单会出现在这里；付款后自动确认座位和商品。",
              "New orders appear here. Payment automatically confirms seats and items.",
            )
          }}
        </p>
      </div>
      <template v-else
        ><div class="orders-table-wrap" :aria-busy="loading">
          <table class="desk-table">
            <thead>
              <tr>
                <th>{{ tr("顾客 / 订单", "Customer / order") }}</th>
                <th>{{ tr("内容与到店安排", "Items & visit") }}</th>
                <th>{{ tr("状态", "Status") }}</th>
                <th class="money-cell">
                  {{ tr("实付 · 人民币", "Paid amount · CNY") }}
                </th>
                <th>
                  <span class="sr-only">{{
                    tr("查看订单", "View order")
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
                    {{ tr("人", "guests") }}</span
                  ><span v-else class="table-subline">{{
                    tr("到店自提", "Studio pickup")
                  }}</span>
                </td>
                <td>
                  <span :class="['desk-status', item.status]">{{
                    item.fulfillment === "completed"
                      ? tr("已完成", "Fulfilled")
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
                      tr(
                        `查看 ${item.customer?.name} 的订单`,
                        `View order for ${item.customer?.name}`,
                      )
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
                  ? tr("已完成", "Fulfilled")
                  : statusText(item.status)
              }}</span></span
            ><span>{{
              tr(item.quote.lines[0].zh, item.quote.lines[0].en)
            }}</span
            ><small v-if="visit(item)"
              >{{ prettyDate(visit(item)!.date) }} · {{ visit(item)!.start }} ·
              {{ visit(item)!.guests }} {{ tr("人", "guests") }}</small
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
          >{{ tr("第", "Page") }} {{ page }} /
          {{ Math.max(1, Math.ceil(total / 30)) }}</span
        >
        <div>
          <button
            class="desk-icon-button"
            :disabled="page <= 1 || loading"
            :aria-label="tr('上一页', 'Previous page')"
            @click="move(-1)"
          >
            <PhArrowLeft /></button
          ><button
            class="desk-icon-button"
            :disabled="page * 30 >= total || loading"
            :aria-label="tr('下一页', 'Next page')"
            @click="move(1)"
          >
            <PhArrowRight />
          </button>
        </div>
      </footer>
    </div>
  </section>
</template>
