<script setup lang="ts">
import { contentModule } from "../content-store";
const copyText = contentModule("components-CommerceManager", copyTextDefault);

import BrandMotif from "./BrandMotif.vue";

import copyTextDefault from "../content/components-CommerceManager.json";
import { say } from "../state";

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
import { createDesk, deskKey, type DeskIntent } from "../admin";
import { hamiltonDate, locale, tr } from "../state";
import OverviewPanel from "./admin/OverviewPanel.vue";
import OrdersPanel from "./admin/OrdersPanel.vue";
import SchedulePanel from "./admin/SchedulePanel.vue";
import ProductsPanel from "./admin/ProductsPanel.vue";
import CheckoutPanel from "./admin/CheckoutPanel.vue";
import ActivityPanel from "./admin/ActivityPanel.vue";
import OrderDrawer from "./admin/OrderDrawer.vue";
import ContentEditor from "./admin/ContentEditor.vue";
import JournalEditor from "./admin/JournalEditor.vue";
import ReservationNotifications from "./admin/ReservationNotifications.vue";
import ReservationsPanel from "./admin/ReservationsPanel.vue";
const props = defineProps<{ token: string }>();
const emit = defineEmits<{ logout: []; expired: [] }>();
const desk = createDesk(props.token, () => emit("expired"));
provide(deskKey, desk);
const route = useRoute();
const router = useRouter();
const mobileMenu = ref(false);
const reservationList = ref<InstanceType<typeof ReservationsPanel>>();
const reservationCalendar = ref<InstanceType<typeof ReservationsPanel>>();
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
  {id:"content",zh:copyText.editor_content[0],en:copyText.editor_content[1],icon:PhSquaresFour},
  {id:"journal-editor",zh:copyText.editor_journal[0],en:copyText.editor_journal[1],icon:PhArchive},
  {
    id: "reservations",
    zh: copyText.nav_c557d2fc[0],
    en: copyText.nav_c557d2fc[1],
    icon: PhReceipt,
  },
  {
    id: "reservation-calendar",
    zh: copyText.nav_b72b465f[0],
    en: copyText.nav_b72b465f[1],
    icon: PhCalendarDots,
  },
  /* V4: commerce navigation is retired; records and panels remain available in source.
  {
    id: "overview",
    zh: copyText.nav_2acebe6d[0],
    en: copyText.nav_2acebe6d[1],
    icon: PhSquaresFour,
  },
  {
    id: "orders",
    zh: copyText.nav_f88bbd41[0],
    en: copyText.nav_f88bbd41[1],
    icon: PhReceipt,
  },
  {
    id: "schedule",
    zh: copyText.nav_fd3e0b4a[0],
    en: copyText.nav_fd3e0b4a[1],
    icon: PhCalendarDots,
  },
  {
    id: "products",
    zh: copyText.nav_f526fd3f[0],
    en: copyText.nav_f526fd3f[1],
    icon: PhPackage,
  },
  {
    id: "checkout",
    zh: copyText.nav_d8f7beee[0],
    en: copyText.nav_d8f7beee[1],
    icon: PhWallet,
  },
  {
    id: "activity",
    zh: copyText.nav_ced4db80[0],
    en: copyText.nav_ced4db80[1],
    icon: PhClockCounterClockwise,
  },
  {
    id: "legacy",
    zh: copyText.nav_096839b5[0],
    en: copyText.nav_096839b5[1],
    icon: PhArchive,
  },
  */
]);
const view = computed(() =>
  navigation.value.some((n) => n.id === route.query.view)
    ? String(route.query.view)
    : "reservations",
);
const selectedIndex = computed(() =>
  navigation.value.findIndex((n) => n.id === view.value),
);
const selected = computed(() => navigation.value[selectedIndex.value]);
const scrolls = new Map<string, number>();
async function navigate(id: string, intent?: DeskIntent) {
  scrolls.set(view.value, pageScrollY());
  // Choosing the current view must also release the mobile menu's focus/scroll lock.
  mobileMenu.value = false;
  await router.replace({
    path: "/manage",
    query: {
      ...(id === "reservations" ? {} : { view: id }),
      ...(intent
        ? { scope: intent, day: desk.overview.value?.date || hamiltonDate() }
        : {}),
    },
  });
  await nextTick();
  scrollTo({ top: intent ? 0 : scrolls.get(id) || 0, behavior: "instant" });
}
watch(view, async () => {
  mobileMenu.value = false;
  desk.error.value = "";
  await nextTick();
  arrival?.progress(1).kill();
  if (content.value) arrival = arrive(content.value, { stationary: true });
});
onMounted(desk.loadSetup);
function refreshCurrent() {
  if (view.value === "reservations") reservationList.value?.refresh();
  else if (view.value === "reservation-calendar")
    reservationCalendar.value?.refresh();
  else desk.loadOverview();
}
const readableDate = computed(() =>
  new Intl.DateTimeFormat(say(copyText.enca_9cd218), {
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
      :aria-label="say(copyText.studio_desk_navigation_28a348)"
      @keydown="trapMenu"
      @keydown.esc.stop="mobileMenu = false"
    >
      <RouterLink to="/" class="desk-brand"
        ><BrandMotif /><span
          >{{ say(copyText.pindo_puppy_08aa61)
          }}<small>{{
            say(copyText.your_studio_in_good_hands_272ef4)
          }}</small></span
        ></RouterLink
      ><button
        class="desk-mobile-close desk-icon-button"
        :aria-label="say(copyText.close_desk_navigation_f2d087)"
        @click="mobileMenu = false"
      >
        <PhX />
      </button>
      <p class="sidebar-section-label">
        {{ say(copyText.your_workspace_2c12d8) }}
      </p>
      <nav
        class="desk-navigation"
        :aria-label="say(copyText.studio_desk_navigation_e9ec2c)"
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
          <span class="state-dot live" /><span>{{
            say(copyText.visits_confirmed_by_the_host_471d39)
          }}</span>
        </div>
        <RouterLink to="/" class="sidebar-store-link"
          >{{ say(copyText.view_your_website_60949c)
          }}<PhArrowUpRight /></RouterLink
        ><button class="sidebar-signout" @click="emit('logout')">
          <PhSignOut />{{ say(copyText.sign_out_e59c73) }}</button
        ><small class="desk-version"
          >{{ say(copyText.studio_desk_4be24d) }} · 0.4</small
        >
      </div>
    </aside>
    <Transition name="menu-shade"
      ><button
        v-if="mobileMenu"
        class="desk-mobile-shade"
        :aria-label="say(copyText.close_navigation_9b4ac8)"
        @click="mobileMenu = false"
    /></Transition>
    <div class="desk-main" :inert="isMobile && mobileMenu">
      <header class="desk-topbar">
        <div class="desk-breadcrumb">
          <button
            class="desk-menu-button desk-icon-button"
            :aria-label="say(copyText.open_desk_navigation_2319be)"
            :aria-expanded="mobileMenu"
            @click="mobileMenu = !mobileMenu"
          >
            <PhList :size="22" /></button
          ><span>{{ say(copyText.studio_desk_4be24d) }}</span
          ><PhCaretRight :size="12" /><strong>{{
            tr(selected.zh, selected.en)
          }}</strong>
        </div>
        <div class="desk-top-actions">
          <span class="desk-current-date">{{ readableDate }}</span
          ><button
            class="desk-icon-button"
            :disabled="desk.overviewBusy.value"
            :aria-label="say(copyText.refresh_overview_07412b)"
            @click="refreshCurrent"
          >
            <PhArrowClockwise
              :class="{ spinning: desk.overviewBusy.value }"
            /></button
          ><button
            class="desk-language"
            :aria-label="say(copyText.switch_to_chinese_6c04c2)"
            @click="locale = locale === 'zh' ? 'en' : 'zh'"
          >
            {{
              locale === "zh"
                ? copyText.literal_348ea84c
                : copyText.literal_72726d88
            }}</button
          ><span class="desk-avatar">{{ say(copyText.p_18d98d) }}</span>
        </div>
      </header>
      <div ref="content" class="desk-content">
        <ReservationNotifications />
        <KeepAlive><ContentEditor v-if="view === 'content'" :active="view === 'content'" /></KeepAlive>
        <KeepAlive><JournalEditor v-if="view === 'journal-editor'" :active="view === 'journal-editor'" /></KeepAlive>
        <p
          v-if="
            !['reservations', 'reservation-calendar', 'legacy', 'content', 'journal-editor'].includes(view)
          "
          class="reservation-commerce-note"
        >
          {{ say(copyText.the_shop_is_paused_commerce_records_remain_b78ead) }}
        </p>
        <ReservationsPanel
          ref="reservationList"
          v-show="view === 'reservations'"
          :active="view === 'reservations'"
        />
        <ReservationsPanel
          ref="reservationCalendar"
          v-show="view === 'reservation-calendar'"
          :active="view === 'reservation-calendar'"
          calendar
        />
        <p
          v-if="desk.error.value && !desk.settings.value"
          class="desk-error"
          role="alert"
        >
          {{ desk.error.value
          }}<button class="desk-link" @click="desk.initialize">
            {{ say(copyText.try_again_014aa4) }}
          </button>
        </p>
        <OverviewPanel
          v-if="view === 'overview'"
          @navigate="navigate"
        /><template v-if="desk.settings.value && ['orders','schedule','products','checkout','activity','legacy'].includes(view)"
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
                  {{ say(copyText.earlier_arrangements_902f91) }}
                </p>
                <h1>{{ say(copyText.earlier_requests_620a53) }}</h1>
                <p>
                  {{
                    say(
                      copyText.visit_and_pickup_inquiries_received_before_online_514cd1,
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
