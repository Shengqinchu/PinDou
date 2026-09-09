<script setup lang="ts">
import { say } from '../state';
import type { ReservationOffer } from '../reservations';
import MoneyText from '../components/MoneyText.vue';
defineProps<{offer:ReservationOffer}>();
</script>
<template><span class="reservation-offer-label">{{say(offer.label)}} · <MoneyText :text="offer.currency+' '+offer.amount"/></span></template>
