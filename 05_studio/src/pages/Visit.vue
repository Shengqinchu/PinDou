<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import AutoHeight from "../components/AutoHeight.vue";
import {
  PhArrowRight,
  PhCheck,
  PhClock,
  PhMapPin,
  PhShoppingBagOpen,
} from "@phosphor-icons/vue";
import {
  hamiltonDate,
  mapsUrl,
  media,
  plusDays,
  prettyDate,
  tr,
} from "../state";
import {
  addToBag,
  catalog,
  commerceApi,
  loadCatalog,
  money,
  type Availability,
  type Slot,
} from "../commerce";
const plan = ref("hourly");
const date = ref(plusDays(hamiltonDate(), 1));
const guests = ref(1);
const duration = ref(120);
const availability = ref<Availability>();
const selected = ref<Slot>();
const loading = ref(false);
const error = ref("");
const added = ref(false);
const today = ref(hamiltonDate());
const days = computed(() =>
  Array.from({ length: 7 }, (_, i) => plusDays(today.value, i)),
);
const plans = computed(
  () =>
    catalog.value?.products.filter(
      (p) => p.kind === "experience" && p.active,
    ) || [],
);
const chosen = computed(() => plans.value.find((p) => p.id === plan.value));
watch(plans, (value) => {
  if (value.length && !value.some((p) => p.id === plan.value))
    plan.value = value[0].id;
});
const amount = computed(
  () =>
    (chosen.value?.price_cents || 0) *
    (plan.value === "hourly" ? (duration.value / 60) * guests.value : 1),
);
const durations = Array.from({ length: 15 }, (_, i) => 60 + i * 30);
let sequence = 0;
let timer: ReturnType<typeof setInterval>;
function dayLabel(value: string) {
  return new Intl.DateTimeFormat(tr("zh-CN", "en-CA"), {
    weekday: "short",
    timeZone: "UTC",
  }).format(new Date(value + "T12:00:00Z"));
}
async function refreshSlots() {
  const request = ++sequence;
  loading.value = true;
  error.value = "";
  added.value = false;
  const priorStart = selected.value?.start;
  selected.value = undefined;
  try {
    const result = await commerceApi<Availability>(
      `/availability?date=${date.value}&plan=${plan.value}&guests=${guests.value}&duration=${duration.value}`,
    );
    if (request !== sequence) return;
    availability.value = result;
    selected.value = result.slots.find(
      (s) => s.available && s.start === priorStart,
    );
  } catch (e) {
    if (request === sequence) {
      error.value = (e as Error).message;
      availability.value = undefined;
    }
  } finally {
    if (request === sequence) loading.value = false;
  }
}
watch(plan, (value) => {
  guests.value = value === "pair" ? 2 : 1;
  selected.value = undefined;
});
watch([date, plan, guests, duration], refreshSlots);
onMounted(async () => {
  try {
    await loadCatalog();
    await refreshSlots();
  } catch (e) {
    error.value = (e as Error).message;
  }
  timer = setInterval(() => {
    today.value = hamiltonDate();
    if (!document.hidden && !added.value) refreshSlots();
  }, 30000);
});
onBeforeUnmount(() => {
  clearInterval(timer);
  sequence++;
});
function add() {
  if (!selected.value || loading.value || !selected.value.available) return;
  addToBag(plan.value, {
    date: date.value,
    start: selected.value.start,
    end: selected.value.end,
    guests: guests.value,
  });
  added.value = true;
}
</script>
<template>
  <div class="container booking-layout section-bottom visit-commerce">
    <aside class="booking-story">
      <span class="eyebrow">A LITTLE TIME, WELL SPENT</span>
      <h1>
        {{ tr("给自己，", "Make room") }}<br /><em>{{
          tr("留一个下午。", "for a little joy.")
        }}</em>
      </h1>
      <p>
        {{
          tr(
            "选一个有空的日子，把喜欢的颜色慢慢拼成生活里的小小快乐。",
            "Choose a day. Pull up a chair. Turn the colours you love into a little everyday joy.",
          )
        }}
      </p>
      <img
        :src="media('studio-04')"
        width="1080"
        height="1440"
        :alt="
          tr(
            '窗边的拼豆座位与作品墙',
            'A sunlit bead table and a wall of little creations',
          )
        "
      />
      <ul class="inclusion-list">
        <li>
          <PhCheck />{{
            tr("独立座位与拼豆工具", "Your own seat and bead tools")
          }}
        </li>
        <li>
          <PhCheck />{{
            tr("图案与配色帮助", "Help with patterns and colours")
          }}
        </li>
        <li>
          <PhCheck />{{
            tr("烫豆与成品制作建议", "Finishing help for your creation")
          }}
        </li>
      </ul>
      <a class="text-link" :href="mapsUrl" target="_blank" rel="noreferrer"
        ><PhMapPin />8 Hughson St N, Hamilton</a
      >
    </aside>
    <section
      class="booking-panel commerce-panel"
      :aria-label="tr('选择到店体验', 'Choose your studio experience')"
    >
      <ol class="purchase-steps">
        <li class="current"><span>01</span>{{ tr("选体验", "Choose") }}</li>
        <li><span>02</span>{{ tr("购物车", "Your bag") }}</li>
        <li><span>03</span>{{ tr("付款确认", "Pay & confirm") }}</li>
      </ol>
      <div class="form-section">
        <h2>
          {{ tr("想怎样度过这段时间？", "How would you like to spend it?") }}
        </h2>
        <div class="plan-options">
          <label
            v-for="p in plans"
            :key="p.id"
            :class="['plan-option', { selected: plan === p.id }]"
            ><input
              v-model="plan"
              type="radio"
              name="plan"
              :value="p.id"
            /><span>{{ tr(p.zh, p.en) }}</span
            ><strong
              ><sup>CA$</sup
              >{{ ((p.price_cents || 0) / 100).toString() }}</strong
            ><small>{{
              p.id === "hourly"
                ? tr("/ 人 / 小时", "/ person / hour")
                : p.id === "pair"
                  ? tr("/ 两人", "/ two people")
                  : tr("/ 人", "/ person")
            }}</small></label
          >
        </div>
        <p class="fine-print">
          {{
            tr(
              "全天体验从所选到店时间开始，至当天打烊。",
              "Day passes run from your selected arrival time until closing.",
            )
          }}
        </p>
      </div>
      <div class="form-section slot-section">
        <div class="section-label">
          <h2>{{ tr("挑一个有空的日子", "Find your little moment") }}</h2>
          <span><PhClock />{{ tr("Hamilton 时间", "Hamilton time") }}</span>
        </div>
        <div
          class="date-strip"
          :aria-label="tr('快捷选择日期', 'Quick date selection')"
        >
          <button
            v-for="d in days"
            :key="d"
            :class="['date-chip', { selected: date === d }]"
            :aria-pressed="date === d"
            :aria-label="prettyDate(d)"
            @click="date = d"
          >
            <small>{{ dayLabel(d) }}</small
            ><strong>{{ Number(d.slice(-2)) }}</strong>
          </button>
        </div>
        <div class="form-grid compact-fields">
          <label class="field field-full"
            >{{ tr("到店日期", "Visit date")
            }}<input
              v-model="date"
              type="date"
              name="date"
              :min="today"
              :max="plusDays(today, 90)"
              required
          /></label>
          <label class="field"
            >{{ tr("同行人数", "Guests")
            }}<input
              v-model.number="guests"
              name="guests"
              type="number"
              min="1"
              :max="catalog?.settings.capacity || 100"
              step="1"
              :readonly="plan !== 'hourly'"
          /></label>
          <label v-if="plan === 'hourly'" class="field"
            >{{ tr("体验时长", "Duration")
            }}<select v-model.number="duration" name="duration">
              <option v-for="d in durations" :key="d" :value="d">
                {{ d / 60 }} {{ tr("小时", "hours") }}
              </option>
            </select></label
          >
          <div v-else class="day-pass-note">
            <PhClock />{{ tr("所选时间到打烊", "Arrival until closing") }}
          </div>
        </div>
        <AutoHeight
          ><div class="slot-results" :aria-busy="loading">
            <p v-if="loading" class="form-help" role="status">
              {{ tr("正在查看可用座位…", "Checking available seats…") }}
            </p>
            <div
              v-if="availability?.slots.length"
              class="time-grid"
              :aria-label="tr('可用到店时段', 'Available visit times')"
            >
              <button
                v-for="slot in availability.slots"
                :key="slot.start"
                :class="[
                  'time-chip',
                  { selected: selected?.start === slot.start },
                ]"
                :disabled="loading || !slot.available"
                :aria-pressed="selected?.start === slot.start"
                @click="
                  selected = slot;
                  added = false;
                "
              >
                <strong>{{ slot.start }}</strong
                ><small>{{
                  slot.available
                    ? tr(
                        `余 ${slot.remaining} 位`,
                        `${slot.remaining} seats left`,
                      )
                    : tr("已满", "Full")
                }}</small>
              </button>
            </div>
            <div
              v-else-if="!error && !loading"
              class="availability-note"
              role="status"
            >
              <PhClock :size="26" />
              <div>
                <strong>{{
                  availability?.reason === "not_open"
                    ? tr(
                        "新的到店时段，正在安排中",
                        "New studio dates are on their way",
                      )
                    : tr(
                        "这一天暂时没有可选时段",
                        "No times available on this day",
                      )
                }}</strong>
                <p>
                  {{
                    availability?.reason === "not_open"
                      ? tr(
                          "开放后，就可以选时间、加购并直接付款。",
                          "Once dates open, choose your time, add to your bag and pay here.",
                        )
                      : tr(
                          "试试另一个日期，给喜欢的事留点时间。",
                          "Try another date and make a little room for something you love.",
                        )
                  }}
                </p>
              </div>
            </div>
            <p v-if="error" class="form-error" role="alert">
              {{ error }}
              <button class="text-link" @click="refreshSlots">
                {{ tr("重试", "Try again") }}
              </button>
            </p>
          </div></AutoHeight
        >
      </div>
      <div class="visit-total">
        <div>
          <span>{{ tr("本次体验", "Your experience") }}</span
          ><strong>{{ money(amount) }}</strong>
        </div>
        <p v-if="selected">
          {{ prettyDate(date) }} · {{ selected.start }}–{{ selected.end }} ·
          {{ guests }} {{ tr("人", "guests") }}
        </p>
        <p v-else>
          {{
            tr(
              "选好时间，再放进购物车。",
              "Choose a time, then add it to your bag.",
            )
          }}
        </p>
      </div>
      <button
        class="button button-primary full-button"
        :disabled="!selected || loading || added"
        @click="add"
      >
        <template v-if="added"
          >{{ tr("已放进购物车", "Added to your bag") }}<PhCheck /></template
        ><template v-else
          >{{ tr("加入购物车", "Add to bag") }}<PhShoppingBagOpen
        /></template>
      </button>
      <RouterLink
        v-if="added"
        class="button button-outline full-button"
        to="/cart"
        >{{ tr("去结账", "Go to checkout") }}<PhArrowRight
      /></RouterLink>
      <p class="fine-print centered">
        {{
          tr(
            "加入购物车不会占位；结账暂留座位，付款后立即确认。",
            "Adding to your bag does not reserve a seat. Checkout holds it; payment confirms it.",
          )
        }}
      </p>
    </section>
  </div>
</template>
