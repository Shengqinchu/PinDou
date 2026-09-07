<script setup lang="ts">
import { computed } from "vue";
import {
  PhArrowUpRight,
  PhArrowRight,
  PhCalendarDots,
  PhUsers,
  PhReceipt,
  PhWallet,
  PhFlower,
  PhCheck,
  PhClock,
} from "@phosphor-icons/vue";
import { useDesk, localTime } from "../../admin";
import { money, statusText } from "../../commerce";
import { media, tr } from "../../state";
const { overview, overviewBusy, settings, paymentConfigured, openOrder } =
  useDesk();
const emit = defineEmits<{ navigate: [view: string] }>();
const todayEntries = computed(() => overview.value?.days[0]?.entries || []);
const readiness = computed(() => [
  {
    done: paymentConfigured.value,
    label: tr("连接收款账户", "Connect your payment account"),
    detail: tr("虎皮椒收银台", "Hupijiao checkout"),
    view: "checkout",
  },
  {
    done:
      !!settings.value?.capacity &&
      !!settings.value?.weekly.some((d) => d.enabled),
    label: tr("安排营业时间和座位", "Set opening hours and seats"),
    detail: tr("每周排班和接待人数", "Weekly hours and capacity"),
    view: "schedule",
  },
  {
    done: !!settings.value && settings.value.tax_mode !== "unconfirmed",
    label: tr("确认售价与税费", "Confirm prices and tax"),
    detail: tr("让客人看到最终实付金额", "Show the final amount customers pay"),
    view: "checkout",
  },
]);
</script>
<template>
  <section class="desk-overview">
    <div class="desk-welcome">
      <div>
        <p class="desk-eyebrow">
          {{ tr("小狗拼豆铺 · 店主工作台", "PINDOU PUPPY · STUDIO DESK") }}
        </p>
        <h1>
          {{ tr("把店里的小事，", "A little studio,") }}<br /><em>{{
            tr("安排得刚刚好。", "in good hands.")
          }}</em>
        </h1>
        <p>
          {{
            tr(
              "看看今天谁要来，再给接下来的好时光留好位置。",
              "See who is coming today, and make room for the lovely days ahead.",
            )
          }}
        </p>
      </div>
      <div class="desk-welcome-photo">
        <img
          :src="media('studio-04')"
          width="1080"
          height="1440"
          :alt="tr('小狗拼豆铺的窗边座位', 'A sunlit seat at PinDou Puppy')"
        /><span
          ><PhFlower />{{
            tr("慢慢做，好好经营。", "Made slowly. Looked after well.")
          }}</span
        >
      </div>
    </div>
    <div v-if="overview" class="desk-metrics">
      <button class="desk-metric" @click="emit('navigate', 'schedule')">
        <span
          ><PhUsers />{{ tr("今日到店人数", "Guests booked today")
          }}<PhArrowUpRight /></span
        ><strong>{{ overview.metrics.guests_today }}</strong
        ><small>{{
          tr("已付款确认的座位", "Paid and confirmed seats")
        }}</small></button
      ><button class="desk-metric" @click="emit('navigate', 'orders')">
        <span
          ><PhReceipt />{{ tr("今日新订单", "New orders today")
          }}<PhArrowUpRight /></span
        ><strong>{{ overview.metrics.orders_today }}</strong
        ><small>{{
          tr("按 Hamilton 当地日期统计", "Counted by Hamilton local date")
        }}</small></button
      ><button class="desk-metric" @click="emit('navigate', 'orders')">
        <span
          ><PhWallet />{{ tr("今日已收款", "Payments received today")
          }}<PhArrowUpRight /></span
        ><strong class="metric-money">{{
          money(overview.metrics.received_cny_fen, "CNY")
        }}</strong
        ><small>{{
          tr("人民币 · 已核实到账", "CNY · Verified payments")
        }}</small></button
      ><button class="desk-metric" @click="emit('navigate', 'orders')">
        <span
          ><PhCalendarDots />{{ tr("待到店／自提", "Awaiting visit or pickup")
          }}<PhArrowUpRight /></span
        ><strong>{{ overview.metrics.awaiting_fulfillment }}</strong
        ><small>{{
          overview.metrics.needs_review
            ? tr(
                `${overview.metrics.needs_review} 笔订单需要跟进`,
                `${overview.metrics.needs_review} orders need follow-up`,
              )
            : tr("所有已付款待完成订单", "All paid orders awaiting fulfillment")
        }}</small>
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
              {{ tr("今日安排", "TODAY AT THE STUDIO") }}
            </p>
            <h2>{{ tr("今天，谁来玩？", "Who is coming by?") }}</h2>
          </div>
          <button class="desk-link" @click="emit('navigate', 'schedule')">
            {{ tr("查看排班", "Schedule") }}<PhArrowUpRight />
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
                {{ tr("人 · 到店体验", "guests · Studio visit") }}</small
              ></span
            ><span :class="['desk-status', entry.status]">{{
              entry.fulfillment === "completed"
                ? tr("已到店", "Visited")
                : entry.status === "paid"
                  ? tr("已确认", "Confirmed")
                  : tr("付款中", "Paying")
            }}</span
            ><PhArrowUpRight />
          </button>
        </div>
        <div v-else class="desk-empty agenda-empty">
          <PhCalendarDots :size="32" weight="light" />
          <h3>
            {{
              tr(
                "今天的座位，等一份期待。",
                "A little room for something lovely.",
              )
            }}
          </h3>
          <p>
            {{
              tr(
                "确认后的到店安排会出现在这里。",
                "Confirmed visits will appear here.",
              )
            }}
          </p>
          <button class="desk-link" @click="emit('navigate', 'schedule')">
            {{ tr("去安排营业时间", "Set your studio hours") }}<PhArrowRight />
          </button>
        </div>
      </section>
      <section class="desk-surface launch-panel">
        <header class="desk-section-heading">
          <div>
            <p class="desk-eyebrow">{{ tr("开店准备", "READY TO WELCOME") }}</p>
            <h2>
              {{
                overview?.checkout_ready
                  ? tr("小店，准备好了。", "Your studio is ready.")
                  : tr("让小店准备好。", "A few things before opening.")
              }}
            </h2>
          </div>
        </header>
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
        <div class="launch-note">
          <span
            :class="['state-dot', { live: overview?.checkout_ready }]"
          /><span>{{
            overview?.checkout_ready
              ? tr("网上购买已开放", "Online purchases are open")
              : tr("网上购买尚未开放", "Online purchases are not open yet")
          }}</span>
        </div>
      </section>
    </div>
    <section class="desk-surface recent-orders">
      <header class="desk-section-heading">
        <h2>{{ tr("最近的订单", "Recent orders") }}</h2>
        <button class="desk-link" @click="emit('navigate', 'orders')">
          {{ tr("全部订单", "All orders") }}<PhArrowUpRight />
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
        {{
          tr(
            "收到第一笔订单后，就会在这里看到它。",
            "Your first order will appear here when it arrives.",
          )
        }}
      </p>
    </section>
  </section>
</template>
