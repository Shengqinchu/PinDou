<script setup lang="ts">
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
          {{ tr("每一次更改，都有来处", "A RECORD OF EVERY CHANGE") }}
        </p>
        <h1>{{ tr("操作记录", "Activity") }}</h1>
        <p>
          {{
            tr(
              "查看订单处理、商品调整和排班变更。",
              "Review order handling, product updates and schedule changes.",
            )
          }}
        </p>
      </div>
      <button class="desk-button secondary" :disabled="busy" @click="load">
        <PhArrowClockwise :class="{ spinning: busy }" />{{
          tr("刷新", "Refresh")
        }}
      </button>
    </header>
    <section class="desk-surface activity-surface">
      <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
      <div v-else-if="!entries.length && !busy" class="desk-empty">
        <PhClockCounterClockwise :size="34" weight="light" />
        <h2>
          {{ tr("操作记录会留在这里", "Your activity will appear here") }}
        </h2>
        <p>
          {{
            tr(
              "保存设置、处理订单后，就能看到对应记录。",
              "After saving settings or handling an order, its record appears here.",
            )
          }}
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
                ? tr("自动处理", "Automatic")
                : event.actor
            }}
          </p>
          <small>{{ event.order_id }}</small>
          <details v-if="changes(event.detail)" class="audit-changes">
            <summary>{{ tr("查看修改前后", "View before and after") }}</summary>
            <div>
              <section>
                <h3>{{ tr("修改前", "Before") }}</h3>
                <pre>{{
                  JSON.stringify(changes(event.detail).before, null, 2)
                }}</pre>
              </section>
              <section>
                <h3>{{ tr("修改后", "After") }}</h3>
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
            :aria-label="tr('上一页', 'Previous page')"
            @click="move(-1)"
          >
            <PhArrowLeft /></button
          ><button
            class="desk-icon-button"
            :disabled="page * 30 >= total || busy"
            :aria-label="tr('下一页', 'Next page')"
            @click="move(1)"
          >
            <PhArrowRight />
          </button>
        </div>
      </footer>
    </section>
  </section>
</template>
