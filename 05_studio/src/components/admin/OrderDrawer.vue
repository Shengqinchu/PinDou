<script setup lang="ts">
import {
  PhCheck,
  PhClock,
  PhCopy,
  PhArrowCounterClockwise,
} from "@phosphor-icons/vue";
import SlideOver from "../SlideOver.vue";
import { useDesk, localTime } from "../../admin";
import { money, statusText } from "../../commerce";
import { locale, prettyDate, tr } from "../../state";
import { eventLabel, notify } from "../../ui";
const { order, orderOpen, orderBusy, saving, error, saveOrder } = useDesk();
async function copy() {
  if (!order.value) return;
  try {
    await navigator.clipboard.writeText(order.value.id);
    notify("订单号已复制", "Order number copied");
  } catch {
    notify("请选中订单号复制", "Select the order number to copy it", "error");
  }
}
</script>
<template>
  <SlideOver
    v-model="orderOpen"
    :title="tr('订单详情', 'Order details')"
    :subtitle="order?.customer?.name"
    :busy="saving"
    ><div v-if="orderBusy" class="drawer-loading" aria-busy="true">
      <div v-for="n in 3" :key="n" class="desk-skeleton" />
    </div>
    <template v-else-if="order"
      ><div class="order-drawer-status">
        <span :class="['desk-status', order.status]">{{
          order.fulfillment === "completed"
            ? tr("已完成", "Fulfilled")
            : statusText(order.status)
        }}</span
        ><small>{{ localTime(order.created_at) }}</small>
      </div>
      <button class="copy-order-number" @click="copy">
        {{ order.id }}<PhCopy />
      </button>
      <p v-if="order.status === 'paid_needs_review'" class="desk-error">
        {{
          tr(
            "这笔订单已收款，但原座位或商品无法履约。请联系顾客安排改期或退款。",
            "Payment was received, but the original seats or stock could not be fulfilled. Contact the customer to reschedule or arrange a refund.",
          )
        }}
      </p>
      <section class="drawer-section">
        <h3>{{ tr("顾客信息", "Customer") }}</h3>
        <div class="drawer-customer">
          <span class="customer-monogram">{{
            order.customer?.name.slice(0, 1)
          }}</span>
          <div>
            <strong>{{ order.customer?.name }}</strong>
            <p>
              {{ order.customer?.contact_method }} ·
              {{ order.customer?.contact }}
            </p>
          </div>
        </div>
        <p v-if="order.customer?.notes" class="customer-note">
          {{ order.customer.notes }}
        </p>
      </section>
      <section class="drawer-section">
        <h3>{{ tr("这份订单里", "In this order") }}</h3>
        <article
          v-for="(line, i) in order.quote.lines"
          :key="i"
          class="drawer-order-line"
        >
          <div>
            <strong
              >{{ tr(line.zh, line.en)
              }}<span v-if="!line.booking"> × {{ line.quantity }}</span></strong
            >
            <p v-if="line.booking">
              {{ prettyDate(line.booking.date) }}<br />{{
                line.booking.start
              }}–{{ line.booking.end }} · {{ line.booking.guests }}
              {{ tr("人 · Hamilton 时间", "guests · Hamilton time") }}
            </p>
            <p v-else>{{ tr("到店自提", "Studio pickup") }}</p>
          </div>
          <strong>{{ money(line.total_cents) }}</strong>
        </article>
        <dl class="drawer-totals">
          <div>
            <dt>{{ tr("加元合计", "CAD total") }}</dt>
            <dd>{{ money(order.quote.total_cents) }}</dd>
          </div>
          <div>
            <dt>{{ tr("人民币实付", "Amount in CNY") }}</dt>
            <dd>{{ money(order.quote.cny_fen, "CNY") }}</dd>
          </div>
        </dl>
      </section>
      <section class="drawer-section">
        <label class="desk-field"
          >{{ tr("内部备注", "Staff note")
          }}<textarea
            v-model="order.staff_note"
            rows="3"
            maxlength="1500"
            :placeholder="
              tr(
                '例如：已联系顾客、自提时间、特别安排',
                'For example: contacted guest, pickup time, special arrangements',
              )
            "
          />
        </label>
        <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
      </section>
      <section class="drawer-section">
        <h3>{{ tr("订单记录", "Order timeline") }}</h3>
        <ol class="order-timeline">
          <li v-for="event in order.events" :key="event.id">
            <span class="timeline-dot"
              ><PhCheck v-if="event.event === 'paid'" :size="12" /><PhClock
                v-else
                :size="11"
            /></span>
            <div>
              <strong>{{ eventLabel(event.event, locale === "zh") }}</strong
              ><small
                >{{ localTime(event.created_at) }} ·
                {{
                  event.actor === "system"
                    ? tr("自动处理", "Automatic")
                    : event.actor
                }}</small
              >
            </div>
          </li>
        </ol>
      </section>
    </template>
    <p v-else-if="error" class="desk-error">{{ error }}</p>
    <template v-if="order" #footer
      ><button
        class="desk-button secondary"
        :disabled="saving"
        @click="saveOrder(order.fulfillment === 'completed')"
      >
        {{ tr("保存备注", "Save note") }}</button
      ><button
        v-if="order.status === 'paid'"
        class="desk-button primary"
        :disabled="saving"
        @click="saveOrder(order.fulfillment !== 'completed')"
      >
        <PhArrowCounterClockwise
          v-if="order.fulfillment === 'completed'"
        /><PhCheck v-else />{{
          saving
            ? tr("保存中…", "Saving…")
            : order.fulfillment === "completed"
              ? tr("恢复待完成", "Reopen")
              : tr("标记已到店／自提", "Mark fulfilled")
        }}
      </button></template
    ></SlideOver
  >
</template>
