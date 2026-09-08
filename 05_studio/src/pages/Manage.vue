<script setup lang="ts">
import "../styles/desk.css";
import { onMounted, reactive, ref } from "vue";
import { PhArrowRight, PhArrowClockwise, PhFlower } from "@phosphor-icons/vue";
import { prettyDate, products, tr, media } from "../state";
import { commerceApi as api, CommerceError } from "../commerce";
import CommerceManager from "../components/CommerceManager.vue";

type Entry = {
  id: string;
  created_at: string;
  kind: string;
  status: string;
  staff_note: string;
  version: number;
  next_status: string;
  next_note: string;
  payload: {
    name: string;
    contact_method: string;
    contact: string;
    notes: string;
    booking: {
      date: string;
      start: string;
      end: string;
      guests: number;
      plan: string;
    } | null;
    items: { id: string; quantity: number }[];
  };
};
const token = ref("");
const login = reactive({ username: "", password: "" });
const entries = ref<Entry[]>([]);
const status = ref("pending");
const error = ref("");
const busy = ref(false);
const total = ref(0);
const page = ref(1);
const statusLabels = () => ({
  pending: tr("待确认", "Pending"),
  confirmed: tr("已确认", "Confirmed"),
  completed: tr("已完成", "Completed"),
  cancelled: tr("已取消", "Cancelled"),
});
function saveToken(value: string) {
  token.value = value;
  try {
    sessionStorage.setItem("puppy-studio-admin", value);
  } catch {
    /* Session remains in memory. */
  }
}
onMounted(() => {
  try {
    token.value = sessionStorage.getItem("puppy-studio-admin") || "";
  } catch {
    /* Sign in normally. */
  }
  if (token.value) load();
});
async function signIn() {
  busy.value = true;
  error.value = "";
  try {
    const response = await fetch("/api/v1/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(login),
    });
    const result = await response.json();
    const access = result.token || result.data?.token;
    if (!response.ok || typeof access !== "string")
      throw new Error(
        tr(
          "登录失败，请检查现有后台账号和密码。",
          "Sign-in failed. Check your existing administrator credentials.",
        ),
      );
    saveToken(access);
    login.password = "";
    await load();
  } catch (e) {
    if (e instanceof CommerceError && (e.status === 401 || e.status === 403))
      saveToken("");
    error.value =
      e instanceof Error
        ? e.message
        : tr("暂时无法登录。", "Could not sign in.");
  } finally {
    busy.value = false;
  }
}
async function load() {
  busy.value = true;
  error.value = "";
  try {
    const result = await api<{ items: Entry[]; total: number }>(
      `/manage/requests?status=${status.value}&page=${page.value}`,
      { headers: { Authorization: `Bearer ${token.value}` } },
    );
    entries.value = result.items.map((entry) => ({
      ...entry,
      next_status: entry.status,
      next_note: entry.staff_note,
    }));
    total.value = result.total;
  } catch (e) {
    if (e instanceof CommerceError && (e.status === 401 || e.status === 403))
      saveToken("");
    error.value =
      e instanceof Error
        ? e.message
        : tr("加载失败。", "Could not load requests.");
  } finally {
    busy.value = false;
  }
}
async function save(entry: Entry) {
  busy.value = true;
  error.value = "";
  try {
    await api(`/manage/requests/${entry.id}`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token.value}` },
      body: JSON.stringify({
        status: entry.next_status,
        staff_note: entry.next_note,
        version: entry.version,
      }),
    });
    await load();
  } catch {
    error.value = tr(
      "未能保存。记录可能已在另一处更新，请刷新核对后重试。",
      "Could not save. This request may have changed elsewhere. Refresh and check before retrying.",
    );
  } finally {
    busy.value = false;
  }
}
function signOut() {
  saveToken("");
  entries.value = [];
  error.value = "";
}
function statusLabel(value: string): string {
  const labels: Record<string, string> = statusLabels();
  return labels[value] || value;
}
</script>
<template>
  <div v-if="!token" class="host-login">
    <div class="host-login-story">
      <RouterLink to="/" class="desk-brand"
        ><PhFlower :size="32" weight="light" /><span
          >{{ tr("小狗拼豆铺", "Pindo Puppy") }}<small>{{
            tr("小狗拼豆铺", "A LITTLE CREATIVE STUDIO")
          }}</small></span
        ></RouterLink
      ><img
        :src="media('studio-04')"
        :alt="tr('小狗拼豆铺工作室', 'Pindo Puppy studio')"
      />
      <div>
        <p>
          {{
            tr(
              "每一份期待，值得好好照顾。",
              "Every little plan deserves a little care.",
            )
          }}
        </p>
        <span>{{ tr("汉密尔顿 · 安大略省", "Hamilton, Ontario") }}</span>
      </div>
    </div>
    <div class="host-login-form">
      <form @submit.prevent="signIn">
        <span class="desk-eyebrow">{{
          tr("欢迎回到小狗拼豆铺", "WELCOME BACK TO YOUR STUDIO")
        }}</span>
        <h1>{{ tr("你好，店主。", "Hello, studio owner.") }}</h1>
        <p>
          {{
            tr(
              "登录后，照看订单、安排座位，再给小店添一点可爱。",
              "Sign in to look after orders, arrange seats and add something lovely to your little shop.",
            )
          }}
        </p>
        <label class="desk-field"
          >{{ tr("管理员账号", "Administrator account")
          }}<input
            v-model.trim="login.username"
            name="username"
            autocomplete="username"
            required /></label
        ><label class="desk-field"
          >{{ tr("密码", "Password")
          }}<input
            v-model="login.password"
            name="password"
            type="password"
            autocomplete="current-password"
            required
        /></label>
        <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
        <button class="desk-button primary" :disabled="busy">
          {{
            busy
              ? tr("正在登录…", "Signing in…")
              : tr("进入工作台", "Open studio desk")
          }}<PhArrowRight />
        </button>
        <p class="login-note">
          {{
            tr(
              "使用现有拼豆后台的管理员账号。",
              "Use your existing PinDou administrator account.",
            )
          }}
        </p>
        <RouterLink to="/" class="desk-link"
          >{{ tr("返回网站", "Back to the website") }}<PhArrowRight
        /></RouterLink>
      </form>
    </div>
  </div>
  <CommerceManager v-else :token="token" @logout="signOut" @expired="signOut"
    ><template #legacy>
      <div class="manage-toolbar">
        <label class="field"
          >{{ tr("请求状态", "Request status")
          }}<select
            v-model="status"
            @change="
              page = 1;
              load();
            "
          >
            <option value="all">{{ tr("全部", "All requests") }}</option>
            <option
              v-for="(label, value) in statusLabels()"
              :key="value"
              :value="value"
            >
              {{ label }}
            </option>
          </select></label
        ><button class="button button-outline" :disabled="busy" @click="load">
          <PhArrowClockwise />{{ tr("刷新", "Refresh") }}</button
        ><span>{{ total }} {{ tr("条请求", "requests") }}</span>
      </div>
      <p class="fine-print">
        {{
          tr(
            "保存状态不会自动通知顾客。请使用请求中留下的联系方式确认，内部备注仅店主可见。",
            "Saving a status does not notify the guest. Contact them using the details they provided. Staff notes are private.",
          )
        }}
      </p>
      <p v-if="!entries.length && !busy && !error" class="empty-selection">
        {{ tr("这里暂时没有请求。", "No requests here yet.") }}
      </p>
      <article v-for="entry in entries" :key="entry.id" class="manage-entry">
        <div class="manage-entry-title">
          <h2>
            {{ entry.payload.name }}
            <small>{{
              entry.kind === "visit"
                ? tr("到店预约", "Visit")
                : tr("自提询单", "Pickup")
            }}</small>
          </h2>
          <span class="status-label">{{ statusLabel(entry.status) }}</span>
        </div>
        <p class="fine-print">
          {{ entry.id }} ·
          {{
            new Date(entry.created_at).toLocaleString("en-CA", {
              timeZone: "America/Toronto",
            })
          }}
          (Hamilton)
        </p>
        <p>
          {{ entry.payload.contact_method }}:
          <strong>{{ entry.payload.contact }}</strong>
        </p>
        <p v-if="entry.payload.booking">
          {{ prettyDate(entry.payload.booking.date) }} ·
          {{ entry.payload.booking.start }}–{{ entry.payload.booking.end }} ·
          {{ entry.payload.booking.guests }} {{ tr("人", "guests") }} ·
          {{ entry.payload.booking.plan }}
        </p>
        <p v-for="item in entry.payload.items" :key="item.id">
          {{
            products.find((p) => p.id === item.id)?.[
              tr("zh", "en") as "zh" | "en"
            ] || item.id
          }}
          × {{ item.quantity }}
        </p>
        <p v-if="entry.payload.notes" class="customer-notes">
          {{ entry.payload.notes }}
        </p>
        <div class="form-grid">
          <label class="field"
            >{{ tr("更新状态", "Update status")
            }}<select v-model="entry.next_status">
              <option
                v-for="(label, value) in statusLabels()"
                :key="value"
                :value="value"
              >
                {{ label }}
              </option>
            </select></label
          ><label class="field"
            >{{ tr("内部备注", "Staff note")
            }}<input
              v-model="entry.next_note"
              maxlength="1500"
              :placeholder="
                tr(
                  '确认的费用、时间或处理记录',
                  'Agreed price, timing or follow-up',
                )
              "
          /></label>
        </div>
        <button
          class="button button-outline"
          @click="save(entry)"
          :disabled="busy"
        >
          {{ tr("保存安排", "Save arrangement") }}
        </button>
      </article>
      <div v-if="total > 50" class="pagination">
        <button
          :disabled="page <= 1 || busy"
          @click="
            page--;
            load();
          "
        >
          {{ tr("上一页", "Previous") }}</button
        ><span>{{ page }}</span
        ><button
          :disabled="page * 50 >= total || busy"
          @click="
            page++;
            load();
          "
        >
          {{ tr("下一页", "Next") }}
        </button>
      </div>

      <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
    </template></CommerceManager
  >
</template>
