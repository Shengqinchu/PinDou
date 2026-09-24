<script setup lang="ts">
import { PhCheck } from '@phosphor-icons/vue';
import { type Order } from '../commerce';
import { orderWords as o, manualStatus } from '../shop-ordering';
import { locale, say, tr } from '../state';
import { money } from '../commerce';
import LiftTitle from './LiftTitle.vue';
import '../styles/shop-ordering.css';
import '../styles/shop.css';
defineProps<{order:Order;detailed?:boolean}>();
function placedAt(timestamp:number){return new Intl.DateTimeFormat(locale.value==='zh'?'zh-CN':'en-CA',{dateStyle:'medium',timeStyle:'short',timeZone:'America/Toronto'}).format(new Date(timestamp*1000));}
</script>
<template>
 <section class="shop-manual-receipt"><div class="shop-success-mark"><PhCheck :size="28"/></div><LiftTitle as="h1" :text="!detailed&&order.status==='manual_pending'?say(o.successTitle):manualStatus(order.status,order.customer?.delivery_method)"/>
  <p v-if="!detailed&&order.status==='manual_pending'" class="shop-success-copy">{{say(o.success)}}</p>
  <p class="shop-order-reference">{{say(o.orderNumber)}}：<strong>{{order.id}}</strong></p>
  <template v-if="detailed"><p class="shop-order-reference">{{say(o.placedAt)}}：{{placedAt(order.created_at)}}</p><article v-for="(line,i) in order.quote.lines" :key="i" class="shop-receipt-line"><div><strong>{{tr(line.zh,line.en)}} × {{line.quantity}}</strong><p v-if="line.variant_zh||line.choice_zh">{{tr(line.variant_zh||'',line.variant_en||'')}} · {{tr(line.choice_zh||'',line.choice_en||'')}}</p></div><strong>{{money(line.total_cents)}}</strong></article><p class="shop-order-sum"><span>{{say(o.total)}}</span><strong>{{money(order.quote.total_cents)}}</strong></p></template>
 </section>
</template>
