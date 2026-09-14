<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { PhMinus, PhPlus, PhTrash, PhArrowRight } from '@phosphor-icons/vue';
import SlideOver from './SlideOver.vue';
import { bag, checkoutBusy, commerceApi, CommerceError, money, quantityChange, removeLine, rememberOrder, type Order, type Quote } from '../commerce';
import { shopWords as w, shopImage, type ShopProduct } from '../shop';
import { orderWords as o, optionText, offerText, orderable, shopPayload, variantPrice, hasVariantPrices } from '../shop-ordering';
import { locale, say, tr } from '../state';

const props=defineProps<{modelValue:boolean;products:ShopProduct[];enabled:boolean}>();
const emit=defineEmits<{'update:modelValue':[boolean]}>();
const open=computed({get:()=>props.modelValue,set:v=>emit('update:modelValue',v)}),router=useRouter();
const quote=ref<Quote>(),error=ref(''),loading=ref(false),sending=ref(false),name=ref(''),contact=ref(''),notes=ref('');
type Attempt={key:string;payload:Record<string,unknown>};
const storageKey='puppy-shop-checkout-v1';
function restore():Attempt|undefined {try{const v=JSON.parse(localStorage.getItem(storageKey)||'null');return v&&typeof v.key==='string'&&typeof v.payload?.access_key==='string'?v:undefined}catch{return undefined}}
const attempt=ref<Attempt|undefined>(restore());
const locked=computed(()=>!!attempt.value||sending.value);
watch(locked,v=>{checkoutBusy.value=v},{immediate:true});
const items=computed(()=>bag.value.map(line=>({line,product:props.products.find(p=>p.id===line.product_id)})));
const invalid=computed(()=>items.value.some(({line,product:p})=>!orderable(p)||!!line.booking));
const missingOption=computed(()=>items.value.some(({line,product:p})=>(!!p?.variants?.length&&!p.variants.some(v=>v.id===line.variant_id))||(!p?.variants?.length&&!!line.variant_id)||(!!p?.choices?.length&&!p.choices.some(v=>v.id===line.choice_id))||(!p?.choices?.length&&!!line.choice_id)));
const duplicate=computed(()=>new Set(bag.value.map(l=>JSON.stringify([l.product_id,l.variant_id||'',l.choice_id||'']))).size!==bag.value.length);
function mergeSelections(){
 if(locked.value)return;
 const merged:typeof bag.value=[];
 for(const line of bag.value){const existing=merged.find(l=>l.product_id===line.product_id&&(l.variant_id||'')===(line.variant_id||'')&&(l.choice_id||'')===(line.choice_id||''));
  if(existing){if(existing.quantity+line.quantity>20){error.value=say(w.cartLimit);return;}existing.quantity+=line.quantity;}else merged.push({...line});}
 if(merged.length!==bag.value.length)bag.value=merged;
}
let sequence=0,timer:ReturnType<typeof setTimeout>|undefined;
async function refreshQuote(){
 const seq=++sequence;quote.value=undefined;error.value='';
 if(!props.enabled||!bag.value.length||invalid.value||missingOption.value||duplicate.value||locked.value){loading.value=false;return}
 loading.value=true;
 try{const result=await commerceApi<Quote>('/shop/cart/quote',{method:'POST',body:JSON.stringify({items:shopPayload(bag.value)})});if(seq===sequence)quote.value=result;}
 catch(e){if(seq===sequence)error.value=(e as Error).message}finally{if(seq===sequence)loading.value=false}
}
watch([()=>props.modelValue,()=>props.products,bag],()=>{mergeSelections();++sequence;quote.value=undefined;clearTimeout(timer);if(open.value&&!locked.value)timer=setTimeout(refreshQuote,180)},{deep:true,immediate:true});
function persistAttempt(value?:Attempt){attempt.value=value;try{if(value)localStorage.setItem(storageKey,JSON.stringify(value));else localStorage.removeItem(storageKey)}catch{/* Retain the in-memory recovery record. */}}
async function submit(){
 if(sending.value)return;
 if(!attempt.value){
  if(!quote.value||loading.value||invalid.value||missingOption.value||duplicate.value)return;
  const key=Array.from(crypto.getRandomValues(new Uint8Array(32)),b=>b.toString(16).padStart(2,'0')).join('');
  persistAttempt({key:crypto.randomUUID(),payload:{items:shopPayload(bag.value),name:name.value,contact:contact.value,notes:notes.value,locale:locale.value,quote_id:quote.value.quote_id,access_key:key}});
 }
 sending.value=true;error.value='';const current=attempt.value!;
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),30000);
 try{
  const result=await commerceApi<Order>('/shop/orders',{method:'POST',headers:{'Idempotency-Key':current.key},body:JSON.stringify(current.payload),signal:controller.signal});
  rememberOrder(result.id,String(current.payload.access_key));persistAttempt();bag.value=[];quote.value=undefined;open.value=false;await router.push('/order/'+result.id);
 }catch(e){
  if(e instanceof CommerceError&&e.status>=400&&e.status<500){persistAttempt();error.value=e.message;quote.value=undefined;}
  else error.value=say(o.uncertain);
 }finally{clearTimeout(timeout);sending.value=false;}
}
onBeforeUnmount(()=>{++sequence;clearTimeout(timer);checkoutBusy.value=false});
</script>
<template>
 <SlideOver v-model="open" :title="say(w.cart)" :busy="sending">
  <p class="shop-notice">{{say(o.notice)}}</p>
  <p v-if="!items.length&&!attempt" class="shop-state">{{say(w.cartEmpty)}}</p>
  <div v-for="{line,product:p} in items" :key="line.key" class="shop-bag-row">
   <div class="shop-bag-thumb"><img v-if="p?.images.length" :src="shopImage(p.images[0])" alt=""/><span v-else>{{p?.code||'—'}}</span></div>
   <div class="shop-bag-info"><strong>{{p?tr(p.zh,p.en):say(w.unavailable)}}</strong><p>{{variantPrice(p,line.variant_id)!==null?money(variantPrice(p,line.variant_id)!):say(w.unpriced)}}</p>
    <label v-if="p?.variants?.length" class="shop-cart-select">{{say(o.variants)}}<select v-model="line.variant_id" :disabled="locked"><option :value="undefined" disabled>{{say(o.choose)}}</option><option v-for="v in p.variants" :key="v.id" :value="v.id">{{tr(v.zh,v.en)}}{{hasVariantPrices(p)&&variantPrice(p,v.id)!==null?' · '+money(variantPrice(p,v.id)!):''}}</option></select></label>
    <label v-if="p?.choices?.length" class="shop-cart-select">{{tr(p.choiceZh||'',p.choiceEn||'')}}<select v-model="line.choice_id" :disabled="locked"><option :value="undefined" disabled>{{say(o.choose)}}</option><option v-for="v in p.choices" :key="v.id" :value="v.id">{{tr(v.zh,v.en)}}</option></select></label>
    <p v-if="!p?.variants?.length&&!p?.choices?.length&&optionText(p,line)">{{optionText(p,line)}}</p>
    <small v-if="p?.quantity_offer" class="shop-offer">{{offerText(p)}}<small v-if="hasVariantPrices(p)">{{say(o.variantOfferNote)}}</small></small>
    <div class="shop-quantity" :aria-label="say(w.quantity)"><button :disabled="locked||line.quantity<=1" :aria-label="say(w.quantity)+' −'" @click="quantityChange(line.key,-1)"><PhMinus/></button><span>{{line.quantity}}</span><button :disabled="locked||line.quantity>=20" :aria-label="say(w.quantity)+' +'" @click="quantityChange(line.key,1)"><PhPlus/></button></div>
   </div><button class="shop-remove" :disabled="locked" :aria-label="say(w.remove)" @click="removeLine(line.key)"><PhTrash/></button>
  </div>
  <p v-if="invalid&&!locked" class="shop-error" role="alert">{{say(o.ineligible)}}</p>
  <p v-else-if="missingOption&&!locked" class="shop-error" role="alert">{{say(o.missingVariant)}}</p>
  <p v-if="duplicate&&!locked" class="shop-error" role="alert">{{say(w.cartLimit)}}</p>
  <form v-if="items.length&&!invalid&&!missingOption&&!locked" id="manual-shop-order" class="shop-edit-form shop-checkout-form" @submit.prevent="submit">
   <label>{{say(o.name)}}<input v-model="name" maxlength="80" autocomplete="name"/></label>
   <label>{{say(o.contactOptional)}}<input v-model="contact" maxlength="180" :placeholder="say(o.contactHint)"/></label>
   <label>{{say(o.notes)}}<textarea v-model="notes" maxlength="1500" rows="3"/></label>
  </form>
  <p v-if="attempt&&!sending" class="shop-notice" role="status">{{say(o.uncertain)}}</p>
  <p v-if="error" class="shop-error" role="alert">{{error}}</p>
  <template #footer>
   <div v-if="quote" class="shop-cart-total"><span>{{say(o.total)}}</span><strong>{{money(quote.total_cents)}}</strong><small v-if="quote.discount_cents">{{say(o.discount)}} −{{money(quote.discount_cents)}}</small></div>
   <button v-if="attempt" class="desk-button primary" :disabled="sending" @click="submit">{{say(sending?o.submitting:o.retrySubmit)}}</button>
   <button v-else-if="quote" form="manual-shop-order" class="desk-button primary" :disabled="loading||sending||!enabled" type="submit">{{say(o.submit)}}<PhArrowRight/></button>
   <button v-else-if="items.length&&!invalid&&!missingOption&&enabled" class="desk-button primary" :disabled="loading" @click="refreshQuote">{{say(loading?w.loading:o.reloadQuote)}}</button>
   <button v-else class="desk-button primary" @click="open=false">{{say(w.browse)}}<PhArrowRight/></button>
  </template>
 </SlideOver>
</template>
