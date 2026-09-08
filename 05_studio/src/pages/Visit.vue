<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  PhArrowRight,
  PhArrowClockwise,
  PhClock,
  PhSun,
} from "@phosphor-icons/vue";
import { commerceApi, CommerceError } from "../commerce";
import { locale, prettyDate, tr, wechat } from "../state";
import {
  reservationDraft as draft,
  readSession,
  saveSession,
  validSelection,
  type ReservationCalendar as Calendar,
  type ReservationPayload,
  type Reservation,
} from "../reservations";
import ReservationCalendar from "../components/ReservationCalendar.vue";
const router = useRouter(),
  calendar = ref<Calendar | null>(null),
  loading = ref(false),
  sending = ref(false),
  error = ref("");
const attempt = ref(
  readSession<{ key: string; body: ReservationPayload }>(
    "puppy-reservation-attempt-v1",
  ),
);
const locked = computed(() => sending.value || !!attempt.value);
const selected = computed(() => validSelection(calendar.value, draft.booking));
let sequence = 0,
  timer: ReturnType<typeof setInterval>,
  alive = true;
async function load() {
  const seq = ++sequence;
  loading.value = true;
  try {
    const value = await commerceApi<Calendar>("/reservation-calendar");
    if (!alive || seq !== sequence) return;
    calendar.value = value;
    if (
      !attempt.value &&
      draft.booking.start &&
      !validSelection(value, draft.booking)
    ) {
      draft.booking.start = "";
      draft.booking.end = "";
      error.value = tr(
        "之前选择的时段已不可预约，请重新选择。",
        "Your previous time is no longer available. Please choose again.",
      );
    }
  } catch (e) {
    if (alive && seq === sequence) error.value = (e as Error).message;
  } finally {
    if (alive && seq === sequence) loading.value = false;
  }
}
function refreshVisible() {
  if (!document.hidden && !sending.value) load();
}
onMounted(() => {
  load();
  timer = setInterval(refreshVisible, 60000);
  window.addEventListener("pageshow", refreshVisible);
  document.addEventListener("visibilitychange", refreshVisible);
});
onBeforeUnmount(() => {
  alive = false;
  sequence++;
  clearInterval(timer);
  window.removeEventListener("pageshow", refreshVisible);
  document.removeEventListener("visibilitychange", refreshVisible);
});
watch(
  () => draft.booking.plan,
  () => {
    if (!locked.value) {
      draft.booking.start = "";
      draft.booking.end = "";
    }
  },
);
function select(value: { date: string; start: string; end: string }) {
  Object.assign(draft.booking, value);
  error.value = "";
}
async function submit() {
  if (sending.value) return;
  if (!attempt.value && (!selected.value || !draft.consent)) return;
  if (!attempt.value) {
    attempt.value = {
      key: crypto.randomUUID(),
      body: {
        booking: { ...draft.booking },
        name: draft.name,
        contact_method: draft.contact_method,
        contact: draft.contact,
        notes: draft.notes,
        consent: draft.consent,
        locale: locale.value,
        website: "",
      },
    };
    saveSession("puppy-reservation-attempt-v1", attempt.value);
  }
  sending.value = true;
  error.value = "";
  try {
    const receipt = await commerceApi<Reservation>("/reservations", {
      method: "POST",
      headers: { "Idempotency-Key": attempt.value.key },
      body: JSON.stringify(attempt.value.body),
    });
    saveSession("puppy-reservation-attempt-v1", null);
    attempt.value = null;
    saveSession("puppy-last-reservation", receipt.id);
    draft.booking.start = "";
    draft.booking.end = "";
    draft.consent = false;
    await router.push("/reservation/" + receipt.id);
  } catch (e) {
    error.value = (e as Error).message;
    if (e instanceof CommerceError && e.code === "reservation_session_missing")
      await load();
    if (
      e instanceof CommerceError &&
      e.status >= 400 &&
      e.status < 500 &&
      !["reservation_session_missing", "reservation_request_changed"].includes(
        e.code || "",
      )
    ) {
      attempt.value = null;
      saveSession("puppy-reservation-attempt-v1", null);
      if (e.status === 409) await load();
    }
  } finally {
    sending.value = false;
  }
}
</script>
<template>
  <section class="reservation-page container">
    <header class="reservation-heading">
      <p class="vision-eyebrow">
        {{
          tr("留一点时间，做喜欢的小事", "A LITTLE TIME FOR SOMETHING YOU LOVE")
        }}
      </p>
      <h1>{{ tr("来拼豆吧", "Come make something") }}</h1>
      <p>
        {{
          tr(
            "选好体验和时间，告诉我们你和谁一起来。店主确认后，预约就安排好了。",
            "Choose your experience and a time, then tell us who is coming. Your visit is booked when the host confirms it.",
          )
        }}
      </p>
    </header>
    <form @submit.prevent="submit" class="reservation-form">
      <fieldset class="reservation-plans" :disabled="locked">
        <legend>{{ tr("先选一种体验", "Choose your experience") }}</legend>
        <label :class="{ selected: draft.booking.plan === 'hourly' }"
          ><input
            v-model="draft.booking.plan"
            type="radio"
            value="hourly"
          /><PhClock :size="28" weight="light" /><strong>{{
            tr("按时体验", "By the hour")
          }}</strong
          ><span>{{
            tr(
              "至少两小时，慢慢拼出喜欢的样子。",
              "At least two hours to make something you love.",
            )
          }}</span></label
        ><label :class="{ selected: draft.booking.plan === 'day' }"
          ><input v-model="draft.booking.plan" type="radio" value="day" /><PhSun
            :size="28"
            weight="light"
          /><strong>{{ tr("全天体验", "A day of making") }}</strong
          ><span>{{
            tr(
              "从所选时间，拼到当天可预约时段结束。",
              "From your chosen arrival until the end of that day's available hours.",
            )
          }}</span></label
        >
        <aside class="reservation-credit">
          <span class="vision-eyebrow">{{
            tr("储值优惠 · 到店了解", "PREPAID HOURS · ASK IN THE STUDIO")
          }}</span
          ><strong>{{ tr("7 加元／小时", "CA$7 / hour") }}</strong>
          <p>
            {{
              tr(
                "10 小时起，且储值时长不少于当日使用总时长的 2 倍。可当天使用，可多人共同使用。",
                "Prepay at least 10 hours and at least twice the total hours used that day. Use them the same day and share them with your group.",
              )
            }}
          </p>
          <small>{{
            tr(
              "仅作优惠说明，无需在此选择。",
              "For information only; this is not a selectable plan.",
            )
          }}</small>
        </aside>
      </fieldset>
      <section class="reservation-time">
        <div class="reservation-section-title">
          <div>
            <span>01</span>
            <h2>
              {{ tr("挑一个合适的时间", "Pick a time that feels right") }}
            </h2>
          </div>
          <button
            type="button"
            class="icon-button"
            :disabled="loading || locked"
            :aria-label="tr('刷新时间表', 'Refresh timetable')"
            @click="load"
          >
            <PhArrowClockwise :class="{ spinning: loading }" />
          </button>
        </div>
        <p
          v-if="loading && !calendar"
          class="reservation-loading"
          role="status"
        >
          {{ tr("正在整理未来两周的时间……", "Loading the next two weeks…") }}
        </p>
        <ReservationCalendar
          v-if="calendar"
          :calendar="calendar"
          :booking="draft.booking"
          :disabled="loading || locked"
          @select="select"
        />
        <p v-if="!calendar && !loading" class="form-error" role="alert">
          {{ error }}
          <button type="button" class="text-link" @click="load">
            {{ tr("重新加载", "Try again") }}
          </button>
        </p>
        <div class="reservation-selection" aria-live="polite">
          <span>{{ tr("你的时间", "Your time") }}</span
          ><strong v-if="selected"
            >{{ prettyDate(draft.booking.date) }} · {{ draft.booking.start }}–{{
              draft.booking.end
            }}</strong
          ><strong v-else>{{
            tr("请在时间表中选择", "Choose a time in the timetable")
          }}</strong>
        </div>
      </section>
      <section class="reservation-guest">
        <div class="reservation-section-title">
          <div>
            <span>02</span>
            <h2>{{ tr("和谁一起来？", "Who is coming along?") }}</h2>
          </div>
        </div>
        <label class="field reservation-guests"
          >{{ tr("同行人数（包括你自己）", "Number of guests, including you")
          }}<input
            v-model.number="draft.booking.guests"
            type="number"
            min="1"
            max="20"
            required
            :disabled="locked"
        /></label>
        <p class="fine-print">
          {{
            tr(
              "我们会根据同行人数，由店主确认具体安排。",
              "The host will confirm arrangements for your group.",
            )
          }}
        </p>
        <div class="reservation-contact-fields">
          <label class="field"
            >{{ tr("客人名称", "Guest name")
            }}<input
              v-model.trim="draft.name"
              autocomplete="name"
              maxlength="80"
              required
              :disabled="locked"
            /><small>{{
              tr(
                "如已添加店主微信，可以填写微信名称，方便联系。",
                "If you have added the host on WeChat, your WeChat name is helpful.",
              )
            }}</small></label
          ><label class="field"
            >{{ tr("联系方式", "Contact method")
            }}<select v-model="draft.contact_method" :disabled="locked">
              <option value="wechat">{{ tr("微信", "WeChat") }}</option>
              <option value="phone">{{ tr("电话", "Phone") }}</option>
              <option value="email">{{ tr("电子邮箱", "Email") }}</option>
              <option value="other">{{ tr("其他方式", "Another way") }}</option>
            </select></label
          ><label class="field"
            >{{
              draft.contact_method === "wechat"
                ? tr("微信号", "WeChat ID")
                : draft.contact_method === "phone"
                  ? tr("电话号码", "Phone number")
                  : draft.contact_method === "email"
                    ? tr("电子邮箱地址", "Email address")
                    : tr("联系信息", "Contact details")
            }}<input
              v-model.trim="draft.contact"
              :type="
                draft.contact_method === 'email'
                  ? 'email'
                  : draft.contact_method === 'phone'
                    ? 'tel'
                    : 'text'
              "
              minlength="3"
              maxlength="180"
              required
              :disabled="locked" /></label
          ><label class="field"
            >{{
              tr(
                "想提前告诉我们的事（可选）",
                "Anything you would like us to know? (optional)",
              )
            }}<textarea
              v-model="draft.notes"
              rows="3"
              maxlength="1500"
              :disabled="locked"
            />
          </label>
        </div>
        <label class="reservation-consent"
          ><input
            v-model="draft.consent"
            type="checkbox"
            required
            :disabled="locked"
          /><span>{{
            tr(
              "同意将以上信息用于本次预约联系。",
              "I agree to use these details to arrange this visit.",
            )
          }}</span></label
        >
      </section>
      <div class="reservation-submit">
        <p v-if="error && calendar" class="form-error" role="alert">
          {{ error }}
        </p>
        <p v-if="attempt && !sending" role="status">
          {{
            tr(
              "已保留这次提交内容。请恢复预约结果，避免重复提交；如浏览器数据已清除，请联系店主查询。",
              "Your submission is saved. Recover its result to avoid a duplicate. If browser data was cleared, ask the host to look it up.",
            )
          }}
        </p>
        <button
          class="button button-primary"
          :disabled="
            sending || loading || (!attempt && (!selected || !draft.consent))
          "
        >
          {{
            sending
              ? tr("正在提交……", "Sending…")
              : attempt
                ? tr("恢复预约结果", "Recover reservation")
                : tr("提交预约", "Request this visit")
          }}<PhArrowRight />
        </button>
        <p>
          {{
            tr(
              "提交后等待店主确认，无需在此付款。",
              "Your request will wait for the host's confirmation. No payment is needed here.",
            )
          }}
        </p>
        <span v-if="attempt" class="fine-print"
          >{{ tr("店主微信：", "Host WeChat: ") }}{{ wechat }}</span
        >
      </div>
    </form>
  </section>
</template>
