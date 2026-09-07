<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  PhArrowClockwise,
  PhCheck,
  PhPlus,
  PhTrash,
} from "@phosphor-icons/vue";
import { hamiltonDate, prettyDate, tr } from "../state";
import {
  commerceApi,
  money,
  statusText,
  type Order,
  type Product,
  type Settings,
} from "../commerce";
const props = defineProps<{ token: string }>();
const tab = ref("orders");
const busy = ref(false);
const error = ref("");
const saved = ref("");
const settings = ref<Settings>();
const products = ref<Product[]>([]);
const orders = ref<Order[]>([]);
const total = ref(0);
const page = ref(1);
const paymentConfigured = ref(false);
const dayNames = [
  ["周一", "Monday"],
  ["周二", "Tuesday"],
  ["周三", "Wednesday"],
  ["周四", "Thursday"],
  ["周五", "Friday"],
  ["周六", "Saturday"],
  ["周日", "Sunday"],
];
const headers = () => ({ Authorization: `Bearer ${props.token}` });
async function loadOrders() {
  const result = await commerceApi<{ items: Order[]; total: number }>(
    `/manage/orders?page=${page.value}`,
    { headers: headers() },
  );
  orders.value = result.items;
  total.value = result.total;
}
async function load() {
  busy.value = true;
  error.value = "";
  saved.value = "";
  try {
    const data = await commerceApi<{
      settings: Settings;
      products: Product[];
      payment_configured: boolean;
    }>("/manage/commerce", { headers: headers() });
    settings.value = data.settings;
    products.value = data.products;
    paymentConfigured.value = data.payment_configured;
    await loadOrders();
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
onMounted(load);
async function saveSchedule() {
  if (!settings.value) return;
  busy.value = true;
  error.value = "";
  saved.value = "";
  try {
    settings.value = await commerceApi<Settings>("/manage/schedule", {
      method: "PUT",
      headers: headers(),
      body: JSON.stringify(settings.value),
    });
    saved.value = tr(
      "排班与结账设置已保存。",
      "Schedule and checkout settings saved.",
    );
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
function priceInput(p: Product, e: Event) {
  const value = (e.target as HTMLInputElement).value;
  p.price_cents = value === "" ? null : Math.round(Number(value) * 100);
}
function taxInput(e: Event) {
  if (settings.value)
    settings.value.tax_bps = Math.round(
      Number((e.target as HTMLInputElement).value) * 100,
    );
}
function addOverride() {
  settings.value?.overrides.push({
    date: hamiltonDate(),
    enabled: false,
    start: "10:00",
    end: "22:00",
  });
}
function addProduct() {
  products.value.push({
    id: "item-" + crypto.randomUUID().slice(0, 8),
    kind: "physical",
    category: "tools",
    zh: "",
    en: "",
    detailZh: "",
    detailEn: "",
    image: "studio-07",
    price_cents: null,
    stock: 0,
    active: false,
    version: 1,
  });
}
async function saveProduct(p: Product) {
  busy.value = true;
  error.value = "";
  saved.value = "";
  try {
    const result = await commerceApi<Product>(`/manage/products/${p.id}`, {
      method: "PUT",
      headers: headers(),
      body: JSON.stringify(p),
    });
    products.value = products.value.map((v) =>
      v.id === result.id ? result : v,
    );
    saved.value = tr(
      "商品已保存，售价和库存会立即更新。",
      "Product saved. Price and inventory are updated.",
    );
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
async function saveOrder(order: Order, completed: boolean) {
  busy.value = true;
  error.value = "";
  saved.value = "";
  try {
    const result = await commerceApi<Order>(`/manage/orders/${order.id}`, {
      method: "PATCH",
      headers: headers(),
      body: JSON.stringify({
        completed,
        staff_note: order.staff_note || "",
        version: order.version,
      }),
    });
    orders.value = orders.value.map((o) => (o.id === result.id ? result : o));
    saved.value = tr(
      "订单备注与交付状态已保存。",
      "Order note and fulfillment status saved.",
    );
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
async function movePage(delta: number) {
  page.value += delta;
  busy.value = true;
  try {
    await loadOrders();
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <section class="commerce-admin">
    <div class="admin-tabs">
      <button :class="{ active: tab === 'orders' }" @click="tab = 'orders'">
        {{ tr("订单与到店安排", "Orders & visits") }}</button
      ><button
        :class="{ active: tab === 'schedule' }"
        @click="tab = 'schedule'"
      >
        {{ tr("营业排班与收款", "Schedule & checkout") }}</button
      ><button
        :class="{ active: tab === 'products' }"
        @click="tab = 'products'"
      >
        {{ tr("商品与价格", "Products & pricing") }}</button
      ><button :disabled="busy" @click="load">
        <PhArrowClockwise /> {{ tr("刷新", "Refresh") }}
      </button>
    </div>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <p v-if="saved" class="admin-feedback" role="status">
      <PhCheck /> {{ saved }}
    </p>
    <template v-if="tab === 'orders'"
      ><p v-if="!orders.length" class="admin-feedback">
        {{
          tr(
            "这里会显示真实订单，以及已确认的到店日期、时间和人数。",
            "Real orders and confirmed visit dates, times and guest counts appear here.",
          )
        }}
      </p>
      <article v-for="order in orders" :key="order.id" class="admin-panel">
        <div class="admin-order-heading">
          <div>
            <strong>{{ order.id }}</strong>
            <p>
              <small
                >{{
                  new Date(order.created_at * 1000).toLocaleString(
                    tr("zh-CN", "en-CA"),
                    { timeZone: "America/Toronto" },
                  )
                }}
                · Hamilton</small
              >
            </p>
          </div>
          <strong>{{ statusText(order.status) }}</strong>
        </div>
        <p v-if="order.status === 'paid_needs_review'" class="form-error">
          {{
            tr(
              "款项已收到，原座位或库存无法履约。请联系顾客改期或通过虎皮椒处理退款。",
              "Payment received, but the original seats or stock could not be fulfilled. Contact the customer to reschedule or refund through Hupijiao.",
            )
          }}
        </p>
        <div class="admin-order-customer">
          <strong>{{ order.customer?.name }}</strong> ·
          {{ order.customer?.contact_method }} · {{ order.customer?.contact }}
          <p v-if="order.customer?.notes">{{ order.customer.notes }}</p>
        </div>
        <ul class="admin-order-items">
          <li v-for="(line, i) in order.quote.lines" :key="i">
            <strong>{{ tr(line.zh, line.en) }}</strong> ·
            {{ money(line.total_cents)
            }}<template v-if="line.booking"
              ><br />{{ prettyDate(line.booking.date) }} ·
              {{ line.booking.start }}–{{ line.booking.end }} ·
              {{ line.booking.guests }} {{ tr("人", "guests") }}</template
            ><template v-else>
              · {{ line.quantity }}
              {{ tr("件 · 到店自提", "items · studio pickup") }}</template
            >
          </li>
        </ul>
        <p>
          {{ tr("加元合计", "CAD total") }}
          {{ money(order.quote.total_cents) }} ·
          {{ tr("人民币实付", "Paid in CNY") }}
          {{ money(order.quote.cny_fen, "CNY") }}
        </p>
        <label class="field"
          >{{ tr("内部备注", "Staff note")
          }}<textarea v-model="order.staff_note" rows="2" maxlength="1500" />
        </label>
        <div class="empty-actions">
          <button
            class="button button-outline"
            :disabled="busy"
            @click="saveOrder(order, order.fulfillment === 'completed')"
          >
            {{ tr("保存备注", "Save note") }}</button
          ><button
            v-if="order.status === 'paid'"
            class="button button-primary"
            :disabled="busy"
            @click="saveOrder(order, order.fulfillment !== 'completed')"
          >
            {{
              order.fulfillment === "completed"
                ? tr("恢复为待到店／自提", "Reopen fulfillment")
                : tr("标记已到店／已自提", "Mark fulfilled")
            }}<PhCheck />
          </button>
        </div>
      </article>
      <div v-if="total > 30" class="empty-actions">
        <button
          class="button button-outline"
          :disabled="page <= 1 || busy"
          @click="movePage(-1)"
        >
          {{ tr("上一页", "Previous") }}</button
        ><span>{{ page }} / {{ Math.ceil(total / 30) }}</span
        ><button
          class="button button-outline"
          :disabled="page * 30 >= total || busy"
          @click="movePage(1)"
        >
          {{ tr("下一页", "Next") }}
        </button>
      </div></template
    >
    <form
      v-if="tab === 'schedule' && settings"
      class="admin-panel"
      @submit.prevent="saveSchedule"
    >
      <h2>{{ tr("营业时间与座位", "Opening hours & seats") }}</h2>
      <p class="fine-print">
        {{
          tr(
            "所有时间按 Hamilton 计算。先保存草稿，确定后开启网上购买。休息日不显示可用时段，已付款订单不会因修改排班而取消。",
            "All times are local to Hamilton. Save a draft, then open online purchases when ready. Closed days offer no times; schedule changes do not cancel paid orders.",
          )
        }}
      </p>
      <div class="admin-settings-grid">
        <label class="field"
          >{{ tr("同时接待人数（未定填 0）", "Capacity (0 until decided)")
          }}<input
            v-model.number="settings.capacity"
            name="capacity"
            type="number"
            min="0"
            max="100"
            required /></label
        ><label class="field"
          >{{ tr("最少提前多少分钟购买", "Minimum booking notice (minutes)")
          }}<input
            v-model.number="settings.notice_minutes"
            type="number"
            min="0"
            max="1440"
            required
        /></label>
      </div>
      <div
        v-for="row in settings.weekly"
        :key="row.day"
        class="admin-hours-row"
      >
        <label
          ><input v-model="row.enabled" type="checkbox" />{{
            tr(dayNames[row.day][0], dayNames[row.day][1])
          }}</label
        ><input
          v-model="row.start"
          type="time"
          step="1800"
          :disabled="!row.enabled"
          :aria-label="tr('开门时间', 'Opening time')"
          required
        /><span>–</span
        ><input
          v-model="row.end"
          type="time"
          step="1800"
          :disabled="!row.enabled"
          :aria-label="tr('打烊时间', 'Closing time')"
          required
        />
      </div>
      <h3 class="override-heading">
        {{ tr("特别日期安排", "Date exceptions") }}
      </h3>
      <div
        v-for="(row, i) in settings.overrides"
        :key="i"
        class="admin-override"
      >
        <label class="field"
          >{{ tr("日期", "Date")
          }}<input v-model="row.date" type="date" required
        /></label>
        <div class="admin-hours-row">
          <label
            ><input v-model="row.enabled" type="checkbox" />{{
              tr("营业", "Open")
            }}</label
          ><input
            v-model="row.start"
            type="time"
            step="1800"
            :disabled="!row.enabled"
            :aria-label="tr('开门时间', 'Opening time')"
            required
          /><span>–</span
          ><input
            v-model="row.end"
            type="time"
            step="1800"
            :disabled="!row.enabled"
            :aria-label="tr('打烊时间', 'Closing time')"
            required
          /><button
            type="button"
            class="icon-button"
            :aria-label="tr('移除特别日期', 'Remove exception')"
            @click="settings.overrides.splice(i, 1)"
          >
            <PhTrash />
          </button>
        </div>
      </div>
      <button type="button" class="text-link" @click="addOverride">
        <PhPlus />{{ tr("添加特别日期", "Add a date exception") }}
      </button>
      <h2 class="override-heading">{{ tr("付款金额", "Payment amounts") }}</h2>
      <p class="fine-print">
        {{
          tr(
            "虎皮椒按人民币收款；汇率会在每笔订单创建时固定。下面的税费方式用于计算客人最终实付金额。",
            "Hupijiao collects CNY. The exchange rate is fixed when each order is created. Tax settings below determine the final payable amount.",
          )
        }}
      </p>
      <div class="admin-settings-grid">
        <label class="field"
          >{{ tr("1 加元兑换人民币", "CNY per 1 CAD")
          }}<input
            v-model="settings.fx_cny_per_cad"
            inputmode="decimal"
            name="fx"
            required /></label
        ><label class="field"
          >{{ tr("商品标价如何计税", "Tax treatment")
          }}<select v-model="settings.tax_mode" name="tax_mode">
            <option value="unconfirmed">
              {{ tr("尚未确认", "Not confirmed") }}
            </option>
            <option value="included">
              {{
                tr("标价就是最终价（含税）", "Prices are final (tax included)")
              }}
            </option>
            <option value="additional">
              {{ tr("标价另加税费", "Add tax to listed prices") }}
            </option>
          </select></label
        ><label v-if="settings.tax_mode === 'additional'" class="field"
          >{{ tr("税率 %", "Tax rate %")
          }}<input
            :value="settings.tax_bps / 100"
            type="number"
            min="0"
            max="30"
            step="0.01"
            required
            @input="taxInput"
        /></label>
      </div>
      <p class="admin-feedback">
        {{
          paymentConfigured
            ? tr("虎皮椒商户已连接。", "Hupijiao merchant is connected.")
            : tr(
                "虎皮椒商户尚未连接，暂不能收款。",
                "Hupijiao merchant is not connected yet.",
              )
        }}
      </p>
      <label class="admin-open-toggle"
        ><input v-model="settings.enabled" type="checkbox" name="enabled" />{{
          tr("开放网上购买", "Open online purchases")
        }}</label
      >
      <p class="fine-print">
        {{
          tr(
            "开启前需要填写接待人数、营业日，并确认售价的税费方式。",
            "Before opening, set capacity, opening days and the tax treatment of your prices.",
          )
        }}
      </p>
      <button type="submit" class="button button-primary" :disabled="busy">
        {{ tr("保存排班与收款设置", "Save schedule & checkout") }}<PhCheck />
      </button>
    </form>
    <section v-if="tab === 'products'" class="admin-panel">
      <h2>{{ tr("商品与体验套餐", "Products & experiences") }}</h2>
      <p class="fine-print">
        {{
          tr(
            "售价单位为加元。实物库存填写当前剩余数量，支付成功时自动扣减；退款后是否重新上架，由你核实后修改。未上架商品可作为预告展示。",
            "Prices are in CAD. Physical stock is the current remaining quantity and decreases after payment. Review returned items before restocking. Unpublished products appear as previews.",
          )
        }}
      </p>
      <div class="admin-product-grid">
        <form
          v-for="p in products"
          :key="p.id"
          class="admin-product"
          @submit.prevent="saveProduct(p)"
        >
          <h3>
            {{ p.zh || tr("新商品", "New product") }}
            <small>· {{ p.id }}</small>
          </h3>
          <div class="form-grid">
            <label class="field"
              >{{ tr("中文名称", "Chinese name")
              }}<input v-model="p.zh" maxlength="90" required /></label
            ><label class="field"
              >{{ tr("英文名称", "English name")
              }}<input v-model="p.en" maxlength="140" required /></label
            ><label class="field"
              >{{ tr("售价 CA$", "Price CA$")
              }}<input
                :value="p.price_cents === null ? '' : p.price_cents / 100"
                type="number"
                min="0.01"
                max="10000"
                step="0.01"
                :required="p.active"
                @input="priceInput(p, $event)" /></label
            ><label v-if="p.kind === 'physical'" class="field"
              >{{ tr("剩余库存", "Remaining stock")
              }}<input
                v-model.number="p.stock"
                type="number"
                min="0"
                max="100000"
                step="1"
                required /></label
            ><label v-if="p.kind === 'physical'" class="field"
              >{{ tr("分类", "Category")
              }}<select v-model="p.category">
                <option value="tools">
                  {{ tr("工具与配件", "Tools & fittings") }}
                </option>
                <option value="beads">
                  {{ tr("拼豆补充装", "Bead refills") }}
                </option>
                <option value="finished">
                  {{ tr("手作成品", "Finished pieces") }}
                </option>
              </select></label
            ><label class="field"
              >{{ tr("图片编号", "Photo")
              }}<select v-model="p.image">
                <option
                  v-for="n in 15"
                  :key="n"
                  :value="`studio-${String(n).padStart(2, '0')}`"
                >
                  studio-{{ String(n).padStart(2, "0") }}
                </option>
                <option
                  v-for="n in ['02', '04', '05', '07', '10', '11', '13', '20']"
                  :key="n"
                  :value="`journal-${n}`"
                >
                  journal-{{ n }}
                </option>
              </select></label
            ><label class="field field-full"
              >{{ tr("中文说明", "Chinese description")
              }}<textarea
                v-model="p.detailZh"
                rows="2"
                maxlength="500"
              /></label
            ><label class="field field-full"
              >{{ tr("英文说明", "English description")
              }}<textarea v-model="p.detailEn" rows="2" maxlength="700" />
            </label>
          </div>
          <label class="consent-label"
            ><input v-model="p.active" type="checkbox" /><span>{{
              tr("上架出售", "Publish for sale")
            }}</span></label
          ><button class="button button-outline full-button" :disabled="busy">
            {{ tr("保存商品", "Save product") }}<PhCheck />
          </button>
        </form>
      </div>
      <button class="text-link" @click="addProduct">
        <PhPlus />{{ tr("添加商品", "Add a product") }}
      </button>
    </section>
  </section>
</template>
