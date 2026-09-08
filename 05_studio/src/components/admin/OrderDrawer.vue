<script setup lang="ts">
import { contentModule } from "../../content-store";
const copyText = contentModule("components-admin-OrderDrawer", copyTextDefault);

import copyTextDefault from "../../content/components-admin-OrderDrawer.json";
import { say } from "../../state";

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
    notify(copyText.message_a1acbedd[0], copyText.message_a1acbedd[1]);
  } catch {
    notify(copyText.message_3d2221e9[0], copyText.message_3d2221e9[1], "error");
  }
}
</script>
<template>
  <SlideOver
    v-model="orderOpen"
    :title="say(copyText.order_details_07f28a)"
    :subtitle="order?.customer?.name"
    :busy="saving"
    ><div v-if="orderBusy" class="drawer-loading" aria-busy="true">
      <div v-for="n in 3" :key="n" class="desk-skeleton" />
    </div>
    <template v-else-if="order"
      ><div class="order-drawer-status">
        <span :class="['desk-status', order.status]">{{
          order.fulfillment === "completed"
            ? say(copyText.fulfilled_bf1ec7)
            : statusText(order.status)
        }}</span
        ><small>{{ localTime(order.created_at) }}</small>
      </div>
      <button class="copy-order-number" @click="copy">
        {{ order.id }}<PhCopy />
      </button>
      <p v-if="order.status === 'paid_needs_review'" class="desk-error">
        {{ say(copyText.payment_was_received_but_the_original_seats_72b31b) }}
      </p>
      <section class="drawer-section">
        <h3>{{ say(copyText.customer_76be83) }}</h3>
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
        <h3>{{ say(copyText.in_this_order_38d926) }}</h3>
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
              {{ say(copyText.guests_hamilton_time_a7aa80) }}
            </p>
            <p v-else>{{ say(copyText.studio_pickup_c13b87) }}</p>
          </div>
          <strong>{{ money(line.total_cents) }}</strong>
        </article>
        <dl class="drawer-totals">
          <div>
            <dt>{{ say(copyText.cad_total_0fc8b6) }}</dt>
            <dd>{{ money(order.quote.total_cents) }}</dd>
          </div>
          <div>
            <dt>{{ say(copyText.amount_in_cny_62da3c) }}</dt>
            <dd>{{ money(order.quote.cny_fen, "CNY") }}</dd>
          </div>
        </dl>
      </section>
      <section class="drawer-section">
        <label class="desk-field"
          >{{ say(copyText.staff_note_0d849e)
          }}<textarea
            v-model="order.staff_note"
            rows="3"
            maxlength="1500"
            :placeholder="
              say(
                copyText.for_example_contacted_guest_pickup_time_special_be0f3b,
              )
            "
          />
        </label>
        <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
      </section>
      <section class="drawer-section">
        <h3>{{ say(copyText.order_timeline_0fd9c3) }}</h3>
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
                    ? say(copyText.automatic_ad54d8)
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
        {{ say(copyText.save_note_449101) }}</button
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
            ? say(copyText.saving_1bd9fd)
            : order.fulfillment === "completed"
              ? say(copyText.reopen_766aae)
              : say(copyText.mark_fulfilled_d8eac2)
        }}
      </button></template
    ></SlideOver
  >
</template>
