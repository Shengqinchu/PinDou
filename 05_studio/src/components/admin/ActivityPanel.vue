<script setup lang="ts">
import { contentModule } from "../../content-store";
const copyText = contentModule("components-admin-ActivityPanel", copyTextDefault);

import copyTextDefault from "../../content/components-admin-ActivityPanel.json";
import { say } from "../../state";

import { onMounted, ref, watch } from "vue";
import {
  PhClockCounterClockwise,
  PhArrowLeft,
  PhArrowRight,
  PhArrowClockwise,
} from "@phosphor-icons/vue";
import { useDesk, localTime, type AuditEvent } from "../../admin";
import { locale, tr } from "../../state";
import { eventLabel } from "../../ui";
const props = defineProps<{ active: boolean }>();
const { request } = useDesk();
const entries = ref<AuditEvent[]>([]);
const page = ref(1);
const total = ref(0);
const busy = ref(false);
const error = ref("");
async function load() {
  busy.value = true;
  error.value = "";
  try {
    const data = await request<{ items: AuditEvent[]; total: number }>(
      `/manage/activity?page=${page.value}`,
    );
    entries.value = data.items;
    total.value = data.total;
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
watch(
  () => props.active,
  (value) => {
    if (value) load();
  },
);
onMounted(() => {
  if (props.active) load();
});
function changes(detail: string) {
  try {
    const data = JSON.parse(detail);
    return data.before !== undefined || data.after !== undefined ? data : null;
  } catch {
    return null;
  }
}
function move(delta: number) {
  page.value += delta;
  load();
}
</script>
<template>
  <section>
    <header class="desk-page-heading">
      <div>
        <p class="desk-eyebrow">
          {{ say(copyText.a_record_of_every_change_3437dd) }}
        </p>
        <h1>{{ say(copyText.activity_78a156) }}</h1>
        <p>
          {{
            say(
              copyText.review_order_handling_product_updates_and_schedule_f41605,
            )
          }}
        </p>
      </div>
      <button class="desk-button secondary" :disabled="busy" @click="load">
        <PhArrowClockwise :class="{ spinning: busy }" />{{
          say(copyText.refresh_5efb82)
        }}
      </button>
    </header>
    <section class="desk-surface activity-surface">
      <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
      <div v-else-if="!entries.length && !busy" class="desk-empty">
        <PhClockCounterClockwise :size="34" weight="light" />
        <h2>
          {{ say(copyText.your_activity_will_appear_here_5f333b) }}
        </h2>
        <p>
          {{ say(copyText.after_saving_settings_or_handling_an_order_fa9b4e) }}
        </p>
      </div>
      <article v-for="event in entries" :key="event.id" class="activity-row">
        <span class="activity-icon"
          ><PhClockCounterClockwise :size="18"
        /></span>
        <div>
          <strong>{{ eventLabel(event.event, locale === "zh") }}</strong>
          <p>
            {{ localTime(event.created_at) }} ·
            {{
              event.actor === "system"
                ? say(copyText.automatic_ad54d8)
                : event.actor
            }}
          </p>
          <small>{{ event.order_id }}</small>
          <details v-if="changes(event.detail)" class="audit-changes">
            <summary>{{ say(copyText.view_before_and_after_1d0446) }}</summary>
            <div>
              <section>
                <h3>{{ say(copyText.before_d1233a) }}</h3>
                <pre>{{
                  JSON.stringify(changes(event.detail).before, null, 2)
                }}</pre>
              </section>
              <section>
                <h3>{{ say(copyText.after_3953d8) }}</h3>
                <pre>{{
                  JSON.stringify(changes(event.detail).after, null, 2)
                }}</pre>
              </section>
            </div>
          </details>
          <p
            v-else-if="event.detail && event.event === 'fulfillment_updated'"
            class="activity-note"
          >
            {{ event.detail }}
          </p>
        </div>
      </article>
      <footer class="desk-pagination">
        <span>{{ page }} / {{ Math.max(1, Math.ceil(total / 30)) }}</span>
        <div>
          <button
            class="desk-icon-button"
            :disabled="page <= 1 || busy"
            :aria-label="say(copyText.previous_page_e70a7e)"
            @click="move(-1)"
          >
            <PhArrowLeft /></button
          ><button
            class="desk-icon-button"
            :disabled="page * 30 >= total || busy"
            :aria-label="say(copyText.next_page_5354f3)"
            @click="move(1)"
          >
            <PhArrowRight />
          </button>
        </div>
      </footer>
    </section>
  </section>
</template>
