import { computed, ref, watch } from "vue";
import { locale, tr } from "./state";

export type Booking = {
  date: string;
  start: string;
  end: string;
  guests: number;
};
export type CartLine = {
  key: string;
  product_id: string;
  quantity: number;
  booking?: Booking | null;
};
export type Product = {
  id: string;
  kind: "experience" | "physical";
  category: string;
  zh: string;
  en: string;
  detailZh: string;
  detailEn: string;
  image: string;
  price_cents: number | null;
  stock: number;
  available_stock?: number;
  active: boolean;
  version: number;
};
export type Hours = {
  day: number;
  enabled: boolean;
  start: string;
  end: string;
};
export type Settings = {
  enabled: boolean;
  capacity: number;
  weekly: Hours[];
  overrides: { date: string; enabled: boolean; start: string; end: string }[];
  fx_cny_per_cad: string;
  tax_mode: "unconfirmed" | "included" | "additional";
  tax_bps: number;
  notice_minutes: number;
  version: number;
};
export type Catalog = {
  products: Product[];
  settings: Settings;
  checkout_ready: boolean;
  payment_configured: boolean;
};
export type Slot = {
  start: string;
  end: string;
  remaining: number;
  available: boolean;
};
export type Availability = {
  date: string;
  slots: Slot[];
  reason: "not_open" | "closed" | "open";
  timezone: string;
};
export type QuoteLine = Omit<CartLine, "key"> & {
  zh: string;
  en: string;
  image: string;
  kind: string;
  unit_cents: number;
  total_cents: number;
};
export type Quote = {
  lines: QuoteLine[];
  subtotal_cents: number;
  tax_cents: number;
  total_cents: number;
  cny_fen: number;
  fx_cny_per_cad: string;
  tax_mode: string;
  tax_bps: number;
  quote_id: string;
};
export type Order = {
  id: string;
  status: string;
  created_at: number;
  expires_at: number;
  hold_until: number;
  paid_at: number | null;
  fulfillment: string;
  quote: Quote;
  payment_url?: string;
  qr_url?: string;
  version: number;
  staff_note?: string;
  customer?: {
    name: string;
    contact_method: string;
    contact: string;
    notes: string;
  };
};

const messages: Record<string, [string, string]> = {
  checkout_not_open: [
    "网上购买即将开放，请稍后再来。",
    "Online purchases will open soon. Please check back.",
  ],
  slot_unavailable: [
    "这个时段的座位不足或已过期，请重新选择。",
    "This time is no longer available. Please choose another.",
  ],
  stock_unavailable: [
    "有商品库存不足，请调整数量。",
    "An item has insufficient stock. Please update the quantity.",
  ],
  product_unavailable: [
    "有商品暂未上架，请将它移出购物车。",
    "An item is unavailable. Please remove it from your bag.",
  ],
  price_changed: [
    "价格已更新，请核对新的金额后再次结账。",
    "Prices have changed. Review the updated total before paying.",
  ],
  version_conflict: [
    "其他操作已更新这份资料，请刷新后再保存。",
    "This was updated elsewhere. Refresh before saving.",
  ],
  capacity_below_reservations: [
    "人数上限不能低于已经确认或暂留的座位数。",
    "Capacity cannot be lower than existing reservations.",
  ],
  stock_below_holds: [
    "库存不能低于付款中的暂留数量。",
    "Stock cannot be lower than the quantity held for payment.",
  ],
  order_not_found: [
    "无法读取订单，请用下单的浏览器打开。",
    "Please open this order in the browser you used to purchase.",
  ],
  request_changed: [
    "这次结账内容已变化，请刷新购物车。",
    "Checkout details changed. Please refresh your bag.",
  ],
  order_not_paid: [
    "订单尚未完成付款，不能标记为已交付。",
    "This order has not been paid and cannot be fulfilled.",
  ],
  order_amount_limit: [
    "本单金额超出在线支付范围，请分开购买。",
    "This order exceeds the online limit. Please split your purchase.",
  ],
};

export class CommerceError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function commerceApi<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`/studio-api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const words = messages[data.detail];
    if (words) throw new CommerceError(tr(...words), response.status);
    if (response.status === 401 || response.status === 403)
      throw new CommerceError(
        tr(
          "请使用管理员账号重新登录。",
          "Please sign in with your administrator account.",
        ),
        response.status,
      );
    if (response.status === 429)
      throw new CommerceError(
        tr(
          "操作较多，请稍后再试。",
          "Too many requests. Please try again later.",
        ),
        response.status,
      );
    if (response.status === 422)
      throw new CommerceError(
        tr(
          "请检查必填项、时间和金额，修正后再试。",
          "Check the required fields, times and amounts, then try again.",
        ),
        response.status,
      );
    throw new CommerceError(
      tr(
        "暂时未能完成，请重试。",
        "We could not complete this. Please try again.",
      ),
      response.status,
    );
  }
  return data as T;
}

function stored<T>(key: string, fallback: T): T {
  try {
    return JSON.parse(localStorage.getItem(key) || "null") ?? fallback;
  } catch {
    return fallback;
  }
}
function persist(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* In-memory shopping remains available. */
  }
}
function loadBag(): CartLine[] {
  const raw = stored<unknown>("puppy-shopping-bag-v2", []);
  if (!Array.isArray(raw)) return [];
  return raw
    .slice(0, 20)
    .filter(
      (v) =>
        v &&
        typeof v.key === "string" &&
        /^[a-z][a-z0-9_-]{0,39}$/.test(v.product_id) &&
        Number.isInteger(v.quantity) &&
        v.quantity > 0 &&
        v.quantity <= 20 &&
        (!v.booking ||
          (typeof v.booking.date === "string" &&
            typeof v.booking.start === "string" &&
            typeof v.booking.end === "string" &&
            Number.isInteger(v.booking.guests))),
    );
}
export const bag = ref<CartLine[]>(loadBag());
export const bagCount = computed(() =>
  bag.value.reduce((n, line) => n + line.quantity, 0),
);
export const checkoutBusy = ref(false);
watch(bag, (value) => persist("puppy-shopping-bag-v2", value), { deep: true });
export const catalog = ref<Catalog>();
export async function loadCatalog() {
  catalog.value = await commerceApi<Catalog>("/catalog");
  return catalog.value;
}
export function addToBag(product_id: string, booking?: Booking) {
  if (checkoutBusy.value) return;
  const line = bag.value.find(
    (v) =>
      v.product_id === product_id &&
      JSON.stringify(v.booking || null) === JSON.stringify(booking || null),
  );
  if (line && !booking) line.quantity = Math.min(20, line.quantity + 1);
  else if (!line)
    bag.value.push({
      key: crypto.randomUUID(),
      product_id,
      quantity: 1,
      booking: booking || null,
    });
}
export function removeLine(key: string) {
  if (!checkoutBusy.value) bag.value = bag.value.filter((v) => v.key !== key);
}
export function quantityChange(key: string, delta: number) {
  if (checkoutBusy.value) return;
  const line = bag.value.find((v) => v.key === key);
  if (!line || line.booking) return;
  line.quantity = Math.max(1, Math.min(20, line.quantity + delta));
}
export function cartPayload() {
  return bag.value.map(({ key: _key, ...line }) => line);
}
export function money(cents: number, currency = "CAD") {
  return new Intl.NumberFormat(locale.value === "zh" ? "zh-CN" : "en-CA", {
    style: "currency",
    currency,
    currencyDisplay: "symbol",
    minimumFractionDigits: 2,
  }).format(cents / 100);
}
export function orderKey(id: string) {
  return stored<Record<string, string>>("puppy-order-access-v2", {})[id] || "";
}
export function rememberOrder(id: string, key: string) {
  const keys = stored<Record<string, string>>("puppy-order-access-v2", {});
  keys[id] = key;
  persist("puppy-order-access-v2", keys);
  recentOrder.value = id;
  persist("puppy-recent-order-v2", id);
}
export const recentOrder = ref(stored<string>("puppy-recent-order-v2", ""));
export function statusText(status: string) {
  const labels: Record<string, [string, string]> = {
    creating: ["正在准备付款", "Preparing payment"],
    pending: ["等待付款", "Awaiting payment"],
    payment_uncertain: ["正在核实支付状态", "Checking payment status"],
    paid: ["付款成功 · 已确认", "Paid · Confirmed"],
    paid_needs_review: [
      "已付款 · 需要店主处理",
      "Paid · Host assistance needed",
    ],
    expired: ["付款时间已过", "Payment time expired"],
    failed: ["付款页面未能打开", "Payment could not be opened"],
    refunded: ["已退款", "Refunded"],
  };
  return tr(...(labels[status] || [status, status]));
}
