<script setup lang="ts">
import { formatCopy } from "../../state";

import copyText from "../../content/components-admin-OverviewPanel.json";
import { say } from "../../state";

import { computed, ref, watch } from "vue";
import {
  PhArrowUpRight,
  PhArrowRight,
  PhCalendarDots,
  PhUsers,
  PhReceipt,
  PhWallet,
  PhCheck,
  PhClock,
} from "@phosphor-icons/vue";
import { useDesk, localTime, type DeskIntent } from "../../admin";
import { money, statusText } from "../../commerce";
import { tr } from "../../state";
const { overview, overviewBusy, settings, paymentConfigured, openOrder } =
  useDesk();
const emit = defineEmits<{ navigate: [view: string, intent?: DeskIntent] }>();
const setupExpanded = ref(false);
const setupComplete = computed(() =>
  readiness.value.every((item) => item.done),
);
const todayEntries = computed(() => overview.value?.days[0]?.entries || []);
const readiness = computed(() => [
  {
    done: paymentConfigured.value,
    label: say(copyText.connect_your_payment_account_a57502),
    detail: say(copyText.hupijiao_checkout_017d75),
    view: "checkout",
  },
  {
    done:
      !!settings.value?.capacity &&
      !!settings.value?.weekly.some((d) => d.enabled),
    label: say(copyText.set_opening_hours_and_seats_4ed29a),
    detail: say(copyText.weekly_hours_and_capacity_e99e57),
    view: "schedule",
  },
  {
    done: !!settings.value && settings.value.tax_mode !== "unconfirmed",
    label: say(copyText.confirm_prices_and_tax_0c4728),
    detail: say(copyText.show_the_final_amount_customers_pay_45b703),
    view: "checkout",
  },
]);
watch(
  setupComplete,
  (complete) => {
    setupExpanded.value = !complete;
  },
  { immediate: true },
);
</script>
<template>
  <section class="desk-overview">
    <header class="desk-welcome">
      <div>
        <p class="desk-eyebrow">
          {{ say(copyText.pindou_puppy_studio_desk_c23194) }}
        </p>
        <h1>{{ say(copyText.today_at_puppy_fa2258) }}</h1>
        <p>
          {{ say(copyText.todays_visits_new_orders_and_the_things_8c7be3) }}
        </p>
      </div>
      <button
        class="desk-button secondary"
        @click="emit('navigate', 'schedule', 'today-visits')"
      >
        <PhCalendarDots />{{ say(copyText.todays_schedule_51eea7) }}
      </button>
    </header>
    <div v-if="overview?.metrics.needs_review" class="desk-review-callout">
      <div>
        <strong>{{
          formatCopy(copyText.message_c5021d52, {
            v0: overview.metrics.needs_review,
          })
        }}</strong>
        <p>
          {{ say(copyText.review_payments_that_need_a_new_arrangement_eba4af) }}
        </p>
      </div>
      <button
        class="desk-button secondary"
        @click="emit('navigate', 'orders', 'needs-review')"
      >
        {{ say(copyText.review_orders_424b4e) }}<PhArrowRight />
      </button>
    </div>
    <div v-if="overview" class="desk-metrics">
      <button
        class="desk-metric"
        @click="emit('navigate', 'schedule', 'today-visits')"
      >
        <span
          ><PhUsers />{{ say(copyText.guests_booked_today_fd4fc5)
          }}<PhArrowUpRight /></span
        ><strong>{{ overview.metrics.guests_today }}</strong
        ><small>{{
          say(copyText.paid_and_confirmed_seats_05d4d4)
        }}</small></button
      ><button
        class="desk-metric"
        @click="emit('navigate', 'orders', 'today-orders')"
      >
        <span
          ><PhReceipt />{{ say(copyText.new_orders_today_39b386)
          }}<PhArrowUpRight /></span
        ><strong>{{ overview.metrics.orders_today }}</strong
        ><small>{{
          say(copyText.counted_by_hamilton_local_date_948b87)
        }}</small></button
      ><button
        class="desk-metric"
        @click="emit('navigate', 'orders', 'today-received')"
      >
        <span
          ><PhWallet />{{ say(copyText.payments_received_today_3c2886)
          }}<PhArrowUpRight /></span
        ><strong class="metric-money">{{
          money(overview.metrics.received_cny_fen, "CNY")
        }}</strong
        ><small>{{ say(copyText.cny_verified_payments_7ad2e0) }}</small></button
      ><button
        class="desk-metric"
        @click="emit('navigate', 'orders', 'awaiting')"
      >
        <span
          ><PhCalendarDots />{{ say(copyText.awaiting_visit_or_pickup_eeb3c4)
          }}<PhArrowUpRight /></span
        ><strong>{{ overview.metrics.awaiting_fulfillment }}</strong
        ><small>{{ say(copyText.paid_awaiting_visit_or_pickup_e82d5f) }}</small>
      </button>
    </div>
    <div v-else-if="overviewBusy" class="desk-metrics" aria-busy="true">
      <div v-for="n in 4" :key="n" class="desk-skeleton metric-skeleton" />
    </div>
    <div class="desk-overview-grid">
      <section class="desk-surface today-agenda">
        <header class="desk-section-heading">
          <div>
            <p class="desk-eyebrow">
              {{ say(copyText.today_at_the_studio_3ac0d6) }}
            </p>
            <h2>{{ say(copyText.who_is_coming_by_31fe9f) }}</h2>
          </div>
          <button
            class="desk-link"
            @click="emit('navigate', 'schedule', 'today-visits')"
          >
            {{ say(copyText.schedule_2cc1af) }}<PhArrowUpRight />
          </button>
        </header>
        <div v-if="todayEntries.length" class="agenda-list">
          <button
            v-for="(entry, i) in todayEntries"
            :key="entry.order_id + i"
            class="agenda-row"
            @click="openOrder(entry.order_id)"
          >
            <span class="agenda-hour"
              >{{ entry.start }}<small>{{ entry.end }}</small></span
            ><span class="agenda-person"
              ><strong>{{ entry.name }}</strong
              ><small
                >{{ entry.guests }}
                {{ say(copyText.guests_studio_visit_ea3db0) }}</small
              ></span
            ><span :class="['desk-status', entry.status]">{{
              entry.fulfillment === "completed"
                ? say(copyText.visited_f3f354)
                : entry.status === "paid"
                  ? say(copyText.confirmed_b1c92b)
                  : say(copyText.paying_575d26)
            }}</span
            ><PhArrowUpRight />
          </button>
        </div>
        <div v-else class="desk-empty agenda-empty">
          <PhCalendarDots :size="32" weight="light" />
          <h3>
            {{ say(copyText.no_visits_booked_for_today_66fab4) }}
          </h3>
          <p>
            {{
              say(copyText.confirmed_visits_and_seats_held_for_payment_1a367b)
            }}
          </p>
          <button
            class="desk-link"
            @click="emit('navigate', 'schedule', 'today-visits')"
          >
            {{ say(copyText.set_your_studio_hours_4b6048) }}<PhArrowRight />
          </button>
        </div>
      </section>
      <section class="desk-surface recent-orders">
        <header class="desk-section-heading">
          <h2>{{ say(copyText.recent_orders_1e2c3b) }}</h2>
          <button
            class="desk-link"
            @click="emit('navigate', 'orders', 'all-orders')"
          >
            {{ say(copyText.all_orders_442e68) }}<PhArrowUpRight />
          </button>
        </header>
        <div v-if="overview?.recent_orders.length" class="recent-order-list">
          <button
            v-for="order in overview.recent_orders"
            :key="order.id"
            class="recent-order-row"
            @click="openOrder(order.id)"
          >
            <span class="customer-monogram">{{
              order.customer?.name.slice(0, 1)
            }}</span
            ><span
              ><strong>{{ order.customer?.name }}</strong
              ><small>{{ localTime(order.created_at) }}</small></span
            ><span :class="['desk-status', order.status]">{{
              statusText(order.status)
            }}</span
            ><strong>{{ money(order.quote.cny_fen, "CNY") }}</strong
            ><PhArrowUpRight />
          </button>
        </div>
        <p v-else class="desk-inline-empty">
          {{ say(copyText.your_first_order_will_appear_here_when_61c238) }}
        </p>
      </section>
    </div>
    <section class="desk-surface desk-setup-summary">
      <button
        class="setup-summary-trigger"
        :aria-expanded="setupExpanded"
        @click="setupExpanded = !setupExpanded"
      >
        <span class="readiness-icon" :class="{ done: setupComplete }"
          ><PhCheck v-if="setupComplete" /><PhClock v-else /></span
        ><span
          ><strong>{{
            setupComplete
              ? say(copyText.studio_setup_complete_3dbd85)
              : say(copyText.a_few_things_before_opening_2124b3)
          }}</strong
          ><small>{{
            overview?.checkout_ready
              ? say(copyText.online_purchases_are_open_f76789)
              : say(copyText.online_purchases_are_not_open_yet_1dc20d)
          }}</small></span
        ><PhArrowRight :class="{ 'setup-arrow-open': setupExpanded }" />
      </button>
      <div v-if="setupExpanded" class="setup-checklist">
        <button
          v-for="item in readiness"
          :key="item.view + item.label"
          class="readiness-row"
          @click="emit('navigate', item.view)"
        >
          <span :class="['readiness-icon', { done: item.done }]"
            ><PhCheck v-if="item.done" /><PhClock v-else /></span
          ><span
            ><strong>{{ item.label }}</strong
            ><small>{{ item.detail }}</small></span
          ><PhArrowUpRight />
        </button>
      </div>
    </section>
  </section>
</template>
