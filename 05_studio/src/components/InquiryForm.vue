<script setup lang="ts">
import { reactive, ref } from "vue";
import { PhArrowRight, PhCheck, PhCopy } from "@phosphor-icons/vue";
import { api, locale, tr, wechat } from "../state";
export type BookingDraft = {
  date: string;
  start: string;
  end: string;
  guests: number;
  plan: "hourly" | "day" | "pair";
};
const props = defineProps<{
  kind: "visit" | "pickup";
  booking?: BookingDraft;
  items?: { id: string; quantity: number }[];
  summary: string[];
  disabled?: boolean;
}>();
const emit = defineEmits<{ complete: []; busy: [value: boolean] }>();
const form = reactive({
  name: "",
  contact_method: "wechat",
  contact: "",
  notes: "",
  consent: false,
  website: "",
});
const sending = ref(false);
const error = ref("");
const receipt = ref("");
const receiptSummary = ref<string[]>([]);
const receiptHeading = ref<HTMLElement>();
const copied = ref(false);
let requestKey = "";
let lastPayload = "";

async function submit() {
  if (sending.value || props.disabled) return;
  error.value = "";
  if (props.booking && props.booking.end <= props.booking.start) {
    error.value = tr(
      "结束时间需要晚于开始时间，请调整后提交。",
      "Please choose an end time after your start time.",
    );
    return;
  }
  const payload = JSON.stringify({
    ...form,
    kind: props.kind,
    locale: locale.value,
    booking: props.booking ?? null,
    items: props.items ?? [],
  });
  if (payload !== lastPayload) {
    requestKey = crypto.randomUUID();
    lastPayload = payload;
  }
  sending.value = true;
  emit("busy", true);
  const snapshot = [...props.summary];
  try {
    const result = await api<{ id: string; status: string }>("/requests", {
      method: "POST",
      headers: { "Idempotency-Key": requestKey },
      body: payload,
    });
    receipt.value = result.id;
    receiptSummary.value = snapshot;
    form.name = "";
    form.contact = "";
    form.notes = "";
    form.consent = false;
    emit("complete");
    setTimeout(() => receiptHeading.value?.focus(), 0);
  } catch (e) {
    error.value =
      e instanceof Error
        ? e.message
        : tr("提交失败，请稍后重试。", "Please try again in a moment.");
  } finally {
    sending.value = false;
    emit("busy", false);
  }
}
async function copyReceipt() {
  try {
    await navigator.clipboard.writeText(
      `${receipt.value}\n${receiptSummary.value.join("\n")}`,
    );
    copied.value = true;
  } catch {
    copied.value = false;
  }
}
</script>
<template>
  <section v-if="receipt" class="receipt" aria-live="polite">
    <div class="receipt-check"><PhCheck :size="28" /></div>
    <h2 ref="receiptHeading" tabindex="-1">
      {{ tr("收到你的小计划了。", "Your little plan is with us.") }}
    </h2>
    <p>
      {{
        tr(
          "这是待店主确认的意向。请保留编号，我们会通过你填写的联系方式确认安排。",
          "This is a request awaiting the host’s confirmation. Keep your reference. We will use the contact details you provided to confirm the arrangements.",
        )
      }}
    </p>
    <div class="receipt-number">
      <span>{{ receipt }}</span
      ><button
        class="icon-button"
        @click="copyReceipt"
        :aria-label="tr('复制意向编号', 'Copy request reference')"
      >
        <PhCheck v-if="copied" /><PhCopy v-else />
      </button>
    </div>
    <ul>
      <li v-for="line in receiptSummary" :key="line">{{ line }}</li>
    </ul>
    <p class="fine-print">
      {{
        tr(
          "尚未锁定座位或库存，也未收取费用。需要补充信息时，可微信联系：",
          "No seats or stock have been reserved and no payment has been taken. To add anything, find us on WeChat: ",
        )
      }}
      {{ wechat }}
    </p>
    <RouterLink to="/" class="text-link"
      >{{ tr("回小屋逛逛", "Back to the studio") }}<PhArrowRight
    /></RouterLink>
  </section>
  <form v-else @submit.prevent="submit" class="inquiry-form">
    <fieldset :disabled="sending || disabled">
      <slot name="details" />
      <div class="form-section">
        <h2>{{ tr("怎么称呼你？", "A little about you.") }}</h2>
        <div class="form-grid">
          <label class="field"
            >{{ tr("你的称呼", "Your name")
            }}<input
              v-model.trim="form.name"
              name="name"
              autocomplete="name"
              required
              maxlength="80"
              :placeholder="
                tr('让我们知道怎么称呼你', 'What should we call you?')
              " /></label
          ><label class="field"
            >{{ tr("联系途径", "Contact me by")
            }}<select v-model="form.contact_method" name="contact_method">
              <option value="wechat">{{ tr("微信", "WeChat") }}</option>
              <option value="email">{{ tr("电子邮箱", "Email") }}</option>
              <option value="phone">
                {{ tr("电话 / 短信", "Phone / text") }}
              </option>
            </select></label
          >
        </div>
        <label class="field"
          >{{
            form.contact_method === "wechat"
              ? tr("微信号", "WeChat ID")
              : form.contact_method === "email"
                ? tr("电子邮箱", "Email address")
                : tr("联系电话", "Phone number")
          }}<input
            v-model.trim="form.contact"
            name="contact"
            :type="
              form.contact_method === 'email'
                ? 'email'
                : form.contact_method === 'phone'
                  ? 'tel'
                  : 'text'
            "
            :autocomplete="
              form.contact_method === 'email'
                ? 'email'
                : form.contact_method === 'phone'
                  ? 'tel'
                  : 'off'
            "
            required
            minlength="3"
            maxlength="180"
            :placeholder="
              tr(
                '仅用于联系并确认这次安排',
                'Only used to arrange this request',
              )
            " /></label
        ><label class="field"
          >{{ tr("想提前告诉我们的事（选填）", "Anything else? (optional)")
          }}<textarea
            v-model.trim="form.notes"
            name="notes"
            rows="3"
            maxlength="1500"
            :placeholder="
              kind === 'visit'
                ? tr(
                    '第一次拼豆、想做的图案、同行安排，或其他需要……',
                    'Your first visit, a pattern you have in mind, or anything you need…',
                  )
                : tr(
                    '色号、数量、喜欢的款式、希望自提的时间……',
                    'Colour codes, preferred styles, quantities or a pickup date…',
                  )
            "
          ></textarea>
        </label>
      </div>
      <div class="honeypot" aria-hidden="true">
        <label
          >Website<input
            v-model="form.website"
            tabindex="-1"
            autocomplete="off"
        /></label>
      </div>
      <div class="request-summary">
        <h3>{{ tr("提交前，再看一眼", "Your request at a glance") }}</h3>
        <p v-for="line in summary" :key="line">{{ line }}</p>
        <p class="fine-print">
          {{
            tr(
              "价格、时间及具体安排，以店主后续确认为准。",
              "Prices, timing and details are subject to the host’s confirmation.",
            )
          }}
        </p>
      </div>
      <label class="consent"
        ><input v-model="form.consent" type="checkbox" required /><span>{{
          tr(
            "我理解这是一份待确认的意向，并同意店主使用上述联系方式沟通本次安排。",
            "I understand this is a request, and agree that the host may use my contact details to arrange this visit or pickup.",
          )
        }}</span></label
      >
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <button
        class="button button-primary submit-button"
        :disabled="sending || disabled"
        type="submit"
      >
        {{
          sending
            ? tr("正在提交…", "Sending…")
            : kind === "visit"
              ? tr("提交预约意向", "Send visit request")
              : tr("提交自提询单", "Send pickup inquiry")
        }}<PhArrowRight v-if="!sending" />
      </button>
      <p class="fine-print privacy-note">
        {{
          tr(
            "联系信息仅供店主处理本次请求。提交后无需在线付款；收到确认后再到店。",
            "Contact details are only used by the host to handle this request. No online payment is required. Please wait for confirmation before visiting.",
          )
        }}
      </p>
    </fieldset>
  </form>
</template>
