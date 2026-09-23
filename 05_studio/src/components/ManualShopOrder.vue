<script setup lang="ts">
import { PhCheck } from '@phosphor-icons/vue';
import { type Order } from '../commerce';
import { orderWords as o, manualStates } from '../shop-ordering';
import { say } from '../state';
import LiftTitle from './LiftTitle.vue';
import '../styles/shop-ordering.css';
import '../styles/shop.css';
defineProps<{order:Order}>();
</script>
<template>
 <section class="shop-manual-receipt"><div class="shop-success-mark"><PhCheck :size="28"/></div><LiftTitle as="h1" :text="say(order.status==='manual_pending'?o.successTitle:o[order.status as typeof manualStates[number]])"/>
  <p v-if="order.status==='manual_pending'" class="shop-success-copy">{{say(o.success)}}</p>
  <p class="shop-order-reference">{{say(o.orderNumber)}}：<strong>{{order.id}}</strong></p>
 </section>
</template>
