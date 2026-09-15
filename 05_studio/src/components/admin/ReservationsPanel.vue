<script setup lang="ts">
import CopyContact from "../CopyContact.vue";
import OwnerDeliveryStatus from './OwnerDeliveryStatus.vue';
import OfferLabel from '../../visit/OfferLabel.vue';
import { contentModule } from "../../content-store";
const copyText = contentModule("components-admin-ReservationsPanel", copyTextDefault);

import copyTextDefault from "../../content/components-admin-ReservationsPanel.json";
import { say } from "../../state";

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
import ReservationAvailability from "./ReservationAvailability.vue";
import ReservationSettings from "./ReservationSettings.vue";
import ReservationTimetable from './ReservationTimetable.vue';
import timetableWords from '../../content/reservation-timetable.json';
import { formatCopy } from '../../state';
const timetableCopy=contentModule('reservation-timetable',timetableWords);
import { walletCopy,duration } from '../../wallet';
import { hoursInput,minutesFromHours } from '../../time-units';
import CustomerIdentity from '../CustomerIdentity.vue';
import type {WalletAccount} from '../../wallet';
import { useRoute, useRouter } from 'vue-router';
import { messageCopy } from '../../messaging';
type Entry = Reservation & { payload: ReservationPayload; staff_note: string;owner_id:string;deleted_at:string|null };
const props = defineProps<{ active: boolean; calendar?: boolean }>();
const at=ref(''),timetableRevision=ref(0);
const { request } = useDesk();
const router=useRouter(),route=useRoute();
const deleted=ref(false),deleting=ref(false),deleteReason=ref(''),publicNote=ref('');
const actualHours=ref<number|string>(''),actualGuests=ref<number|''>('');
const customer=ref<WalletAccount>();let customerSequence=0;
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
  pending: say(copyText.pending_5c3b18),
  confirmed: say(copyText.confirmed_b1c92b),
  completed: say(copyText.completed_ff8af6),
  cancelled: say(copyText.cancelled_8c9064),
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
      deleted:String(deleted.value),
    });
    if (day.value) query.set("day", day.value);
    if(day.value&&at.value&&!deleted.value)query.set('at',at.value);
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
    timetableRevision.value++;
  } catch (e) {
    if (seq === sequence) error.value = (e as Error).message;
  } finally {
    if (seq === sequence) busy.value = false;
  }
}
function inspect(item: Entry) {
  customer.value=undefined;const identitySequence=++customerSequence;
  if(item.owner_id)void request<{account:WalletAccount}>('/manage/members/'+encodeURIComponent(item.owner_id)).then(data=>{if(identitySequence===customerSequence)customer.value=data.account;}).catch(()=>{});
  entry.value = item;
  nextStatus.value = item.status;
  note.value = item.staff_note;
  actualHours.value=hoursInput(item.actual_minutes);actualGuests.value=item.actual_guests??'';
  publicNote.value=item.public_note||'';deleting.value=false;deleteReason.value='';
  saveError.value = "";
  open.value = true;
}
let inspectSequence=0;
async function inspectBooking(id:string){
 const n=++inspectSequence;saveError.value='';
 try{const data=await request<{items:Entry[]}>('/manage/reservations?search='+encodeURIComponent(id));if(n===inspectSequence&&props.active){const found=data.items.find(item=>item.id===id);if(found)inspect(found);}}
 catch(e){if(n===inspectSequence)error.value=(e as Error).message;}
}
onBeforeUnmount(()=>{inspectSequence++;customerSequence++;});
async function save() {
  if (!entry.value || saving.value) return;
  const completing=nextStatus.value==='completed',actualMinutes=completing?minutesFromHours(actualHours.value):null;
  if(completing&&(actualMinutes===null||actualMinutes<1||actualMinutes>1440||!Number.isInteger(actualGuests.value)||Number(actualGuests.value)<1||Number(actualGuests.value)>99)){
    saveError.value=say(walletCopy.wallet_actual_hours_details_required);return;
  }
  saving.value = true;
  saveError.value = "";
  try {
    await request("/manage/reservations/" + entry.value.id, {
      method: "PATCH",
      body: JSON.stringify({
        status: nextStatus.value,
        staff_note: note.value,
        version: entry.value.version,
        ...(completing?{actual_minutes:actualMinutes,actual_guests:actualGuests.value}:{}),
        public_note:publicNote.value,
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
watch(nextStatus,()=>{saveError.value='';});
async function removeOrRestore(){
  if(!entry.value||saving.value||!deleteReason.value.trim())return;
  saving.value=true;saveError.value='';
  try{await request('/manage/reservations/'+entry.value.id+(entry.value.deleted_at?'/restore':''),{
    method:entry.value.deleted_at?'POST':'DELETE',body:JSON.stringify({version:entry.value.version,reason:deleteReason.value.trim()})});
    open.value=false;await load();
  }catch(e){saveError.value=(e as Error).message;}finally{saving.value=false;}
}
function openWallet(){if(!entry.value?.owner_id)return;open.value=false;void router.push({path:'/manage',query:{view:'members',member:entry.value.owner_id,booking:entry.value.id}});}
function openMessages(){if(!entry.value)return;open.value=false;void router.push({path:'/manage',query:{view:'messages',reservation:entry.value.id}});}
watch(()=>[props.active,route.query.booking],()=>{if(props.active&&typeof route.query.booking==='string')void inspectBooking(route.query.booking);},{immediate:true});
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
watch([status, day,deleted,at], () => {
  if(deleted.value||!day.value)at.value='';
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
          {{ say(copyText.a_little_care_for_every_visit_4e8c5b) }}
        </p>
        <h1>
          {{
            calendar
              ? say(copyText.reservation_calendar_79ec67)
              : say(copyText.studio_reservations_4896a2)
          }}
        </h1>
        <p>
          {{ say(copyText.review_the_time_and_group_size_then_6af55f) }}
        </p>
      </div>
      <button class="desk-button secondary" :disabled="busy" @click="load">
        <PhArrowClockwise :class="{ spinning: busy }" />{{
          say(copyText.refresh_5efb82)
        }}
      </button>
    </header>
    <OwnerDeliveryStatus :active="active" />
    <ReservationAvailability v-if="calendar" :active="active" />
    <div v-if="!calendar" class="reservation-desk-metrics">
      <button @click="status = 'pending'">
        <PhClock /><span>{{ say(copyText.waiting_for_you_41a255) }}</span
        ><strong>{{ counts.pending || 0 }}</strong></button
      ><button @click="status = 'confirmed'">
        <PhCalendarDots /><span>{{
          say(copyText.confirmed_visits_305c18)
        }}</span
        ><strong>{{ counts.confirmed || 0 }}</strong></button
      ><button @click="status = 'completed'">
        <PhCheck /><span>{{ say(copyText.completed_visits_1cdc52) }}</span
        ><strong>{{ counts.completed || 0 }}</strong>
      </button>
    </div>
    <div
      v-if="calendar"
      class="reservation-desk-days"
      :aria-label="say(copyText.choose_reservation_date_ae55e6)"
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
    <ReservationSettings :active="active" @saved="load" />
    <ReservationTimetable v-if="!deleted" :active="active" :refresh-key="timetableRevision" :selected-date="day" :selected-time="at" @inspect="inspectBooking" @select="value=>{day=value.date;at=value.at;status='all';search='';}"/>
    <div v-if="at&&day&&!deleted" class="timetable-filter"><span>{{formatCopy(timetableCopy.selected,{v0:prettyDate(day),v1:at})}}</span><button class="desk-link" @click="at=''">{{say(timetableCopy.clear)}}</button></div>
    <div class="reservation-deleted-toggle" role="group" :aria-label="say(walletCopy.deleted)"><button class="desk-link" :aria-pressed="!deleted" @click="deleted=false">{{say(walletCopy.active)}}</button><button class="desk-link" :aria-pressed="deleted" @click="deleted=true">{{say(walletCopy.deleted)}}</button></div>
    <div class="reservation-desk-filters">
      <label class="desk-field"
        >{{ say(copyText.status_4434e2)
        }}<select v-model="status">
          <option value="all">{{ say(copyText.all_902ec4) }}</option>
          <option v-for="(label, key) in labels" :key="key" :value="key">
            {{ label }}
          </option>
        </select></label
      ><label class="desk-field"
        >{{ say(copyText.visit_date_270402)
        }}<input v-model="day" type="date" /></label
      ><label class="desk-field"
        >{{ say(copyText.name_or_reference_c2f162)
        }}<input v-model.trim="search" type="search" /></label
      ><button
        class="desk-link"
        @click="
          status = 'all';
          day = '';
          search = '';
          at = '';
        "
      >
        {{ say(copyText.clear_filters_0a6c6f) }}
      </button>
    </div>
    <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
    <p v-if="busy && !items.length" class="reservation-loading" role="status">
      {{ say(copyText.loading_reservations_adb99a) }}
    </p>
    <div v-else-if="!items.length" class="reservation-desk-empty">
      <PhCalendarDots :size="35" weight="light" />
      <h2>{{ say(copyText.no_reservations_here_yet_1ffd1c) }}</h2>
      <p>
        {{ say(copyText.when_a_guest_submits_a_request_you_d10e4b) }}
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
            {{ item.booking.guests }} {{ say(copyText.guests_24bfb5) }}</small
          >
          <small v-if="item.offer"><OfferLabel :offer="item.offer"/></small>
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
        {{ say(copyText.previous_94c671) }}</button
      ><span
        >{{ say(copyText.total_74beb1) }} {{ total }}
        {{ say(copyText.reservations_718784) }}</span
      ><button
        class="desk-button secondary"
        :disabled="page * 30 >= total || busy"
        @click="
          page++;
          load();
        "
      >
        {{ say(copyText.next_05635e) }}
      </button>
    </div>
    <SlideOver
      v-model="open"
      :title="entry?.name || say(copyText.reservation_details_d248c4)"
      :subtitle="entry?.id"
      :busy="saving"
      ><template v-if="entry"
        ><CustomerIdentity v-if="customer" :customer="customer"/><dl class="reservation-desk-summary">
          <div>
            <dt>{{ say(copyText.visit_f29981) }}</dt>
            <dd>
              {{ prettyDate(entry.booking.date) }}<br />{{
                entry.booking.start
              }}–{{ entry.booking.end }}
            </dd>
          </div>
          <div>
            <dt>{{ say(copyText.experience_and_guests_369b9e) }}</dt>
            <dd>
              {{
                entry.booking.plan === "day"
                  ? say(copyText.day_visit_aad886)
                  : say(copyText.hourly_visit_681491)
              }}
              · {{ entry.booking.guests }} {{ say(copyText.guests_24bfb5) }}
              <p v-if="entry.offer"><OfferLabel :offer="entry.offer"/></p>
            </dd>
          </div>
          <div>
            <dt>{{ say(copyText.contact_b87aac) }}</dt>
            <dd>
              <span v-if="!entry.payload.contact">{{say(copyText.returning_contact_omitted)}}</span>
              <template v-else>
              {{
                entry.payload.contact_method === "wechat"
                  ? say(copyText.wechat_2941d2)
                  : entry.payload.contact_method === "phone"
                    ? say(copyText.phone_ac7a62)
                    : entry.payload.contact_method === "email"
                      ? say(copyText.email_8501ec)
                      : say(copyText.other_8b6752)
              }}：<CopyContact v-if="entry.payload.contact_method==='wechat'" :value="entry.payload.contact" /><span v-else>{{ entry.payload.contact }}</span>
              </template>
            </dd>
          </div>
          <div v-if="entry.payload.notes">
            <dt>{{ say(copyText.guest_note_a101f4) }}</dt>
            <dd>{{ entry.payload.notes }}</dd>
          </div>
        </dl>
        <button v-if="entry.owner_id" class="desk-button secondary" @click="openWallet">{{say(walletCopy.open_wallet)}}<PhArrowRight/></button>
        <button v-if="!entry.deleted_at" class="desk-button secondary" @click="openMessages">{{say(messageCopy.new_conversation)}}<PhArrowRight/></button>
        <div v-if="!entry.deleted_at" class="reservation-attendance">
          <p class="fine-print">{{say(walletCopy.booked)}} · {{duration(entry.booked_minutes)}}</p>
          <label class="desk-field">{{say(walletCopy.public_note)}}<textarea v-model="publicNote" rows="3" maxlength="600" :disabled="saving"/></label>
        </div>
        <p class="fine-print">
          {{
            say(copyText.saving_updates_the_guests_result_page_please_6140a1)
          }}
        </p>
        <label class="desk-field"
          >{{ say(copyText.update_reservation_status_0ddee8)
          }}<select
            v-model="nextStatus"
            :disabled="saving||!!entry.deleted_at"
            :aria-label="say(copyText.update_reservation_status_0ddee8)"
          >
            <option v-for="(label, key) in labels" :key="key" :value="key">
              {{ label }}
            </option>
          </select></label>
        <template v-if="nextStatus==='completed'&&!entry.deleted_at">
          <div class="wallet-input-grid"><label class="desk-field">{{say(walletCopy.actual_hours)}}<input v-model="actualHours" type="number" inputmode="decimal" min="0" max="24" step="any" :disabled="saving"/></label><label class="desk-field">{{say(walletCopy.actual_guests)}}<input v-model.number="actualGuests" type="number" min="1" max="99" step="1" :disabled="saving"/></label></div>
          <p class="wallet-rule">{{say(walletCopy.attendance_help)}}</p>
        </template>
        <label class="desk-field"
          >{{ say(copyText.staff_note_private_53d294)
          }}<textarea
            v-model="note"
            rows="4"
            maxlength="1500"
            :disabled="saving||!!entry.deleted_at"
          />
        </label>
        <div class="reservation-delete">
          <button class="desk-button secondary" :disabled="saving" @click="deleting=!deleting">{{say(entry.deleted_at?walletCopy.restore:walletCopy.delete)}}</button>
          <form v-if="deleting" @submit.prevent="removeOrRestore"><p class="wallet-rule">{{say(walletCopy.delete_help)}}</p><label class="desk-field">{{say(walletCopy.deletion_reason)}}<textarea v-model="deleteReason" rows="2" minlength="1" maxlength="600" required :disabled="saving"/></label><button class="desk-button secondary" :disabled="saving||!deleteReason.trim()">{{say(entry.deleted_at?walletCopy.restore:walletCopy.confirm_delete)}}</button></form>
        </div>
        <p v-if="saveError" class="desk-error" role="alert">
          {{ saveError }}
        </p></template
      ><template #footer
        ><button
          class="desk-button secondary"
          :disabled="saving"
          @click="open = false"
        >
          {{ say(copyText.close_accb35) }}</button
        ><button v-if="!entry?.deleted_at" class="desk-button primary" :disabled="saving" @click="save">
          {{
            saving
              ? say(copyText.saving_9a40ec)
              : say(copyText.save_arrangement_87aa75)
          }}<PhCheck /></button></template
    ></SlideOver>
  </section>
</template>
