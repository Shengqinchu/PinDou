<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { PhArrowRight, PhArrowClockwise } from '@phosphor-icons/vue';
import { accountUser, closeAccount } from '../account';
import { commerceApi, money, orderKey, type Order } from '../commerce';
import { savedShopOrders, shopWords as w } from '../shop';
import { manualStatus, orderWords as o } from '../shop-ordering';
import { locale, say, tr } from '../state';
import '../styles/shop.css';
import '../styles/shop-ordering.css';

const props=withDefaults(defineProps<{clickable?:boolean;showRefresh?:boolean}>(),{clickable:false,showRefresh:true});
const items=ref<Order[]>([]),total=ref(0),page=ref(1),busy=ref(false),error=ref('');
let sequence=0;
function placedAt(timestamp:number){return new Intl.DateTimeFormat(locale.value==='zh'?'zh-CN':'en-CA',{dateStyle:'medium',timeStyle:'short',timeZone:'America/Toronto'}).format(new Date(timestamp*1000));}
async function refresh(){
 const id=accountUser.value?.id||'',seq=++sequence;busy.value=true;error.value='';
 try{
  if(id){
   const local=savedShopOrders().slice(0,100).map(orderId=>({id:orderId,access_key:orderKey(orderId)}));
   if(local.length){try{await commerceApi('/auth/shop/orders/claim',{method:'POST',body:JSON.stringify({items:local})});}catch{/* Existing linked orders remain readable if claiming local guest orders fails. */}}
   const result=await commerceApi<{items:Order[];total:number}>(`/auth/shop/orders?page=${page.value}`);
   if(seq===sequence&&accountUser.value?.id===id){items.value=result.items;total.value=result.total;}
  }else{
   const local=savedShopOrders();
   const start=(page.value-1)*30;
   const result=await Promise.allSettled(local.slice(start,start+30).map(orderId=>commerceApi<Order>(`/orders/${orderId}`,{headers:{'X-Order-Key':orderKey(orderId)}})));
   if(seq===sequence&&!accountUser.value){items.value=result.flatMap(row=>row.status==='fulfilled'&&row.value.status!=='manual_deleted'?[row.value]:[]);total.value=local.length;}
  }
 }catch(e){if(seq===sequence)error.value=(e as Error).message;}
 finally{if(seq===sequence)busy.value=false;}
}
function visible(){if(!document.hidden&&!busy.value)void refresh();}
watch(()=>accountUser.value?.id,()=>{page.value=1;items.value=[];void refresh()});
watch(page,()=>void refresh());
onMounted(()=>{void refresh();window.addEventListener('focus',visible);});
onUnmounted(()=>{sequence++;window.removeEventListener('focus',visible);});
defineExpose({refresh,busy});
</script>
<template>
 <div class="shop-order-history">
  <div v-if="props.showRefresh" class="shop-order-history-tools"><button type="button" class="icon-button" :aria-label="say(w.refresh)" :disabled="busy" @click="refresh"><PhArrowClockwise :size="19" :class="{spinning:busy}"/></button></div>
  <p v-if="error" class="shop-error" role="alert">{{error}}</p>
  <p v-if="!items.length&&!busy" class="shop-state">{{say(w.ordersEmpty)}}</p>
  <div v-for="order in items" :key="order.id" class="shop-order-history-card">
   <div class="shop-order-history-head"><strong>{{manualStatus(order.status,order.customer?.delivery_method)}}</strong><strong>{{money(order.quote.total_cents)}}</strong></div>
   <p class="shop-order-history-products">{{order.quote.lines.map(line=>tr(line.zh,line.en)+' × '+line.quantity).join('、')}}</p>
   <p class="shop-order-history-meta">{{say(o.placedAt)}} · {{placedAt(order.created_at)}}<br/>{{say(o.orderNumber)}} · {{order.id}}</p>
   <RouterLink v-if="props.clickable" :to="'/order/'+order.id+'?details=1'" class="shop-order-history-open" @click="closeAccount">{{say(w.orderOpen)}} <PhArrowRight :size="17"/></RouterLink>
  </div>
  <div v-if="total>30" class="wallet-pagination"><button :disabled="page===1||busy" @click="page--">{{say(o.previous)}}</button><span>{{page}} / {{Math.ceil(total/30)}}</span><button :disabled="page*30>=total||busy" @click="page++">{{say(o.next)}}</button></div>
 </div>
</template>
