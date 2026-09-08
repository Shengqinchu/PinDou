import contactDefaults from "./content/contact-fields.json";
import { contentModule } from "./content-store";
const copyText = contentModule("state", copyTextDefault);
import { contentPhotos, asset } from "./content-store";
import profileDefault from "./content/studio-profile.json";
import contentGallery from "./content/data-state-gallery.json";
import contentProducts from "./content/data-state-products.json";
import copyTextDefault from "./content/state.json";
import { computed, ref, watch } from "vue";

export type Locale = "zh" | "en";
function read(key: string) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* Browsing still works without storage. */
  }
}
export const locale = ref<Locale>(
  (new URLSearchParams(location.search).get("preview-locale") || read("puppy-studio-locale")) === "en" ? "en" : "zh",
);
export const tr = (zh: string, en: string) => (locale.value === "zh" ? zh : en);
export function say(pair: readonly string[]) {
  return tr(pair[0], pair[1]);
}
export function formatCopy(
  pair: readonly string[],
  values: Record<string, unknown>,
) {
  return say(pair).replace(/\{(v\d+)\}/g, (_, key) => String(values[key]));
}
watch(
  locale,
  (value) => {
    if (!new URLSearchParams(location.search).has("content-preview")) write("puppy-studio-locale", value);
    document.documentElement.lang = value === "zh" ? "zh-CN" : "en-CA";
    document.title = say(
      copyText.pindo_puppy_a_little_creative_studio_in_d8b24c,
    );
  },
  { immediate: true },
);

export const media = (name: string) =>
  asset(name).src;
export const contacts = contentModule("contact-fields",contactDefaults);
export const socialUrl = computed(() => say(contacts.social_url));
export const noteUrl = computed(() => say(contacts.original_post));
export const mapsUrl = computed(() => "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(say(contacts.address)));
export const wechat = computed(() => say(contacts.wechat));
export const phone = computed(() => say(contacts.phone));
export const phoneHref = computed(() => say(contacts.phone_href));

export const products = contentProducts;

const productIds = new Set(products.map((p) => p.id as string));
function loadCart(): Record<string, number> {
  try {
    const saved = JSON.parse(read("puppy-studio-cart") || "{}");
    return Object.fromEntries(
      Object.entries(saved).filter(
        ([id, qty]) =>
          productIds.has(id) &&
          Number.isInteger(qty) &&
          Number(qty) > 0 &&
          Number(qty) <= 20,
      ),
    ) as Record<string, number>;
  } catch {
    return {};
  }
}
export const cart = ref<Record<string, number>>(loadCart());
export const cartCount = computed(() =>
  Object.values(cart.value).reduce((sum, n) => sum + n, 0),
);
watch(cart, (value) => write("puppy-studio-cart", JSON.stringify(value)), {
  deep: true,
});
export function changeQuantity(id: string, delta: number) {
  if (!productIds.has(id)) return;
  const next = Math.min(20, Math.max(0, (cart.value[id] || 0) + delta));
  if (next) cart.value[id] = next;
  else delete cart.value[id];
}

export function hamiltonDate(): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Toronto",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const value = (key: string) => parts.find((part) => part.type === key)?.value;
  return `${value("year")}-${value("month")}-${value("day")}`;
}
export function plusDays(day: string, days: number): string {
  const dt = new Date(`${day}T12:00:00Z`);
  dt.setUTCDate(dt.getUTCDate() + days);
  return dt.toISOString().slice(0, 10);
}
export function prettyDate(day: string) {
  return new Intl.DateTimeFormat(locale.value === "zh" ? "zh-CN" : "en-CA", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${day}T12:00:00Z`));
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/studio-api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 429)
      throw new Error(
        say(copyText.too_many_requests_please_try_again_later_7d3a95),
      );
    if (response.status === 422)
      throw new Error(
        say(copyText.please_check_the_date_time_and_contact_baa037),
      );
    if (response.status === 401 || response.status === 403)
      throw new Error(
        say(copyText.please_sign_in_with_an_administrator_account_801902),
      );
    throw new Error(
      say(copyText.we_could_not_complete_that_request_please_967586),
    );
  }
  return data as T;
}

export const gallery = contentPhotos("gallery-labels", contentGallery);
