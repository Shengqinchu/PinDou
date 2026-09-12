<script setup lang="ts">
import {computed,ref,watch} from 'vue';
import StudioGlyph from './StudioGlyph.vue';
import copy from '../../../05_studio/src/content/profile.json';
import visit from '../../../05_studio/src/content/pages-Visit.json';
const props=withDefaults(defineProps<{customer:any;language:'zh'|'en';compact?:boolean}>(),{compact:false});
const failed=ref(false);watch(()=>props.customer?.avatar,()=>failed.value=false);
const image=computed(()=>props.customer?.avatar?.startsWith('/')?'https://pindoupuppy.com'+props.customer.avatar:props.customer?.avatar);
const say=(pair:string[])=>pair[props.language==='en'?1:0];
const contactLabel=(kind:string)=>say(({wechat:visit.wechat_2941d2,phone:visit.phone_ac7a62,email:visit.email_b6d15f,other:visit.another_way_f489b4} as Record<string,string[]>)[kind]||visit.another_way_f489b4);
</script>
<template><view v-if="customer" class="native-customer-identity"><image v-if="image&&!failed" :src="image" mode="aspectFill" class="native-customer-avatar" @error="failed=true"/><view v-else class="native-customer-avatar"><StudioGlyph name="user" :size="28"/></view><view class="native-customer-info"><text class="admin-name">{{customer.booking_profile?.name||customer.name}}</text><text class="admin-muted">{{say(copy.nickname)}} · {{customer.name}}</text><text class="admin-muted" selectable>{{say(copy.customer_code)}} · {{customer.customer_code}}</text><template v-if="!compact"><text v-for="contact in customer.contacts" :key="contact.kind+contact.value" class="admin-muted" selectable>{{contactLabel(contact.kind)}} · {{contact.value}}</text></template></view></view></template>
<style scoped>.native-customer-identity{display:flex;align-items:center;gap:12px;min-width:0;width:100%;text-align:left}.native-customer-avatar{width:44px;height:44px;border-radius:14px;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:#f0f6f9}.native-customer-info{display:flex;flex-direction:column;gap:5px;min-width:0;flex:1;overflow-wrap:anywhere;word-break:break-word}</style>
