<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { PhArrowLeft, PhArrowRight, PhMapPin } from '@phosphor-icons/vue';
import { bag, checkoutBusy, commerceApi, CommerceError, money, rememberOrder, type Order, type Quote } from '../commerce';
import { shopPayload, orderWords as o } from '../shop-ordering';
import { shopWords as w } from '../shop';
import { locale, say } from '../state';
import profile from '../content/studio-profile.json';
import { accountUser } from '../account';
import { loadBookingProfile } from '../booking-profile';
import '../styles/shop-ordering.css';

type Attempt={key:string;payload:Record<string,unknown>};
const storageKey='puppy-shop-checkout-v1';
function restore():Attempt|undefined {try{const v=JSON.parse(localStorage.getItem(storageKey)||'null');return v&&typeof v.key==='string'&&typeof v.payload?.access_key==='string'?v:undefined}catch{return undefined}}
const router=useRouter(),attempt=ref<Attempt|undefined>(restore());
const quote=ref<Quote>(),error=ref(''),loading=ref(false),sending=ref(false);
const delivery=ref<'pickup'|'courier'>('pickup'),name=ref(''),contact=ref(''),notes=ref(''),address=ref('');
const locked=computed(()=>!!attempt.value||sending.value);
watch(locked,value=>{checkoutBusy.value=value},{immediate:true});
let sequence=0;
async function refreshQuote(){
 const current=++sequence;quote.value=undefined;error.value='';
 if(!bag.value.length||attempt.value)return;
 loading.value=true;
 try{const result=await commerceApi<Quote>('/shop/cart/quote',{method:'POST',body:JSON.stringify({items:shopPayload(bag.value)})});if(current===sequence)quote.value=result;}
 catch(e){if(current===sequence)error.value=(e as Error).message}finally{if(current===sequence)loading.value=false}
}
function persistAttempt(value?:Attempt){attempt.value=value;try{if(value)localStorage.setItem(storageKey,JSON.stringify(value));else localStorage.removeItem(storageKey)}catch{/* Keep the in-memory recovery record. */}}
async function submit(){
 if(sending.value)return;
 if(!attempt.value){
  if(!quote.value||loading.value)return;
  if(!name.value.trim()||!contact.value.trim()||!notes.value.trim()||(delivery.value==='courier'&&!address.value.trim())){error.value=say(o.requiredDetails);return;}
  const accessKey=Array.from(crypto.getRandomValues(new Uint8Array(32)),b=>b.toString(16).padStart(2,'0')).join('');
  persistAttempt({key:crypto.randomUUID(),payload:{items:shopPayload(bag.value),name:name.value.trim(),contact:contact.value.trim(),notes:notes.value.trim(),delivery_method:delivery.value,address:delivery.value==='courier'?address.value.trim():'',locale:locale.value,quote_id:quote.value.quote_id,access_key:accessKey}});
 }
 sending.value=true;error.value='';const current=attempt.value!;
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),30000);
 try{
  const result=await commerceApi<Order>('/shop/orders',{method:'POST',headers:{'Idempotency-Key':current.key},body:JSON.stringify(current.payload),signal:controller.signal});
  rememberOrder(result.id,String(current.payload.access_key));persistAttempt();bag.value=[];quote.value=undefined;await router.replace('/order/'+result.id);
 }catch(e){
  if(e instanceof CommerceError&&e.status>=400&&e.status<500){persistAttempt();await refreshQuote();error.value=e.message;}
  else error.value=say(o.uncertain);
 }finally{clearTimeout(timeout);sending.value=false;}
}
async function prefill(){const id=accountUser.value?.id;if(!id)return;try{const saved=await loadBookingProfile(id);if(accountUser.value?.id!==id)return;if(!name.value)name.value=saved.name;if(!contact.value)contact.value=saved.contact;if(!address.value)address.value=saved.delivery_address||'';}catch{/* Checkout remains available with manual entry. */}}
watch(()=>accountUser.value?.id,()=>void prefill());
onMounted(()=>{if(!attempt.value)void refreshQuote();void prefill()});
onBeforeUnmount(()=>{++sequence;checkoutBusy.value=false});
</script>
<template>
 <section class="container shop-delivery-page section-bottom">
  <RouterLink to="/shop?view=cart" class="text-link shop-delivery-back"><PhArrowLeft :size="18"/>{{say(o.backToCart)}}</RouterLink>
  <h1>{{say(o.deliveryTitle)}}</h1>
  <p v-if="!bag.length&&!attempt" class="shop-notice">{{say(w.cartEmpty)}}</p>
  <form v-else class="shop-edit-form shop-delivery-form" @submit.prevent="submit">
   <fieldset :disabled="locked" class="shop-delivery-choice"><legend>{{say(o.deliveryMethod)}}</legend><div>
    <label :class="{active:delivery==='pickup'}"><input v-model="delivery" type="radio" value="pickup"/>{{say(o.pickup)}}</label>
    <label :class="{active:delivery==='courier'}"><input v-model="delivery" type="radio" value="courier"/>{{say(o.courier)}}</label>
   </div></fieldset>
   <p v-if="delivery==='pickup'" class="shop-pickup-address"><PhMapPin :size="20"/><span>{{say(o.pickupAddress)}}<strong>{{profile.address}}</strong></span></p>
   <p v-else class="shop-notice">{{say(o.courierFee)}}</p>
   <fieldset :disabled="locked" class="shop-delivery-fields">
    <label>{{say(o.name)}}<input v-model="name" required maxlength="80" autocomplete="name"/></label>
    <label>{{say(o.contactOptional)}}<input v-model="contact" required maxlength="180" :placeholder="say(o.contactHint)" autocomplete="tel"/></label>
    <label v-if="delivery==='courier'">{{say(o.shippingAddress)}}<textarea v-model="address" required maxlength="500" rows="2" autocomplete="street-address"/></label>
    <label>{{say(o.notes)}}<textarea v-model="notes" required maxlength="1500" rows="3" :placeholder="say(o.notesHint)"/></label>
   </fieldset>
   <p class="shop-delivery-notice">{{say(o.paymentNotice)}}</p>
   <p v-if="attempt&&!sending" class="shop-notice" role="status">{{say(o.uncertain)}}</p>
   <p v-if="error" class="shop-error" role="alert">{{error}}</p>
   <div class="shop-delivery-action"><p v-if="quote">{{say(o.total)}} <strong>{{money(quote.total_cents)}}</strong></p><button class="desk-button primary" type="submit" :disabled="sending||(!quote&&!attempt)||loading">{{say(sending?o.submitting:attempt?o.retrySubmit:o.confirmSubmit)}}<PhArrowRight :size="18"/></button></div>
  </form>
 </section>
</template>
