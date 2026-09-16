<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { useDesk } from '../../admin';
import { CommerceError } from '../../commerce';
import { adminVisitCopy as copy, visitSourceLabel, visitStatusLabel } from '../../admin-visits';
import { walletCopy, duration, type WalletAccount } from '../../wallet';
import { say, formatCopy, locale, hamiltonDate, plusDays, prettyDate } from '../../state';
import { readSession, saveSession, validSelection, type Reservation, type ReservationCalendar } from '../../reservations';
import { minutesFromHours } from '../../time-units';

const props = defineProps<{ account: WalletAccount; disabled?: boolean }>();
const emit = defineEmits<{ busy: [value: boolean]; recorded: [] }>();
const { request } = useDesk();
type Draft = { kind: 'booking' | 'backfill'; date: string; start: string; end: string; plan: 'hourly' | 'day'; guests: number; status: 'pending' | 'confirmed'; actualHours: number | string; actualGuests: number | string; reason: string; publicNote: string; staffNote: string };
type Pending = { key: string; body: Record<string, unknown> };
const storageKey = `studio-admin-visit-v1:${props.account.owner_id}`;
const stored = readSession<{ draft: Draft; open: boolean; pending: Pending | null }>(storageKey);
const draft = ref<Draft>(stored?.draft || { kind: 'booking', date: plusDays(hamiltonDate(), 1), start: '10:00', end: '12:00', plan: 'hourly', guests: 1, status: 'pending', actualHours: '', actualGuests: '', reason: '', publicNote: '', staffNote: '' });
const formOpen = ref(stored?.open || false), pending = ref<Pending | null>(stored?.pending || null);
const items = ref<Reservation[]>([]), page = ref(1), total = ref(0), loading = ref(false), listError = ref('');
const saving = ref(false), error = ref(''), saved = ref(''), calendar = ref<ReservationCalendar>(), calendarBusy = ref(false), calendarError = ref('');
const frozen = computed(() => props.disabled || saving.value || !!pending.value);
const times = Array.from({ length: 48 }, (_, i) => `${String(Math.floor(i / 2)).padStart(2, '0')}:${i % 2 ? '30' : '00'}`);
const booking = computed(() => ({ date: draft.value.date, start: draft.value.start, end: draft.value.end, plan: draft.value.plan, guests: Number(draft.value.kind === 'backfill' ? draft.value.actualGuests : draft.value.guests) }));
const available = computed(() => validSelection(calendar.value || null, booking.value));
let listSequence = 0, calendarSequence = 0;
async function load() {
  const n = ++listSequence; loading.value = true; listError.value = '';
  try {
    const result = await request<{ items: Reservation[]; total: number }>(`/manage/reservations?${new URLSearchParams({ owner_id: props.account.owner_id, page: String(page.value) })}`);
    if (n === listSequence) { items.value = result.items; total.value = result.total; }
  } catch (e) { if (n === listSequence) listError.value = (e as Error).message; }
  finally { if (n === listSequence) loading.value = false; }
}
async function loadCalendar() {
  if (!formOpen.value || draft.value.kind !== 'booking') return;
  const n = ++calendarSequence; calendarBusy.value = true; calendarError.value = '';
  try {
    const result = await request<ReservationCalendar>(`/reservation-calendar?guests=${draft.value.guests}`);
    if (n === calendarSequence) calendar.value = result;
  } catch (e) { if (n === calendarSequence) { calendar.value = undefined; calendarError.value = (e as Error).message; } }
  finally { if (n === calendarSequence) calendarBusy.value = false; }
}
function begin(kind: Draft['kind']) {
  if (frozen.value) return;
  if (draft.value.kind !== kind) { draft.value.kind = kind; draft.value.date = plusDays(hamiltonDate(), kind === 'booking' ? 1 : -1); }
  formOpen.value = true; saved.value = ''; error.value = '';
}
async function sendPending() {
  const action = pending.value; if (!action || saving.value || props.disabled) return;
  saving.value = true; emit('busy', true); error.value = ''; saved.value = '';
  try {
    await request<Reservation>(`/manage/members/${encodeURIComponent(props.account.owner_id)}/reservations`, { method: 'POST', headers: { 'Idempotency-Key': action.key }, body: JSON.stringify(action.body) });
    pending.value = null; formOpen.value = false; draft.value.reason = ''; saved.value = say(copy.saved);
    page.value = 1; await load(); emit('recorded');
  } catch (e) {
    error.value = (e as Error).message;
    if (e instanceof CommerceError && e.status >= 400 && e.status < 500) pending.value = null;
  } finally { saving.value = false; emit('busy', false); }
}
async function save() {
  if (frozen.value) return;
  error.value = '';
  if (draft.value.end <= draft.value.start) { error.value = say(copy.interval_invalid); return; }
  const backfill = draft.value.kind === 'backfill';
  const actual = minutesFromHours(draft.value.actualHours), guests = Number(draft.value.actualGuests);
  if (backfill && (actual === null || actual < 1 || actual > 1440 || !Number.isInteger(guests) || guests < 1 || guests > 99)) { error.value = say(walletCopy.wallet_actual_hours_details_required); return; }
  if (!backfill && (!available.value || calendarBusy.value || calendarError.value)) { error.value = say(copy.unavailable); return; }
  pending.value = { key: crypto.randomUUID(), body: { kind: draft.value.kind, booking: booking.value, status: backfill ? 'completed' : draft.value.status,
    ...(backfill ? { actual_minutes: actual, actual_guests: guests } : {}), reason: draft.value.reason, public_note: draft.value.publicNote, staff_note: draft.value.staffNote, locale: locale.value } };
  // Persist before sending so a lost response/reload retains the original key.
  persist(); await sendPending();
}
function persist() { saveSession(storageKey, { draft: draft.value, open: formOpen.value, pending: pending.value }); }
watch([draft, formOpen, pending], persist, { deep: true, flush: 'sync' });
watch([formOpen, () => draft.value.kind, () => draft.value.guests], loadCalendar, { immediate: true });
watch(page, load, { immediate: true });
onBeforeUnmount(() => { listSequence++; calendarSequence++; });
</script>

<template>
  <section class="member-visits">
    <h3>{{ say(copy.title) }}</h3>
    <p class="wallet-rule">{{ say(copy.no_reward) }}</p>
    <div class="wallet-form-actions">
      <button type="button" class="desk-button secondary" :disabled="frozen" @click="begin('booking')">{{ say(copy.add_booking) }}</button>
      <button type="button" class="desk-button secondary" :disabled="frozen" @click="begin('backfill')">{{ say(copy.add_backfill) }}</button>
    </div>
    <p v-if="saved" class="wallet-saved" role="status">{{ saved }}</p>
    <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
    <div v-if="pending" class="wallet-uncertain" role="alert">
      <p>{{ say(saving ? walletCopy.saving : copy.uncertain) }}</p>
      <button v-if="!saving" type="button" class="desk-button primary" :disabled="disabled" @click="sendPending">{{ say(walletCopy.retry) }}</button>
    </div>
    <form v-if="formOpen" class="wallet-form admin-visit-form" @submit.prevent="save">
      <h4>{{ say(draft.kind === 'booking' ? copy.add_booking : copy.add_backfill) }}</h4>
      <p class="wallet-rule">{{ say(draft.kind === 'booking' ? copy.booking_help : copy.backfill_help) }}</p>
      <fieldset :disabled="frozen">
        <label class="desk-field">{{ say(copy.date) }}<input v-model="draft.date" type="date" :min="draft.kind === 'booking' ? hamiltonDate() : undefined" :max="draft.kind === 'booking' ? plusDays(hamiltonDate(), 13) : hamiltonDate()" required /></label>
        <div class="wallet-input-grid">
          <label class="desk-field">{{ say(copy.start) }}<select v-model="draft.start"><option v-for="time in times" :key="time">{{ time }}</option></select></label>
          <label class="desk-field">{{ say(copy.end) }}<select v-model="draft.end"><option v-for="time in times" :key="time">{{ time }}</option></select></label>
          <label class="desk-field">{{ say(copy.plan) }}<select v-model="draft.plan"><option value="hourly">{{ say(copy.hourly) }}</option><option value="day">{{ say(copy.day) }}</option></select></label>
          <label v-if="draft.kind === 'booking'" class="desk-field">{{ say(copy.guests) }}<input v-model.number="draft.guests" type="number" min="1" :max="calendar?.max_guests_per_group || 99" step="1" required /></label>
        </div>
        <template v-if="draft.kind === 'booking'">
          <p v-if="calendarBusy" role="status">{{ say(walletCopy.loading) }}</p>
          <p v-else-if="calendarError" class="desk-error" role="alert">{{ calendarError }} <button type="button" class="desk-link" @click="loadCalendar">{{ say(walletCopy.retry) }}</button></p>
          <p v-else-if="!available" class="wallet-rule">{{ say(copy.unavailable) }}</p>
          <label class="desk-field">{{ say(copy.status) }}<select v-model="draft.status"><option value="pending">{{ say(copy.pending) }}</option><option value="confirmed">{{ say(copy.confirmed) }}</option></select></label>
        </template>
        <div v-else class="wallet-input-grid">
          <label class="desk-field">{{ say(walletCopy.actual_hours) }}<input v-model="draft.actualHours" type="number" min="0" max="24" step="any" inputmode="decimal" required /></label>
          <label class="desk-field">{{ say(walletCopy.actual_guests) }}<input v-model="draft.actualGuests" type="number" min="1" max="99" step="1" required /></label>
        </div>
        <label class="desk-field">{{ say(walletCopy.public_note) }}<textarea v-model="draft.publicNote" maxlength="600" rows="2" /></label>
        <label class="desk-field">{{ say(walletCopy.private_note) }}<textarea v-model="draft.staffNote" maxlength="1500" rows="2" /></label>
        <label class="desk-field">{{ say(copy.reason) }}<textarea v-model.trim="draft.reason" minlength="1" maxlength="600" rows="2" required /></label>
      </fieldset>
      <div class="wallet-form-actions">
        <button type="button" class="desk-button secondary" :disabled="frozen" @click="formOpen = false">{{ say(walletCopy.cancel) }}</button>
        <button class="desk-button primary" :disabled="frozen || (draft.kind === 'booking' && (calendarBusy || !available))">{{ say(draft.kind === 'booking' ? copy.save_booking : copy.save_backfill) }}</button>
      </div>
    </form>
    <p v-if="listError" class="desk-error" role="alert">{{ listError }} <button type="button" class="desk-link" @click="load">{{ say(walletCopy.retry) }}</button></p>
    <p v-else-if="loading && !items.length" role="status">{{ say(walletCopy.loading) }}</p>
    <p v-else-if="!items.length">{{ say(copy.empty) }}</p>
    <article v-for="item in items" :key="item.id" class="member-visit-row">
      <strong>{{ prettyDate(item.booking.date) }} · {{ item.booking.start }}–{{ item.booking.end }}</strong>
      <p>{{ visitStatusLabel(item.status) }} · {{ visitSourceLabel(item.creation_source) }}</p>
      <p v-if="item.actual_minutes">{{ formatCopy(walletCopy.per_guest, { v0: duration(item.actual_minutes), v1: item.actual_guests }) }}</p>
      <RouterLink :to="{ path: '/manage', query: { view: 'reservations', booking: item.id } }" class="desk-link" :aria-disabled="saving" @click="saving && $event.preventDefault()">{{ say(copy.open_record) }}</RouterLink>
    </article>
    <div v-if="total > 30" class="wallet-pagination"><button :disabled="page === 1 || loading" @click="page--">{{ say(walletCopy.previous) }}</button><span>{{ page }}</span><button :disabled="page * 30 >= total || loading" @click="page++">{{ say(walletCopy.next) }}</button></div>
  </section>
</template>

<style scoped>
.member-visits { margin: 24px 0; padding-top: 20px; border-top: 1px solid var(--line, #ddd); }
.member-visits h3, .member-visits h4 { margin: 0 0 12px; }
.admin-visit-form fieldset { display: grid; gap: 14px; padding: 0; margin: 0; border: 0; min-width: 0; }
.member-visit-row { padding: 16px 0; border-top: 1px solid var(--line, #ddd); overflow-wrap: anywhere; }
.member-visit-row p { margin: 6px 0; font-size: 14px; }
.admin-visit-form input, .admin-visit-form select, .admin-visit-form textarea { font-size: 16px; max-width: 100%; min-width: 0; }
</style>
