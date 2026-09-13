<script setup lang="ts">
import { ref, watch } from 'vue';
import { PhCheck } from '@phosphor-icons/vue';
import { type Order, commerceApi, money, orderKey } from '../commerce';
import { orderWords as o, manualStates } from '../shop-ordering';
import { shopWords as w, shopImage } from '../shop';
import { say, tr } from '../state';
import CopyContact from './CopyContact.vue';
import LiftTitle from './LiftTitle.vue';
import '../styles/shop-ordering.css';
import '../styles/shop.css';
const props=defineProps<{order:Order}>(),emit=defineEmits<{updated:[Order]}>();
const name=ref(''),contact=ref(''),notes=ref(''),busy=ref(false),saved=ref(false),error=ref('');
watch(()=>props.order.id,()=>{name.value=props.order.customer?.name||'';contact.value=props.order.customer?.contact||'';notes.value=props.order.customer?.notes||''},{immediate:true});
async function save(){if(busy.value)return;busy.value=true;error.value='';saved.value=false;try{const updated=await commerceApi<Order>('/shop/orders/'+props.order.id+'/contact',{method:'PATCH',headers:{'X-Order-Key':orderKey(props.order.id)},body:JSON.stringify({name:name.value,contact:contact.value,notes:notes.value,version:props.order.version})});emit('updated',updated);saved.value=true}catch(e){error.value=(e as Error).message}finally{busy.value=false}}
</script>
<template>
 <div class="shop-manual-receipt"><section class="shop-order-message"><div class="shop-success-mark"><PhCheck :size="28"/></div><LiftTitle as="h1" :text="say(order.status==='manual_pending'?o.successTitle:o[order.status as typeof manualStates[number]])"/>
  <p v-if="order.status!=='manual_cancelled'" class="shop-success-copy">{{say(o.success)}}</p>
  <p class="shop-order-reference">{{say(o.orderNumber)}} <strong>{{order.id}}</strong> <CopyContact :value="order.id"/></p>
  <div class="shop-host-contacts"><a class="desk-button secondary" href="sms:+14373624360">{{say(o.message)}} · +1 437 362 4360</a><p>{{say(o.wechat)}} · xiaogoushuangji <CopyContact value="xiaogoushuangji"/></p></div>
  <form class="shop-edit-form shop-contact-form" @submit.prevent="save"><p>{{say(o.leaveContact)}}</p><label>{{say(o.name)}}<input v-model="name" maxlength="80" autocomplete="name"/></label><label>{{say(o.contactOptional)}}<input v-model="contact" maxlength="180" :placeholder="say(o.contactHint)"/></label><label>{{say(o.notes)}}<textarea v-model="notes" maxlength="1500" rows="3"/></label><p v-if="error" class="shop-error" role="alert">{{error}}</p><p v-if="saved" role="status">{{say(o.contactSaved)}}</p><button class="desk-button primary" :disabled="busy">{{say(o.saveContact)}}</button></form>
 </section><aside class="shop-order-items"><h2>{{say(o.review)}}</h2><article v-for="(line,i) in order.quote.lines" :key="i" class="shop-receipt-line"><img v-if="line.image" :src="shopImage(line.image)" alt=""/><div><strong>{{tr(line.zh,line.en)}} × {{line.quantity}}</strong><p>{{tr(line.variant_zh||'',line.variant_en||'')}}<span v-if="line.choice_zh"> · {{tr(line.choice_zh,line.choice_en||'')}}</span></p></div><strong>{{money(line.total_cents)}}</strong></article><p v-if="order.quote.discount_cents" class="shop-order-sum">{{say(o.discount)}} <span>−{{money(order.quote.discount_cents)}}</span></p><p class="shop-order-sum">{{say(o.total)}} <strong>{{money(order.quote.total_cents)}}</strong></p><RouterLink to="/shop?section=finished" class="desk-button secondary">{{say(w.browse)}}</RouterLink></aside></div>
</template>
