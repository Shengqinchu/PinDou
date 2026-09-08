<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import {
  PhCheck,
  PhClock,
  PhArrowRight,
  PhArrowClockwise,
} from "@phosphor-icons/vue";
import { commerceApi } from "../commerce";
import { prettyDate, tr, wechat } from "../state";
import type { Reservation } from "../reservations";
const route = useRoute(),
  result = ref<Reservation>(),
  busy = ref(false),
  error = ref("");
let timer: ReturnType<typeof setInterval>,
  alive = true;
async function refresh() {
  if (busy.value) return;
  busy.value = true;
  try {
    const data = await commerceApi<Reservation>(
      "/reservations/" + encodeURIComponent(String(route.params.id)),
    );
    if (alive) {
      result.value = data;
      error.value = "";
    }
  } catch (e) {
    if (alive) error.value = (e as Error).message;
  } finally {
    if (alive) busy.value = false;
  }
}
function visible() {
  if (!document.hidden) refresh();
}
onMounted(() => {
  refresh();
  timer = setInterval(() => {
    if (result.value?.status === "pending") visible();
  }, 15000);
  window.addEventListener("pageshow", visible);
  document.addEventListener("visibilitychange", visible);
});
onBeforeUnmount(() => {
  alive = false;
  clearInterval(timer);
  window.removeEventListener("pageshow", visible);
  document.removeEventListener("visibilitychange", visible);
});
</script>
<template>
  <section class="reservation-receipt container">
    <template v-if="result"
      ><div class="reservation-seal">
        <PhCheck
          v-if="['confirmed', 'completed'].includes(result.status)"
          :size="33"
        /><PhClock v-else :size="33" />
      </div>
      <p class="vision-eyebrow">{{ result.id }}</p>
      <h1 v-if="result.status === 'pending'">
        {{ tr("已提交预约，", "Your request is in.") }}<br /><em>{{
          tr("等待店主确认", "The host will confirm it.")
        }}</em>
      </h1>
      <h1 v-else-if="result.status === 'confirmed'">
        {{ tr("预约成功，", "Your visit is confirmed.") }}<br /><em>{{
          tr("等你来玩！", "See you at the studio!")
        }}</em>
      </h1>
      <h1 v-else-if="result.status === 'completed'">
        {{ tr("谢谢你来，", "Thank you for coming.") }}<br /><em>{{
          tr("下次再一起拼。", "Let's make again soon.")
        }}</em>
      </h1>
      <h1 v-else>
        {{ tr("这次预约已取消", "This reservation was cancelled") }}
      </h1>
      <p v-if="result.status === 'pending'">
        {{
          tr(
            "店主会尽快查看安排，确认后即预约成功。把这页留在当前浏览器，可以随时查看状态。",
            "The host will review your plans as soon as possible. Your visit is booked once confirmed. Keep this page in the same browser to check its status.",
          )
        }}
      </p>
      <dl>
        <div>
          <dt>{{ tr("客人", "Guest") }}</dt>
          <dd>{{ result.name }}</dd>
        </div>
        <div>
          <dt>{{ tr("到店时间", "Visit time") }}</dt>
          <dd>
            {{ prettyDate(result.booking.date) }}<br />{{
              result.booking.start
            }}–{{ result.booking.end }} ·
            {{ tr("汉密尔顿当地时间", "Hamilton local time") }}
          </dd>
        </div>
        <div>
          <dt>{{ tr("同行人数", "Guests") }}</dt>
          <dd>{{ result.booking.guests }} {{ tr("人", "guests") }}</dd>
        </div>
        <div>
          <dt>{{ tr("体验", "Experience") }}</dt>
          <dd>
            {{
              result.booking.plan === "day"
                ? tr("全天体验", "Day visit")
                : tr("按时体验", "Hourly visit")
            }}
          </dd>
        </div>
      </dl>
      <p>
        {{
          tr(
            "欢迎来玩，先看看小屋的到访和停车信息吧。",
            "We look forward to seeing you. Take a look at the studio and parking details before you come.",
          )
        }}
      </p>
      <RouterLink class="button button-primary" to="/details"
        >{{ tr("拼豆铺详细信息", "Studio details") }}<PhArrowRight
      /></RouterLink>
    </template>
    <p v-else-if="busy" role="status">
      {{ tr("正在查看预约……", "Loading your reservation…") }}
    </p>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <button type="button" class="text-link" :disabled="busy" @click="refresh">
      <PhArrowClockwise :class="{ spinning: busy }" />{{
        tr("刷新预约状态", "Refresh reservation")
      }}
    </button>
    <p class="fine-print">
      {{
        tr(
          "如需调整安排，请联系店主。微信号：",
          "For changes, contact the host on WeChat: ",
        )
      }}{{ wechat }}
    </p>
  </section>
</template>
