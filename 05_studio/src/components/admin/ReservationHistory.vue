<script setup lang="ts">
import { ref } from 'vue';
import { useDesk } from '../../admin';
import { say } from '../../state';
import { adminVisitCopy as copy, visitStatusLabel } from '../../admin-visits';
import { walletCopy } from '../../wallet';
const props = defineProps<{ reference: string }>();
const { request } = useDesk();
type Event = { id: number; created_at: string; actor: string; status: string; note: string };
const items = ref<Event[]>([]), page = ref(1), total = ref(0), busy = ref(false), error = ref(''), loaded = ref(false);
async function load() {
  busy.value = true; error.value = '';
  try { const data = await request<{ items: Event[]; total: number }>(`/manage/reservations/${encodeURIComponent(props.reference)}/events?page=${page.value}`); items.value = data.items; total.value = data.total; loaded.value = true; }
  catch (e) { error.value = (e as Error).message; }
  finally { busy.value = false; }
}
function note(event: Event) {
  if (event.status === 'created') { try { return JSON.parse(event.note).reason || ''; } catch { return event.note; } }
  return event.note;
}
function toggle(event: EventTarget | null) { if ((event as HTMLDetailsElement)?.open && !loaded.value && !busy.value) void load(); }
</script>
<template>
  <details class="reservation-history" @toggle="toggle($event.target)">
    <summary>{{ say(copy.history) }}</summary>
    <p v-if="busy" role="status">{{ say(walletCopy.loading) }}</p>
    <p v-if="error" class="desk-error" role="alert">{{ error }} <button type="button" class="desk-link" @click="load">{{ say(walletCopy.retry) }}</button></p>
    <article v-for="event in items" :key="event.id"><strong>{{ visitStatusLabel(event.status) }} · {{ event.actor }}</strong><time>{{ event.created_at }}</time><p v-if="note(event)">{{ note(event) }}</p></article>
    <div v-if="total > 30" class="wallet-pagination"><button :disabled="page === 1 || busy" @click="page--;load()">{{ say(walletCopy.previous) }}</button><span>{{ page }}</span><button :disabled="page * 30 >= total || busy" @click="page++;load()">{{ say(walletCopy.next) }}</button></div>
  </details>
</template>
<style scoped>
.reservation-history { margin: 20px 0; overflow-wrap: anywhere; }
.reservation-history summary { cursor: pointer; padding: 10px 0; }
.reservation-history article { padding: 12px 0; border-bottom: 1px solid var(--line, #ddd); font-size: 14px; }
.reservation-history time { display: block; color: var(--muted, #666); margin-top: 4px; }
.reservation-history p { margin: 8px 0 0; white-space: pre-wrap; }
</style>
