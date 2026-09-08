<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import {
  PhArrowRight,
  PhArrowClockwise,
  PhMagnifyingGlass,
  PhCalendarDots,
  PhClock,
  PhCheck,
} from "@phosphor-icons/vue";
import { useDesk } from "../../admin";
import { hamiltonDate, plusDays, prettyDate, tr } from "../../state";
import type { Reservation, ReservationPayload } from "../../reservations";
import SlideOver from "../SlideOver.vue";
import ToggleSwitch from "../ToggleSwitch.vue";
type Entry = Reservation & { payload: ReservationPayload; staff_note: string };
const props = defineProps<{ active: boolean; calendar?: boolean }>();
const { request } = useDesk();
const items = ref<Entry[]>([]),
  counts = ref<Record<string, number>>({}),
  total = ref(0),
  status = ref("all"),
  day = ref(props.calendar ? hamiltonDate() : ""),
  search = ref(""),
  page = ref(1),
  busy = ref(false),
  error = ref("");
const policy = ref({ exclusive_groups: false, version: 1 }),
  policyBusy = ref(false);
const entry = ref<Entry>(),
  open = ref(false),
  saving = ref(false),
  nextStatus = ref("pending"),
  note = ref(""),
  saveError = ref("");
const days = computed(() =>
  Array.from({ length: 14 }, (_, i) => plusDays(hamiltonDate(), i)),
);
let sequence = 0,
  debounce: ReturnType<typeof setTimeout>;
const labels = computed<Record<string, string>>(() => ({
  pending: tr("待确认", "Pending"),
  confirmed: tr("已确认", "Confirmed"),
  completed: tr("已完成", "Completed"),
  cancelled: tr("已取消", "Cancelled"),
}));
async function load() {
  const seq = ++sequence;
  busy.value = true;
  error.value = "";
  try {
    const query = new URLSearchParams({
      status: status.value,
      page: String(page.value),
      search: search.value,
    });
    if (day.value) query.set("day", day.value);
    const data = await request<{
      items: Entry[];
      total: number;
      counts: Record<string, number>;
      policy: { exclusive_groups: boolean | number; version: number };
    }>("/manage/reservations?" + query);
    if (seq !== sequence) return;
    items.value = data.items;
    total.value = data.total;
    counts.value = data.counts;
    policy.value = {
      exclusive_groups: !!data.policy.exclusive_groups,
      version: data.policy.version,
    };
  } catch (e) {
    if (seq === sequence) error.value = (e as Error).message;
  } finally {
    if (seq === sequence) busy.value = false;
  }
}
function inspect(item: Entry) {
  entry.value = item;
  nextStatus.value = item.status;
  note.value = item.staff_note;
  saveError.value = "";
  open.value = true;
}
async function save() {
  if (!entry.value || saving.value) return;
  saving.value = true;
  saveError.value = "";
  try {
    await request("/manage/reservations/" + entry.value.id, {
      method: "PATCH",
      body: JSON.stringify({
        status: nextStatus.value,
        staff_note: note.value,
        version: entry.value.version,
      }),
    });
    open.value = false;
    await load();
  } catch (e) {
    saveError.value = (e as Error).message;
  } finally {
    saving.value = false;
  }
}
async function changePolicy(value: boolean) {
  if (policyBusy.value) return;
  policyBusy.value = true;
  error.value = "";
  try {
    policy.value = await request("/manage/reservation-policy", {
      method: "PUT",
      body: JSON.stringify({
        exclusive_groups: value,
        version: policy.value.version,
      }),
    });
    await load();
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    policyBusy.value = false;
  }
}
watch(
  () => props.active,
  (v) => {
    if (v) load();
  },
  { immediate: true },
);
watch([status, day], () => {
  page.value = 1;
  if (props.active) load();
});
watch(search, () => {
  clearTimeout(debounce);
  debounce = setTimeout(() => {
    page.value = 1;
    load();
  }, 300);
});
onBeforeUnmount(() => {
  sequence++;
  clearTimeout(debounce);
});
defineExpose({ refresh: load });
</script>
<template>
  <section class="reservation-desk">
    <header class="desk-page-heading">
      <div>
        <p class="desk-eyebrow">
          {{ tr("照顾好每一次期待", "A LITTLE CARE FOR EVERY VISIT") }}
        </p>
        <h1>
          {{
            calendar
              ? tr("预约日历", "Reservation calendar")
              : tr("预约管理", "Studio reservations")
          }}
        </h1>
        <p>
          {{
            tr(
              "先核对时间和同行人数，再联系客人确认。这里的预约无需在线付款。",
              "Review the time and group size, then contact your guest and confirm. These reservations do not require online payment.",
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
    <div v-if="!calendar" class="reservation-desk-metrics">
      <button @click="status = 'pending'">
        <PhClock /><span>{{ tr("等待确认", "Waiting for you") }}</span
        ><strong>{{ counts.pending || 0 }}</strong></button
      ><button @click="status = 'confirmed'">
        <PhCalendarDots /><span>{{ tr("已确认预约", "Confirmed visits") }}</span
        ><strong>{{ counts.confirmed || 0 }}</strong></button
      ><button @click="status = 'completed'">
        <PhCheck /><span>{{ tr("已完成到访", "Completed visits") }}</span
        ><strong>{{ counts.completed || 0 }}</strong>
      </button>
    </div>
    <div
      v-if="calendar"
      class="reservation-desk-days"
      :aria-label="tr('选择预约日期', 'Choose reservation date')"
    >
      <button
        v-for="date in days"
        :key="date"
        :class="{ selected: day === date }"
        @click="day = date"
      >
        <span>{{ prettyDate(date) }}</span
        ><PhCalendarDots :size="17" />
      </button>
    </div>
    <div class="reservation-desk-policy">
      <div>
        <strong>{{ tr("同一时段只接待一组", "One group at a time") }}</strong>
        <p>
          {{
            tr(
              "开启后，确认一组会关闭重叠时段；待确认申请不会占用时段。",
              "When enabled, a confirmed group closes overlapping times. Pending requests do not hold a time.",
            )
          }}
        </p>
      </div>
      <ToggleSwitch
        :model-value="policy.exclusive_groups"
        :disabled="policyBusy"
        :label="tr('同一时段只接待一组', 'One group at a time')"
        @update:model-value="changePolicy"
      />
    </div>
    <div class="reservation-desk-filters">
      <label class="desk-field"
        >{{ tr("预约状态", "Status")
        }}<select v-model="status">
          <option value="all">{{ tr("全部", "All") }}</option>
          <option v-for="(label, key) in labels" :key="key" :value="key">
            {{ label }}
          </option>
        </select></label
      ><label class="desk-field"
        >{{ tr("到店日期", "Visit date")
        }}<input v-model="day" type="date" /></label
      ><label class="desk-field"
        >{{ tr("姓名或预约编号", "Name or reference")
        }}<input v-model.trim="search" type="search" /></label
      ><button
        class="desk-link"
        @click="
          status = 'all';
          day = '';
          search = '';
        "
      >
        {{ tr("清除筛选", "Clear filters") }}
      </button>
    </div>
    <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
    <p v-if="busy && !items.length" class="reservation-loading" role="status">
      {{ tr("正在查看预约……", "Loading reservations…") }}
    </p>
    <div v-else-if="!items.length" class="reservation-desk-empty">
      <PhCalendarDots :size="35" weight="light" />
      <h2>{{ tr("这里还没有预约", "No reservations here yet") }}</h2>
      <p>
        {{
          tr(
            "顾客提交后，就可以在这里核对并确认安排。",
            "When a guest submits a request, you can review and confirm it here.",
          )
        }}
      </p>
    </div>
    <div v-else class="reservation-desk-list">
      <button
        v-for="item in items"
        :key="item.id"
        class="reservation-desk-row"
        @click="inspect(item)"
      >
        <div>
          <strong>{{ item.name }}</strong
          ><small>{{ item.id }}</small>
        </div>
        <div>
          <span>{{ prettyDate(item.booking.date) }}</span
          ><small
            >{{ item.booking.start }}–{{ item.booking.end }} ·
            {{ item.booking.guests }} {{ tr("人", "guests") }}</small
          >
        </div>
        <span :class="['reservation-status', item.status]">{{
          labels[item.status]
        }}</span
        ><PhArrowRight :size="19" />
      </button>
    </div>
    <div class="reservation-desk-pagination">
      <button
        class="desk-button secondary"
        :disabled="page === 1 || busy"
        @click="
          page--;
          load();
        "
      >
        {{ tr("上一页", "Previous") }}</button
      ><span
        >{{ tr("共", "Total") }} {{ total }}
        {{ tr("份预约", "reservations") }}</span
      ><button
        class="desk-button secondary"
        :disabled="page * 30 >= total || busy"
        @click="
          page++;
          load();
        "
      >
        {{ tr("下一页", "Next") }}
      </button>
    </div>
    <SlideOver
      v-model="open"
      :title="entry?.name || tr('预约详情', 'Reservation details')"
      :subtitle="entry?.id"
      :busy="saving"
      ><template v-if="entry"
        ><dl class="reservation-desk-summary">
          <div>
            <dt>{{ tr("到访", "Visit") }}</dt>
            <dd>
              {{ prettyDate(entry.booking.date) }}<br />{{
                entry.booking.start
              }}–{{ entry.booking.end }}
            </dd>
          </div>
          <div>
            <dt>{{ tr("体验与人数", "Experience and guests") }}</dt>
            <dd>
              {{
                entry.booking.plan === "day"
                  ? tr("全天体验", "Day visit")
                  : tr("按时体验", "Hourly visit")
              }}
              · {{ entry.booking.guests }} {{ tr("人", "guests") }}
            </dd>
          </div>
          <div>
            <dt>{{ tr("联系方式", "Contact") }}</dt>
            <dd>
              {{
                entry.payload.contact_method === "wechat"
                  ? tr("微信", "WeChat")
                  : entry.payload.contact_method === "phone"
                    ? tr("电话", "Phone")
                    : entry.payload.contact_method === "email"
                      ? tr("邮箱", "Email")
                      : tr("其他", "Other")
              }}：{{ entry.payload.contact }}
            </dd>
          </div>
          <div v-if="entry.payload.notes">
            <dt>{{ tr("客人留言", "Guest note") }}</dt>
            <dd>{{ entry.payload.notes }}</dd>
          </div>
        </dl>
        <p class="fine-print">
          {{
            tr(
              "保存会更新客人结果页；请用以上联系方式另行通知客人。",
              "Saving updates the guest's result page. Please also contact the guest using the details above.",
            )
          }}
        </p>
        <label class="desk-field"
          >{{ tr("更新预约状态", "Update reservation status")
          }}<select
            v-model="nextStatus"
            :disabled="saving"
            :aria-label="tr('更新预约状态', 'Update reservation status')"
          >
            <option v-for="(label, key) in labels" :key="key" :value="key">
              {{ label }}
            </option>
          </select></label
        ><label class="desk-field"
          >{{ tr("店内备注（客人不可见）", "Staff note (private)")
          }}<textarea
            v-model="note"
            rows="4"
            maxlength="1500"
            :disabled="saving"
          />
        </label>
        <p v-if="saveError" class="desk-error" role="alert">
          {{ saveError }}
        </p></template
      ><template #footer
        ><button
          class="desk-button secondary"
          :disabled="saving"
          @click="open = false"
        >
          {{ tr("暂不更改", "Close") }}</button
        ><button class="desk-button primary" :disabled="saving" @click="save">
          {{
            saving
              ? tr("保存中……", "Saving…")
              : tr("保存安排", "Save arrangement")
          }}<PhCheck /></button></template
    ></SlideOver>
  </section>
</template>
