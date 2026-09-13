<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { useDesk, localTime } from '../../admin';
import { type Order, money } from '../../commerce';
import { shopWords as w } from '../../shop';
import { orderWords as o, manualStates } from '../../shop-ordering';
import { say, tr } from '../../state';
import SlideOver from '../SlideOver.vue';
import CopyContact from '../CopyContact.vue';
const {request}=useDesk();
const items=ref<Order[]>([]),total=ref(0),page=ref(1),search=ref(''),status=ref('all'),busy=ref(false),error=ref(''),open=ref(false),selected=ref<Order>(),newStatus=ref('manual_pending'),staffNote=ref('');
let seq=0,timer:ReturnType<typeof setTimeout>;
async function refresh(){const id=++seq;try{const r=await request<{items:Order[];total:number}>('/manage/shop/orders?'+new URLSearchParams({page:String(page.value),status:status.value,search:search.value}));if(id===seq){items.value=r.items;total.value=r.total}}catch(e){if(id===seq)error.value=(e as Error).message}}
async function choose(order:Order){if(busy.value)return;busy.value=true;error.value='';try{selected.value=await request<Order>('/manage/orders/'+order.id);newStatus.value=selected.value.status;staffNote.value=selected.value.staff_note||'';open.value=true}catch(e){error.value=(e as Error).message}finally{busy.value=false}}
async function save(){if(!selected.value||busy.value)return;busy.value=true;error.value='';try{selected.value=await request<Order>('/manage/shop/orders/'+selected.value.id,{method:'PATCH',body:JSON.stringify({version:selected.value.version,status:newStatus.value,staff_note:staffNote.value})});open.value=false;await refresh()}catch(e){error.value=(e as Error).message}finally{busy.value=false}}
watch([status,search],()=>{page.value=1;clearTimeout(timer);timer=setTimeout(refresh,220)});
watch(page,refresh);onMounted(refresh);onUnmounted(()=>{seq++;clearTimeout(timer)});defineExpose({refresh});
</script>
<template>
 <section class="shop-orders-admin"><p>{{say(o.ordersHelp)}}</p><div class="shop-admin-tools"><select v-model="status" :aria-label="say(o.status)"><option value="all">{{say(w.all)}}</option><option v-for="s in manualStates" :key="s" :value="s">{{say(o[s])}}</option></select><input v-model="search" type="search" :placeholder="say(o.searchOrders)" :aria-label="say(o.searchOrders)" maxlength="120"/><button class="desk-button secondary" @click="refresh">{{say(w.refresh)}}</button></div>
  <p v-if="error&&!open" class="shop-error" role="alert">{{error}}</p><p v-if="!items.length">{{say(w.ordersEmpty)}}</p>
  <button v-for="item in items" :key="item.id" class="shop-manual-order-row" :disabled="busy" @click="choose(item)"><span><strong>{{item.customer?.name||say(o.emptyName)}}</strong><small>{{item.id}} · {{localTime(item.created_at)}}</small><span>{{item.customer?.contact||say(o.emptyContact)}}</span></span><strong>{{money(item.quote.total_cents)}}</strong><span>{{say(o[item.status as typeof manualStates[number]])}}</span></button>
  <footer class="desk-pagination"><button class="desk-button secondary" :disabled="page<=1" @click="page--">{{say(o.previous)}}</button><span>{{page}} / {{Math.max(1,Math.ceil(total/30))}}</span><button class="desk-button secondary" :disabled="page*30>=total" @click="page++">{{say(o.next)}}</button></footer>
 </section>
 <SlideOver v-model="open" :title="selected?.customer?.name||say(o.ordersTitle)" :busy="busy">
  <template v-if="selected"><p>{{selected.id}}</p><p>{{selected.customer?.contact||say(o.emptyContact)}} <CopyContact v-if="selected.customer?.contact" :value="selected.customer.contact"/></p><p class="shop-description">{{selected.customer?.notes}}</p>
   <article v-for="(line,i) in selected.quote.lines" :key="i" class="shop-receipt-line"><div><strong>{{tr(line.zh,line.en)}} × {{line.quantity}}</strong><p>{{tr(line.variant_zh||'',line.variant_en||'')}} <span v-if="line.choice_zh">· {{tr(line.choice_zh,line.choice_en||'')}}</span></p></div><strong>{{money(line.total_cents)}}</strong></article>
   <p v-if="selected.quote.discount_cents">{{say(o.discount)}} −{{money(selected.quote.discount_cents)}}</p><p>{{say(o.total)}} <strong>{{money(selected.quote.total_cents)}}</strong></p>
   <form id="shop-order-status" class="shop-edit-form" @submit.prevent="save"><label>{{say(o.status)}}<select v-model="newStatus" :aria-label="say(o.status)" :disabled="['manual_completed','manual_cancelled'].includes(selected.status)"><option v-for="s in manualStates" :key="s" :value="s">{{say(o[s])}}</option></select></label><p class="shop-notice">{{say(o.completeHelp)}}</p><label>{{say(o.staffNote)}}<textarea v-model="staffNote" maxlength="1500" rows="4"/></label></form>
   <p v-if="error" class="shop-error" role="alert">{{error}} <button type="button" :disabled="busy" @click="choose(selected)">{{say(w.retry)}}</button></p>
  </template><template #footer><button class="desk-button primary" type="submit" form="shop-order-status" :disabled="busy">{{say(w.save)}}</button></template>
 </SlideOver>
</template>
