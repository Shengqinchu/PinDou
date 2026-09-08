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
  read("puppy-studio-locale") === "en" ? "en" : "zh",
);
export const tr = (zh: string, en: string) => (locale.value === "zh" ? zh : en);
watch(
  locale,
  (value) => {
    write("puppy-studio-locale", value);
    document.documentElement.lang = value === "zh" ? "zh-CN" : "en-CA";
    document.title = tr(
      "小狗拼豆铺 · 汉密尔顿拼豆手作体验",
      "Pindo Puppy · A little creative studio in Hamilton",
    );
  },
  { immediate: true },
);

export const media = (name: string) =>
  `${import.meta.env.BASE_URL}studio-media/${name}.jpg`;
export const socialUrl =
  "https://www.xiaohongshu.com/user/profile/65f8375c000000000b00c921";
export const noteUrl = "https://xhslink.cn/o/8HFIo1pstmk";
export const mapsUrl =
  "https://www.google.com/maps/search/?api=1&query=8+Hughson+St+N+Hamilton+ON";
export const wechat = "xiaogoushuangji";

export const products = [
  {
    id: "starter",
    category: "tools",
    zh: "给第一幅作品的工具",
    en: "Your first little toolkit",
    detailZh: "告诉我们你想做什么，一起选底板、镊子和需要的工具。",
    detailEn:
      "Tell us what you would like to make. We will help you choose boards, tweezers and tools.",
    image: "studio-07",
    price: null,
  },
  {
    id: "beads",
    category: "beads",
    zh: "刚好缺的那一抹颜色",
    en: "A little more colour",
    detailZh: "补齐下一幅图纸需要的豆子。请在备注里留下色号、品牌或图纸。",
    detailEn:
      "Top up for your next pattern. Include your colour codes, bead brand or pattern in the notes.",
    image: "studio-06",
    price: null,
  },
  {
    id: "findings",
    category: "tools",
    zh: "让拼豆变成随身小物",
    en: "The finishing touches",
    detailZh: "挂绳、钥匙扣、冰箱贴配件等。款式与数量由店主确认。",
    detailEn:
      "Straps, key rings and magnet fittings. We will confirm styles and quantities with you.",
    image: "studio-11",
    price: null,
  },
  {
    id: "custom",
    category: "finished",
    zh: "一份专属的手作心意",
    en: "Something made for you",
    detailZh:
      "把你的想法告诉我们，聊聊定制的尺寸、配色和交付时间。图片为作品展示。",
    detailEn:
      "Share an idea for a custom piece. We will discuss size, colours and timing. Photo shows example work.",
    image: "journal-05",
    price: null,
  },
] as const;

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
        tr(
          "提交次数较多，请稍后再试，或通过微信联系店主。",
          "Too many requests. Please try again later or contact us on WeChat.",
        ),
      );
    if (response.status === 422)
      throw new Error(
        tr(
          "请检查日期、时间和联系信息，再试一次。",
          "Please check the date, time and contact details, then try again.",
        ),
      );
    if (response.status === 401 || response.status === 403)
      throw new Error(
        tr(
          "登录已过期或账号无管理权限，请重新登录。",
          "Please sign in with an administrator account.",
        ),
      );
    throw new Error(
      tr(
        "暂时未能提交，请重试或通过微信联系店主。",
        "We could not complete that request. Please try again or contact us on WeChat.",
      ),
    );
  }
  return data as T;
}

export const gallery = [
  {
    image: "studio-02",
    zh: "阳光、白桌，和一个属于你的座位",
    en: "Daylight, a white desk, a place for you",
  },
  {
    image: "studio-08",
    zh: "让可爱挂在每一个角落",
    en: "Little things, everywhere",
  },
  {
    image: "journal-05",
    zh: "一颗一颗，拼出落日的颜色",
    en: "A sunset, one bead at a time",
  },
  {
    image: "studio-04",
    zh: "今天也想在这里待久一点",
    en: "Stay a little longer",
  },
  {
    image: "studio-11",
    zh: "做冰箱贴，也做小挂件",
    en: "Magnets, charms, and possibilities",
  },
  { image: "journal-13", zh: "用手作装饰日常", en: "Make yourself at home" },
];
