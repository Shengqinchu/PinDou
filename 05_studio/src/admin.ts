import copyText from "./content/admin.json";
import { say } from "./state";
import { computed, inject, ref, type InjectionKey } from "vue";
import {
  CommerceError,
  commerceApi,
  type Order,
  type Product,
  type Settings,
} from "./commerce";
import { hamiltonDate, tr } from "./state";
import { notify } from "./ui";

export type DeskIntent =
  | "today-orders"
  | "today-received"
  | "awaiting"
  | "needs-review"
  | "today-visits"
  | "all-orders";

export type AuditEvent = {
  id: number;
  order_id?: string;
  created_at: number;
  event: string;
  actor: string;
  detail: string;
};
export type OrderDetail = Order & {
  provider_id?: string;
  trade_id?: string;
  events: AuditEvent[];
};
export type CalendarDay = {
  date: string;
  hours: { start: string; end: string } | null;
  entries: {
    order_id: string;
    name: string;
    start: string;
    end: string;
    guests: number;
    status: string;
    fulfillment: string;
  }[];
};
export type Overview = {
  date: string;
  metrics: {
    orders_today: number;
    needs_review: number;
    awaiting_fulfillment: number;
    received_cny_fen: number;
    guests_today: number;
  };
  days: CalendarDay[];
  recent_orders: Order[];
  catalog: { published: number; drafts: number; low_stock: number };
  checkout_ready: boolean;
  payment_configured: boolean;
};
export function createDesk(token: string, expired: () => void) {
  const settings = ref<Settings>();
  const savedSettings = ref("");
  const products = ref<Product[]>([]);
  const overview = ref<Overview>();
  const calendar = ref<CalendarDay[]>([]);
  const overviewBusy = ref(false);
  const calendarBusy = ref(false);
  const saving = ref(false);
  const error = ref("");
  const paymentConfigured = ref(false);
  const order = ref<OrderDetail>();
  const orderOpen = ref(false);
  const orderBusy = ref(false);
  const settingsDirty = computed(
    () =>
      !!settings.value &&
      JSON.stringify(settings.value) !== savedSettings.value,
  );
  const headers = () => ({ Authorization: `Bearer ${token}` });
  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    try {
      return await commerceApi<T>(path, {
        ...init,
        headers: { ...init.headers, ...headers() },
      });
    } catch (e) {
      if (e instanceof CommerceError && (e.status === 401 || e.status === 403))
        expired();
      throw e;
    }
  }
  function failed(e: unknown) {
    error.value = (e as Error).message;
    notify(error.value, error.value, "error");
  }
  async function loadOverview() {
    overviewBusy.value = true;
    try {
      overview.value = await request<Overview>("/manage/overview");
    } catch (e) {
      failed(e);
    } finally {
      overviewBusy.value = false;
    }
  }
  async function loadSetup() {
    const result = await request<{
      settings: Settings;
      products: Product[];
      payment_configured: boolean;
    }>("/manage/commerce");
    settings.value = result.settings;
    savedSettings.value = JSON.stringify(result.settings);
    products.value = result.products;
    paymentConfigured.value = result.payment_configured;
  }
  let calendarSequence = 0;
  async function loadCalendar(day = hamiltonDate()) {
    const seq = ++calendarSequence;
    calendarBusy.value = true;
    try {
      const result = await request<Overview>(`/manage/overview?day=${day}`);
      if (seq === calendarSequence) calendar.value = result.days;
    } catch (e) {
      failed(e);
    } finally {
      if (seq === calendarSequence) calendarBusy.value = false;
    }
  }
  async function initialize() {
    overviewBusy.value = true;
    error.value = "";
    try {
      await loadSetup();
      await loadOverview();
      calendar.value = overview.value?.days || [];
    } catch (e) {
      failed(e);
    } finally {
      overviewBusy.value = false;
    }
  }
  async function saveSettings() {
    if (!settings.value || saving.value) return false;
    saving.value = true;
    error.value = "";
    try {
      settings.value = await request<Settings>("/manage/schedule", {
        method: "PUT",
        body: JSON.stringify(settings.value),
      });
      savedSettings.value = JSON.stringify(settings.value);
      notify(copyText.message_88704412[0], copyText.message_88704412[1]);
      await loadOverview();
      await loadCalendar();
      return true;
    } catch (e) {
      failed(e);
      return false;
    } finally {
      saving.value = false;
    }
  }
  async function saveProduct(product: Product) {
    if (saving.value) return;
    saving.value = true;
    error.value = "";
    try {
      const result = await request<Product>(`/manage/products/${product.id}`, {
        method: "PUT",
        body: JSON.stringify(product),
      });
      if (products.value.some((p) => p.id === result.id))
        products.value = products.value.map((p) =>
          p.id === result.id ? result : p,
        );
      else products.value.push(result);
      notify(copyText.message_450b75db[0], copyText.message_450b75db[1]);
      await loadOverview();
      return result;
    } catch (e) {
      failed(e);
    } finally {
      saving.value = false;
    }
  }
  let orderSequence = 0;
  async function openOrder(id: string) {
    error.value = "";
    const seq = ++orderSequence;
    order.value = undefined;
    orderOpen.value = true;
    orderBusy.value = true;
    try {
      const result = await request<OrderDetail>(`/manage/orders/${id}`);
      if (seq === orderSequence) order.value = result;
    } catch (e) {
      failed(e);
    } finally {
      if (seq === orderSequence) orderBusy.value = false;
    }
  }
  const orderRevision = ref(0);
  async function saveOrder(completed: boolean) {
    if (!order.value || saving.value) return;
    saving.value = true;
    error.value = "";
    try {
      const result = await request<Order>(`/manage/orders/${order.value.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          completed,
          staff_note: order.value.staff_note || "",
          version: order.value.version,
        }),
      });
      order.value = { ...order.value, ...result };
      orderRevision.value++;
      notify(
        completed ? copyText.literal_9594c825 : copyText.literal_1888eeef,
        completed ? copyText.literal_ee776f3d : copyText.literal_00f955c3,
      );
      await loadOverview();
      await loadCalendar();
      order.value = await request<OrderDetail>(`/manage/orders/${result.id}`);
    } catch (e) {
      failed(e);
    } finally {
      saving.value = false;
    }
  }
  return {
    settings,
    settingsDirty,
    products,
    overview,
    calendar,
    overviewBusy,
    calendarBusy,
    paymentConfigured,
    saving,
    error,
    order,
    orderOpen,
    orderBusy,
    orderRevision,
    request,
    initialize,
    loadOverview,
    loadSetup,
    loadCalendar,
    saveSettings,
    saveProduct,
    openOrder,
    saveOrder,
    failed,
  };
}
export type Desk = ReturnType<typeof createDesk>;
export const deskKey: InjectionKey<Desk> = Symbol("studio-desk");
export function useDesk() {
  const desk = inject(deskKey);
  if (!desk) throw new Error("Studio desk provider missing");
  return desk;
}
export function localTime(timestamp: number) {
  return new Intl.DateTimeFormat(say(copyText.enca_9cd218), {
    timeZone: "America/Toronto",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(timestamp * 1000));
}
