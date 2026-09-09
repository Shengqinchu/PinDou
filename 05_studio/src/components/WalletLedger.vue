<script setup lang="ts">
import { walletCopy as copy,duration,type WalletEntry } from '../wallet';
import { say,prettyDate,formatCopy } from '../state';
defineProps<{entries:WalletEntry[];admin?:boolean;busy?:boolean}>();
const emit=defineEmits<{reverse:[WalletEntry]}>();
const kind=(value:string)=>say((copy as Record<string,string[]>)[value]||copy.adjustment);
</script>
<template>
  <p v-if="!entries.length" class="account-note wallet-empty">{{say(copy.empty)}}</p>
  <ol v-else class="wallet-ledger">
    <li v-for="entry in entries" :key="entry.id">
      <div class="wallet-entry-heading"><strong>{{kind(entry.kind)}}</strong><time :datetime="entry.effective_date">{{prettyDate(entry.effective_date)}}</time></div>
      <div class="wallet-entry-deltas"><strong v-if="entry.minutes_delta">{{entry.minutes_delta>0?'+':'−'}}{{duration(entry.minutes_delta)}}</strong><strong v-if="entry.points_delta">{{entry.points_delta>0?'+':'−'}}{{formatCopy(copy.point_count,{v0:Math.abs(entry.points_delta)})}}</strong></div>
      <p v-if="entry.note">{{entry.note}}</p><small v-if="entry.reservation_id">{{entry.reservation_id}}</small>
      <small class="wallet-entry-balance">{{say(copy.balance_after)}} · <span v-if="entry.minutes_delta">{{duration(entry.minutes_balance)}}</span><span v-if="entry.minutes_delta&&entry.points_delta"> / </span><span v-if="entry.points_delta">{{formatCopy(copy.point_count,{v0:entry.points_balance})}}</span></small>
      <small v-if="entry.reversed_by">{{say(copy.reversed)}}</small>
      <button v-else-if="admin&&!entry.reverses_id" class="desk-link wallet-reverse" :disabled="busy" @click="emit('reverse',entry)">{{say(copy.reverse)}}</button>
    </li>
  </ol>
</template>
