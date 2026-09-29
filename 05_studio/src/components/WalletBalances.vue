<script setup lang="ts">
import { PhClock,PhStar } from '@phosphor-icons/vue';
import { walletCopy as copy,duration,type WalletAccount } from '../wallet';
import { say,formatCopy } from '../state';
import InfoTip from './InfoTip.vue';
import { profileCopy } from '../profile';
defineProps<{account:WalletAccount;customer?:boolean;admin?:boolean}>();
</script>
<template>
  <div class="wallet-balances">
    <div class="wallet-balance time"><div class="wallet-balance-label"><PhClock :size="20" weight="light"/><span>{{say(copy.remaining_time)}}</span><InfoTip v-if="customer" :label="say(profileCopy.time_help)"><p>{{say(copy.time_rule)}}</p></InfoTip></div><strong>{{duration(account.minutes)}}</strong></div>
    <div class="wallet-balance points"><div class="wallet-balance-label"><PhStar :size="20" weight="light"/><span>{{say(copy.remaining_points)}}</span><InfoTip v-if="customer" :label="say(profileCopy.points_help)"><p>{{formatCopy(copy.redeemable,{v0:account.redeemable_cad})}}</p><p>{{say(copy.rules)}}<br/>{{say(copy.redeem_rule)}}<br/>{{say(copy.promotion_rule)}}</p><p>{{say(copy.earn_rule)}}</p><p>{{say(copy.patch_points_rule)}}</p></InfoTip></div><strong>{{account.points.toLocaleString()}}</strong><small v-if="!customer">{{formatCopy(copy.redeemable,{v0:admin?(account.points/account.points_per_cad).toFixed(2):account.redeemable_cad})}}</small></div>
  </div>
</template>
