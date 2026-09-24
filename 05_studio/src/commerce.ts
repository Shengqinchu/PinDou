import { contentModule } from "./content-store";
const contentLabels = contentModule("data-commerce-labels", contentLabelsDefault);
const contentMessages = contentModule("data-commerce-messages", contentMessagesDefault);
const copyText = contentModule("commerce", copyTextDefault);
import contentLabelsDefault from "./content/data-commerce-labels.json";
import contentMessagesDefault from "./content/data-commerce-messages.json";
import copyTextDefault from "./content/commerce.json";
import { say } from "./state";
import { computed, ref, watch } from "vue";
import { locale, tr } from "./state";
import { notify } from "./ui";
import { customerToken } from "./account-storage";
import accountDefaults from "./content/account.json";
const accountMessages=contentModule("account",accountDefaults) as Record<string,string[]>;
import walletDefaults from './content/wallet.json';
const walletMessages=contentModule('wallet',walletDefaults) as Record<string,string[]>;
import wechatDefaults from './content/wechat.json';
const wechatMessages=contentModule('wechat',wechatDefaults) as Record<string,string[]>;
import bookingProfileDefaults from './content/booking-profile.json';
const bookingProfileMessages=contentModule('booking-profile',bookingProfileDefaults);
import cancellationDefaults from './content/reservation-cancellation.json';
import notificationMessages from './content/customer-notifications.json';
import adminVisitMessages from './content/admin-visits.json';
import shopOrderingDefaults from './content/shop-ordering.json';
const shopOrderingMessages=contentModule('shop-ordering',shopOrderingDefaults) as Record<string,string[]>;
import miniappDefaults from './content/miniapp.json';
const miniappMessages=contentModule('miniapp',miniappDefaults) as Record<string,string[]>;
const cancellationMessages=contentModule('reservation-cancellation',cancellationDefaults) as Record<string,string[]>;

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
  variant_id?: string;
  choice_id?: string;
};
export type ProductOption = {id:string;zh:string;en:string};
export type ProductVariant = ProductOption & {price_cents?:number|null};
export type QuantityOffer = {quantity:number;price_cents:number};
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
  variants?: ProductVariant[];
  choices?: ProductOption[];
  choiceZh?: string;
  choiceEn?: string;
  quantity_offer?: QuantityOffer | null;
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
  variant_zh?: string;
  variant_en?: string;
  choice_zh?: string;
  choice_en?: string;
  discount_cents?: number;
};
export type Quote = {
  mode?: 'manual';
  discount_cents?: number;
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
    delivery_method?: 'pickup' | 'courier';
    address?: string;
  };
};

const messages: Record<string, string[]> = contentMessages as Record<
  string,
  string[]
>;

export class CommerceError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public requestId?: string,
  ) {
    super(message);
  }
}
export async function commerceApi<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    const token=(path.startsWith("/auth/")||path.startsWith("/reservations")||path==='/shop/orders')?customerToken():"";
    response = await fetch(`/studio-api${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(token?{Authorization:"Bearer "+token}:{}), ...init.headers },
      cache: "no-store",
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    // No HTTP response: keep checkout's uncertain-result recovery semantics.
    throw new CommerceError(
      say(copyText.we_could_not_connect_check_your_connection_b4bde6),
      0,
    );
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const words = (adminVisitMessages as Record<string,string[]>)[data.detail] || shopOrderingMessages[data.detail] || (data.detail==='booking_profile_changed'?bookingProfileMessages.changed:undefined) || (notificationMessages as Record<string,string[]>)[data.detail] || cancellationMessages[data.detail] || messages[data.detail] || accountMessages[data.detail] || walletMessages[data.detail] || wechatMessages[data.detail] || miniappMessages[data.detail];
    if (words)
      throw new CommerceError(say(words), response.status, data.detail, response.headers.get('X-Request-ID') || undefined);
    if (response.status === 401 || response.status === 403)
      throw new CommerceError(
        say(copyText.please_sign_in_with_your_administrator_account_e74731),
        response.status,
      );
    if (response.status === 429)
      throw new CommerceError(
        say(copyText.too_many_requests_please_try_again_later_e30269),
        response.status,
      );
    if (response.status === 422)
      throw new CommerceError(
        say(copyText.check_the_required_fields_dates_and_times_29fdcf),
        response.status,
      );
    throw new CommerceError(
      say(copyText.we_could_not_complete_this_please_try_928dc4),
      response.status,
      typeof data.detail==='string'?data.detail:undefined,
      response.headers.get('X-Request-ID') || undefined,
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
export function addToBag(product_id: string, booking?: Booking, selection?:{variant_id:string;choice_id:string}, silent=false) {
  if (checkoutBusy.value) return;
  const line = bag.value.find(
    (v) =>
      v.product_id === product_id &&
      (v.variant_id||'') === (selection?.variant_id||'') && (v.choice_id||'') === (selection?.choice_id||'') &&
      JSON.stringify(v.booking || null) === JSON.stringify(booking || null),
  );
  if (line && !booking) line.quantity = Math.min(20, line.quantity + 1);
  else if (!line)
    bag.value.push({
      key: crypto.randomUUID(),
      product_id,
      quantity: 1,
      booking: booking || null,
      ...(selection||{}),
    });
  if(!silent)notify(copyText.message_1186a6e2[0],copyText.message_1186a6e2[1],"success","cart");
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
    currencyDisplay: currency === "CAD" ? "code" : "symbol",
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
  const labels: Record<string, string[]> = contentLabels as Record<
    string,
    string[]
  >;
  return say(labels[status] || [status, status]);
}
