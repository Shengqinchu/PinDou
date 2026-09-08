<script setup lang="ts">
import BrandMotif from "../components/BrandMotif.vue";
import copyText from "../content/pages-Manage.json";
import { say } from "../state";

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
  pending: say(copyText.pending_5c3b18),
  confirmed: say(copyText.confirmed_b1c92b),
  completed: say(copyText.completed_ff8af6),
  cancelled: say(copyText.cancelled_8c9064),
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
        say(
          copyText.signin_failed_check_your_existing_administrator_credentials_2e7049,
        ),
      );
    saveToken(access);
    login.password = "";
    await load();
  } catch (e) {
    if (e instanceof CommerceError && (e.status === 401 || e.status === 403))
      saveToken("");
    error.value =
      e instanceof Error ? e.message : say(copyText.could_not_sign_in_4e21bb);
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
        : say(copyText.could_not_load_requests_bd1427);
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
    error.value = say(copyText.could_not_save_this_request_may_have_c04e66);
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
        ><BrandMotif /><span
          >{{ say(copyText.pindo_puppy_08aa61)
          }}<small>{{
            say(copyText.a_little_creative_studio_72779b)
          }}</small></span
        ></RouterLink
      ><img
        :src="media('studio-04')"
        :alt="say(copyText.pindo_puppy_studio_98f0bc)"
      />
      <div>
        <p>
          {{ say(copyText.every_little_plan_deserves_a_little_care_12f43a) }}
        </p>
        <span>{{ say(copyText.hamilton_ontario_1f281c) }}</span>
      </div>
    </div>
    <div class="host-login-form">
      <form @submit.prevent="signIn">
        <span class="desk-eyebrow">{{
          say(copyText.welcome_back_to_your_studio_5785ce)
        }}</span>
        <h1>{{ say(copyText.hello_studio_owner_3dd59b) }}</h1>
        <p>
          {{ say(copyText.sign_in_to_look_after_orders_arrange_961ef3) }}
        </p>
        <label class="desk-field"
          >{{ say(copyText.administrator_account_61308e)
          }}<input
            v-model.trim="login.username"
            name="username"
            autocomplete="username"
            required /></label
        ><label class="desk-field"
          >{{ say(copyText.password_db2477)
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
              ? say(copyText.signing_in_f2f0b2)
              : say(copyText.open_studio_desk_d62008)
          }}<PhArrowRight />
        </button>
        <p class="login-note">
          {{
            say(copyText.use_your_existing_pindou_administrator_account_ac1b0a)
          }}
        </p>
        <RouterLink to="/" class="desk-link"
          >{{ say(copyText.back_to_the_website_19fd8b) }}<PhArrowRight
        /></RouterLink>
      </form>
    </div>
  </div>
  <CommerceManager v-else :token="token" @logout="signOut" @expired="signOut"
    ><template #legacy>
      <div class="manage-toolbar">
        <label class="field"
          >{{ say(copyText.request_status_f5815f)
          }}<select
            v-model="status"
            @change="
              page = 1;
              load();
            "
          >
            <option value="all">{{ say(copyText.all_requests_26d41f) }}</option>
            <option
              v-for="(label, value) in statusLabels()"
              :key="value"
              :value="value"
            >
              {{ label }}
            </option>
          </select></label
        ><button class="button button-outline" :disabled="busy" @click="load">
          <PhArrowClockwise />{{ say(copyText.refresh_5efb82) }}</button
        ><span>{{ total }} {{ say(copyText.requests_be865b) }}</span>
      </div>
      <p class="fine-print">
        {{ say(copyText.saving_a_status_does_not_notify_the_c16998) }}
      </p>
      <p v-if="!entries.length && !busy && !error" class="empty-selection">
        {{ say(copyText.no_requests_here_yet_ce9b61) }}
      </p>
      <article v-for="entry in entries" :key="entry.id" class="manage-entry">
        <div class="manage-entry-title">
          <h2>
            {{ entry.payload.name }}
            <small>{{
              entry.kind === "visit"
                ? say(copyText.visit_111717)
                : say(copyText.pickup_eb8e71)
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
          {{ entry.payload.booking.guests }} {{ say(copyText.guests_24bfb5) }} ·
          {{ entry.payload.booking.plan }}
        </p>
        <p v-for="item in entry.payload.items" :key="item.id">
          {{
            products.find((p) => p.id === item.id)?.[
              say(copyText.en_1ac02c) as "zh" | "en"
            ] || item.id
          }}
          × {{ item.quantity }}
        </p>
        <p v-if="entry.payload.notes" class="customer-notes">
          {{ entry.payload.notes }}
        </p>
        <div class="form-grid">
          <label class="field"
            >{{ say(copyText.update_status_89e527)
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
            >{{ say(copyText.staff_note_0d849e)
            }}<input
              v-model="entry.next_note"
              maxlength="1500"
              :placeholder="
                say(copyText.agreed_price_timing_or_followup_8826ab)
              "
          /></label>
        </div>
        <button
          class="button button-outline"
          @click="save(entry)"
          :disabled="busy"
        >
          {{ say(copyText.save_arrangement_87aa75) }}
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
          {{ say(copyText.previous_94c671) }}</button
        ><span>{{ page }}</span
        ><button
          :disabled="page * 50 >= total || busy"
          @click="
            page++;
            load();
          "
        >
          {{ say(copyText.next_05635e) }}
        </button>
      </div>

      <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
    </template></CommerceManager
  >
</template>
