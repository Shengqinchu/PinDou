<script setup lang="ts">
import {computed,ref,watch} from 'vue';
import {PhUserCircle} from '@phosphor-icons/vue';
import {profileCopy as copy} from '../profile';
import {say} from '../state';
import {contactMethodLabel} from '../booking-profile';
import type {WalletAccount} from '../wallet';
const props=defineProps<{customer:WalletAccount;compact?:boolean}>();
const failed=ref(false);watch(()=>props.customer.avatar,()=>failed.value=false);
const title=computed(()=>props.customer.booking_profile?.name||props.customer.name);
</script>
<template><span class="customer-identity" :class="{'customer-identity--compact':compact}">
 <img v-if="customer.avatar&&!failed" :src="customer.avatar" alt="" referrerpolicy="no-referrer" @error="failed=true"/><PhUserCircle v-else :size="44" weight="light"/>
 <span class="customer-identity-info"><strong>{{title}}</strong><small>{{say(copy.nickname)}} · {{customer.name}}</small><small>{{say(copy.customer_code)}} · {{customer.customer_code}}</small><template v-if="!compact"><small v-for="contact in customer.contacts" :key="contact.kind+contact.value">{{contactMethodLabel(contact.kind)}} · {{contact.value}}</small></template></span>
</span></template>
<style scoped>.customer-identity{display:flex;align-items:center;gap:12px;min-width:0;text-align:left}.customer-identity>img{width:44px;height:44px;object-fit:cover;border-radius:14px;flex:none}.customer-identity>svg{flex:none}.customer-identity-info{display:grid;gap:4px;min-width:0}.customer-identity-info strong,.customer-identity-info small{white-space:normal;overflow-wrap:anywhere}.customer-identity-info small{font-size:12px;color:var(--muted,#657579);line-height:1.5}.customer-identity--compact>img{width:38px;height:38px}</style>
