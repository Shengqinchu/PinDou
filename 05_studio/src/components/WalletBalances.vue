<script setup lang="ts">
import { PhClock,PhStar } from '@phosphor-icons/vue';
import { walletCopy as copy,duration,type WalletAccount } from '../wallet';
import { say,formatCopy } from '../state';
defineProps<{account:WalletAccount}>();
</script>
<template>
  <div class="wallet-balances">
    <div class="wallet-balance time"><PhClock :size="24" weight="light"/><span>{{say(copy.remaining_time)}}</span><strong>{{duration(account.minutes)}}</strong></div>
    <div class="wallet-balance points"><PhStar :size="24" weight="light"/><span>{{say(copy.remaining_points)}}</span><strong>{{account.points.toLocaleString()}}</strong><small>{{formatCopy(copy.redeemable,{v0:account.redeemable_cad})}}</small></div>
  </div>
</template>
