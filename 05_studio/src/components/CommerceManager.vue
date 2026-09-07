<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  provide,
  ref,
  watch,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  PhFlower,
  PhSquaresFour,
  PhReceipt,
  PhCalendarDots,
  PhPackage,
  PhWallet,
  PhClockCounterClockwise,
  PhArchive,
  PhArrowUpRight,
  PhSignOut,
  PhList,
  PhX,
  PhCaretRight,
  PhArrowClockwise,
} from "@phosphor-icons/vue";
import { gsap } from "gsap";
import { arrive } from "../motion";
import { lockPageScroll, pageScrollY } from "../browser";
import { createDesk, deskKey } from "../admin";
import { hamiltonDate, locale, tr } from "../state";
import OverviewPanel from "./admin/OverviewPanel.vue";
import OrdersPanel from "./admin/OrdersPanel.vue";
import SchedulePanel from "./admin/SchedulePanel.vue";
import ProductsPanel from "./admin/ProductsPanel.vue";
import CheckoutPanel from "./admin/CheckoutPanel.vue";
import ActivityPanel from "./admin/ActivityPanel.vue";
import OrderDrawer from "./admin/OrderDrawer.vue";
const props = defineProps<{ token: string }>();
const emit = defineEmits<{ logout: []; expired: [] }>();
const desk = createDesk(props.token, () => emit("expired"));
provide(deskKey, desk);
const route = useRoute();
const router = useRouter();
const mobileMenu = ref(false);
const mobileMedia = matchMedia("(max-width: 900px)");
const isMobile = ref(mobileMedia.matches);
const sidebar = ref<HTMLElement>();
let unlockMenu: (() => void) | undefined;
let arrival: gsap.core.Tween | undefined;
const content = ref<HTMLElement>();
function resizeMenu(event: MediaQueryListEvent) {
  isMobile.value = event.matches;
  mobileMenu.value = false;
}
mobileMedia.addEventListener("change", resizeMenu);
watch(mobileMenu, async (value) => {
  if (value && isMobile.value) {
    unlockMenu ||= lockPageScroll();
  } else {
    unlockMenu?.();
    unlockMenu = undefined;
  }
  await nextTick();
  if (value)
    sidebar.value
      ?.querySelector<HTMLElement>(".desk-navigation > button.active")
      ?.focus();
  else if (isMobile.value)
    document.querySelector<HTMLElement>(".desk-menu-button")?.focus();
});
function trapMenu(event: KeyboardEvent) {
  if (
    !isMobile.value ||
    !mobileMenu.value ||
    event.key !== "Tab" ||
    !sidebar.value
  )
    return;
  const focusable = [
    ...sidebar.value.querySelectorAll<HTMLElement>(
      "a[href],button:not(:disabled)",
    ),
  ].filter((e) => e.offsetParent !== null);
  const first = focusable[0],
    last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last?.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first?.focus();
  }
}
onBeforeUnmount(() => {
  mobileMedia.removeEventListener("change", resizeMenu);
  unlockMenu?.();
  arrival?.kill();
});
const navigation = computed(() => [
  { id: "overview", zh: "今日概览", en: "Overview", icon: PhSquaresFour },
  { id: "orders", zh: "订单管理", en: "Orders", icon: PhReceipt },
  { id: "schedule", zh: "到店排班", en: "Schedule", icon: PhCalendarDots },
  { id: "products", zh: "商品与体验", en: "Products", icon: PhPackage },
  { id: "checkout", zh: "收款设置", en: "Checkout", icon: PhWallet },
  {
    id: "activity",
    zh: "操作记录",
    en: "Activity",
    icon: PhClockCounterClockwise,
  },
  { id: "legacy", zh: "历史询单", en: "Earlier requests", icon: PhArchive },
]);
const view = computed(() =>
  navigation.value.some((n) => n.id === route.query.view)
    ? String(route.query.view)
    : "overview",
);
const selectedIndex = computed(() =>
  navigation.value.findIndex((n) => n.id === view.value),
);
const selected = computed(() => navigation.value[selectedIndex.value]);
const scrolls = new Map<string, number>();
async function navigate(id: string) {
  scrolls.set(view.value, pageScrollY());
  await router.replace({
    path: "/manage",
    query: id === "overview" ? {} : { view: id },
  });
  await nextTick();
  scrollTo({ top: scrolls.get(id) || 0, behavior: "instant" });
}
watch(view, async () => {
  mobileMenu.value = false;
  desk.error.value = "";
  await nextTick();
  arrival?.progress(1).kill();
  if (content.value) arrival = arrive(content.value);
});
onMounted(desk.initialize);
const readableDate = computed(() =>
  new Intl.DateTimeFormat(tr("zh-CN", "en-CA"), {
    month: "long",
    day: "numeric",
    weekday: "short",
    timeZone: "UTC",
  }).format(
    new Date((desk.overview.value?.date || hamiltonDate()) + "T12:00:00Z"),
  ),
);
</script>
<template>
  <div class="studio-desk">
    <aside
      ref="sidebar"
      :class="['desk-sidebar', { expanded: mobileMenu }]"
      :inert="isMobile && !mobileMenu"
      :aria-hidden="isMobile && !mobileMenu ? true : undefined"
      :role="isMobile && mobileMenu ? 'dialog' : undefined"
      :aria-modal="isMobile && mobileMenu ? true : undefined"
      :aria-label="tr('店主工作台导航', 'Studio desk navigation')"
      @keydown="trapMenu"
      @keydown.esc.stop="mobileMenu = false"
    >
      <RouterLink to="/" class="desk-brand"
        ><PhFlower :size="29" weight="light" /><span
          >pindou puppy<small>{{
            tr("小狗拼豆铺 · 店主工作台", "YOUR STUDIO, IN GOOD HANDS")
          }}</small></span
        ></RouterLink
      ><button
        class="desk-mobile-close desk-icon-button"
        :aria-label="tr('关闭后台导航', 'Close desk navigation')"
        @click="mobileMenu = false"
      >
        <PhX />
      </button>
      <p class="sidebar-section-label">
        {{ tr("我的工作室", "YOUR WORKSPACE") }}
      </p>
      <nav
        class="desk-navigation"
        :aria-label="tr('后台导航', 'Studio desk navigation')"
        :style="{ '--nav-index': selectedIndex }"
      >
        <span class="desk-nav-indicator" aria-hidden="true" /><button
          v-for="nav in navigation"
          :key="nav.id"
          :class="{ active: view === nav.id }"
          :aria-current="view === nav.id ? 'page' : undefined"
          @click="navigate(nav.id)"
        >
          <component
            :is="nav.icon"
            :size="20"
            :weight="view === nav.id ? 'regular' : 'light'"
          /><span>{{ tr(nav.zh, nav.en) }}</span
          ><span
            v-if="
              nav.id === 'orders' && desk.overview.value?.metrics.needs_review
            "
            class="nav-count"
            >{{ desk.overview.value.metrics.needs_review }}</span
          >
        </button>
      </nav>
      <div class="sidebar-bottom">
        <div class="sidebar-shop-state">
          <span
            :class="[
              'state-dot',
              { live: desk.overview.value?.checkout_ready },
            ]"
          /><span>{{
            desk.overview.value?.checkout_ready
              ? tr("网上购买已开放", "Shop is open")
              : tr("小店准备中", "Getting ready to open")
          }}</span>
        </div>
        <RouterLink to="/" class="sidebar-store-link"
          >{{ tr("看看我的网站", "View your website")
          }}<PhArrowUpRight /></RouterLink
        ><button class="sidebar-signout" @click="emit('logout')">
          <PhSignOut />{{ tr("退出登录", "Sign out") }}</button
        ><small class="desk-version">Studio desk · 0.3</small>
      </div>
    </aside>
    <Transition name="menu-shade"
      ><button
        v-if="mobileMenu"
        class="desk-mobile-shade"
        :aria-label="tr('关闭导航', 'Close navigation')"
        @click="mobileMenu = false"
    /></Transition>
    <div class="desk-main" :inert="isMobile && mobileMenu">
      <header class="desk-topbar">
        <div class="desk-breadcrumb">
          <button
            class="desk-menu-button desk-icon-button"
            :aria-label="tr('打开后台导航', 'Open desk navigation')"
            :aria-expanded="mobileMenu"
            @click="mobileMenu = !mobileMenu"
          >
            <PhList :size="22" /></button
          ><span>{{ tr("店主工作台", "Studio desk") }}</span
          ><PhCaretRight :size="12" /><strong>{{
            tr(selected.zh, selected.en)
          }}</strong>
        </div>
        <div class="desk-top-actions">
          <span class="desk-current-date">{{ readableDate }}</span
          ><button
            class="desk-icon-button"
            :disabled="desk.overviewBusy.value"
            :aria-label="tr('刷新概览', 'Refresh overview')"
            @click="desk.loadOverview"
          >
            <PhArrowClockwise
              :class="{ spinning: desk.overviewBusy.value }"
            /></button
          ><button
            class="desk-language"
            :aria-label="tr('Switch to English', '切换为中文')"
            @click="locale = locale === 'zh' ? 'en' : 'zh'"
          >
            {{ locale === "zh" ? "EN" : "中文" }}</button
          ><span class="desk-avatar">{{ tr("双吉", "P") }}</span>
        </div>
      </header>
      <div ref="content" class="desk-content">
        <p
          v-if="desk.error.value && !desk.settings.value"
          class="desk-error"
          role="alert"
        >
          {{ desk.error.value
          }}<button class="desk-link" @click="desk.initialize">
            {{ tr("重新加载", "Try again") }}
          </button>
        </p>
        <OverviewPanel
          v-show="view === 'overview'"
          @navigate="navigate"
        /><template v-if="desk.settings.value"
          ><OrdersPanel v-show="view === 'orders'" /><SchedulePanel
            v-show="view === 'schedule'" /><ProductsPanel
            v-show="view === 'products'" /><CheckoutPanel
            v-show="view === 'checkout'" /><ActivityPanel
            v-show="view === 'activity'"
            :active="view === 'activity'" />
          <section v-show="view === 'legacy'" class="legacy-workspace">
            <header class="desk-page-heading">
              <div>
                <p class="desk-eyebrow">
                  {{ tr("保留从前的安排", "EARLIER ARRANGEMENTS") }}
                </p>
                <h1>{{ tr("历史预约与询单", "Earlier requests") }}</h1>
                <p>
                  {{
                    tr(
                      "上线购物车之前留下的预约和自提意向。",
                      "Visit and pickup inquiries received before online checkout.",
                    )
                  }}
                </p>
              </div>
            </header>
            <div class="desk-surface legacy-surface">
              <slot name="legacy" />
            </div></section
        ></template>
      </div>
    </div>
    <OrderDrawer />
  </div>
</template>
