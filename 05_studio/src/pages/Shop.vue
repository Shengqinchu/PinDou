<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { PhShoppingCart, PhReceipt, PhMagnifyingGlass, PhPlus, PhMinus, PhTrash, PhCaretDown, PhArrowRight } from '@phosphor-icons/vue';
import LiftTitle from '../components/LiftTitle.vue';
import SlideOver from '../components/SlideOver.vue';
import { say, tr, formatCopy } from '../state';
import { bag, bagCount, addToBag, removeLine, quantityChange, money } from '../commerce';
import { shopWords as w, shopCatalog, loadShop, shopImage, savedShopOrders, type ShopProduct } from '../shop';
import { notify } from '../ui';
import '../styles/shop.css';
const route=useRoute(),router=useRouter();
const section=computed(()=>['home','finished','services'].includes(String(route.query.section))?String(route.query.section):'home');
const searches=reactive<Record<string,string>>({home:'',finished:'',services:''});
const search=computed({get:()=>searches[section.value],set:value=>{searches[section.value]=value}});
const root=ref('refills'),leaf=ref('refill-a'),error=ref(''),loading=ref(!shopCatalog.value);
const selected=ref<ShopProduct>(),detailsOpen=ref(false),photo=ref(0);
const cartOpen=computed({get:()=>route.query.view==='cart',set:v=>setView(v?'cart':'')});
const ordersOpen=computed({get:()=>route.query.view==='orders',set:v=>setView(v?'orders':'')});
const orders=ref<string[]>([]);
const roots=computed(()=>shopCatalog.value?.categories.filter(c=>!c.parent_id)||[]);
const children=(id:string)=>shopCatalog.value?.categories.filter(c=>c.parent_id===id)||[];
const products=computed(()=>shopCatalog.value?.products||[]);
const visible=computed(()=>products.value.filter(p=>p.shop_collection===section.value&&(section.value!=='home'||p.shop_category_id===leaf.value)&&`${p.zh} ${p.en} ${p.code}`.toLowerCase().includes(search.value.trim().toLowerCase())));
const items=computed(()=>bag.value.map(line=>({line,product:products.value.find(p=>p.id===line.product_id)})));
const total=computed(()=>items.value.reduce((s,{line,product})=>s+(product?.price_cents||0)*line.quantity,0));
function setView(view:string){void router.replace({query:{...route.query,view:view||undefined}})}
function chooseRoot(id:string){root.value=id;leaf.value=children(id)[0]?.id||id;search.value='';}
function chooseSection(value:string){void router.replace({query:{...route.query,section:value}})}
function openProduct(p:ShopProduct){selected.value=p;photo.value=0;detailsOpen.value=true;}
function add(p:ShopProduct){
 const line=bag.value.find(l=>l.product_id===p.id);
 if((!line&&bag.value.length>=20)||(line&&line.quantity>=20)){notify(w.cartLimit[0],w.cartLimit[1],'error');return;}
 addToBag(p.id);
}
async function refresh(){loading.value=true;error.value='';try{await loadShop(true)}catch(e){error.value=(e as Error).message}finally{loading.value=false}}
watch(shopCatalog,d=>{if(!d)return;if(!d.categories.some(c=>c.id===leaf.value)){const r=d.categories.find(c=>c.id===root.value&&!c.parent_id)||d.categories.find(c=>!c.parent_id);root.value=r?.id||'';leaf.value=d.categories.find(c=>c.parent_id===root.value)?.id||root.value;}},{immediate:true});
watch(ordersOpen,v=>{if(v)orders.value=savedShopOrders()},{immediate:true});
onMounted(async()=>{try{await loadShop()}catch(e){error.value=(e as Error).message}finally{loading.value=false}});
</script>
<template>
 <section class="shop-page container">
  <header class="shop-heading"><LiftTitle as="h1" :text="say(w.title)"/><div class="shop-actions">
   <button class="shop-action" @click="setView('cart')"><PhShoppingCart/><span>{{say(w.cart)}}</span><span v-if="bagCount" class="shop-badge">{{bagCount}}</span></button>
   <button class="shop-action" @click="setView('orders')"><PhReceipt/><span>{{say(w.orders)}}</span></button>
  </div></header>
  <nav class="shop-tabs" :aria-label="say(w.collection)"><button v-for="s in (['home','finished','services'] as const)" :key="s" :class="{active:section===s}" :aria-pressed="section===s" @click="chooseSection(s)">{{say(w[s])}}</button></nav>
  <p v-if="error" class="shop-error" role="alert">{{error}} <button @click="refresh">{{say(w.retry)}}</button></p>
  <p v-if="loading&&!shopCatalog" class="shop-state" role="status">{{say(w.loading)}}</p>
  <div v-else class="shop-layout" :class="{'shop-layout-flat':section!=='home'}">
   <nav v-if="section==='home'" class="shop-categories" :aria-label="say(w.categories)"><div v-for="c in roots" :key="c.id" class="shop-category-group">
    <button class="shop-root" :class="{active:root===c.id}" :aria-expanded="children(c.id).length?root===c.id:undefined" :aria-pressed="!children(c.id).length?root===c.id:undefined" @click="chooseRoot(c.id)">{{tr(c.zh,c.en)}}<PhCaretDown v-if="children(c.id).length"/></button>
    <div v-if="root===c.id&&children(c.id).length" class="shop-children"><button v-for="child in children(c.id)" :key="child.id" :class="{active:leaf===child.id}" :aria-pressed="leaf===child.id" @click="leaf=child.id;search=''">{{tr(child.zh,child.en)}}</button></div>
   </div></nav>
   <main class="shop-results">
    <div class="shop-result-tools"><label class="shop-search"><PhMagnifyingGlass/><input v-model="search" type="search" :placeholder="say(w.search)" :aria-label="say(w.search)"/></label><span class="shop-result-count">{{formatCopy(w.count,{v0:visible.length})}}</span></div>
    <div class="shop-grid" :class="{'shop-service-grid':section==='services'}">
     <article v-for="p in visible" :key="p.id" class="shop-card">
      <button class="shop-card-preview" :aria-label="tr(p.zh,p.en)" @click="openProduct(p)">
       <img v-if="p.images.length" :src="shopImage(p.images[0])" :alt="tr(p.zh,p.en)" width="600" height="600" loading="lazy"/>
       <span v-else class="shop-placeholder" :class="{'shop-kit-placeholder':p.shop_category_id==='kits'}"><strong>{{p.code||tr(p.zh,p.en)}}</strong><small>{{say(w.noPhoto)}}</small></span><span v-if="p.images.length>1" class="shop-photo-count">{{p.images.length}}</span>
      </button>
      <div class="shop-card-body"><button class="shop-name" @click="openProduct(p)">{{tr(p.zh,p.en)}}</button><p>{{tr(p.detailZh,p.detailEn)}}</p>
       <div class="shop-card-bottom"><span v-if="p.price_cents!==null" class="shop-price">{{(p.price_cents/100).toFixed(2)}}<small>CAD</small></span><span v-else class="shop-unpriced">{{say(w.unpriced)}}</span><button class="shop-add" :aria-label="say(w.addCart)+' · '+tr(p.zh,p.en)" @click="section==='services'?openProduct(p):add(p)"><PhArrowRight v-if="section==='services'"/><PhPlus v-else/></button></div>
      </div>
     </article>
    </div>
    <div v-if="!visible.length" class="shop-state"><PhShoppingCart :size="32"/><h2>{{say(search?w.noMatch:w.empty)}}</h2></div>
   </main>
  </div>
 </section>
 <SlideOver v-model="detailsOpen" :title="selected?tr(selected.zh,selected.en):''">
  <div v-if="selected" class="shop-detail"><img v-if="selected.images.length" class="shop-detail-image" :src="shopImage(selected.images[photo])" :alt="tr(selected.zh,selected.en)"/><div v-else class="shop-placeholder"><strong>{{selected.code||tr(selected.zh,selected.en)}}</strong><small>{{say(w.noPhoto)}}</small></div>
   <div v-if="selected.images.length>1" class="shop-thumbnails"><button v-for="(src,i) in selected.images" :key="src" :class="{active:photo===i}" :aria-label="formatCopy(w.imageNumber,{v0:i+1})" :aria-pressed="photo===i" @click="photo=i"><img :src="shopImage(src)" alt=""/></button></div>
   <p class="shop-description">{{tr(selected.detailZh,selected.detailEn)}}</p><p>{{selected.price_cents===null?say(w.unpriced):money(selected.price_cents)}}</p>
  </div>
  <template #footer><button v-if="selected" class="desk-button primary" @click="add(selected)"><PhPlus/>{{say(w.addCart)}}</button></template>
 </SlideOver>
 <SlideOver v-model="cartOpen" :title="say(w.cart)">
  <p class="shop-notice">{{say(w.paused)}}</p><p v-if="!items.length" class="shop-state">{{say(w.cartEmpty)}}</p>
  <div v-for="{line,product} in items" :key="line.key" class="shop-bag-row"><div class="shop-bag-thumb"><img v-if="product?.images.length" :src="shopImage(product.images[0])" alt=""/><span v-else>{{product?.code||'—'}}</span></div>
   <div><strong>{{product?tr(product.zh,product.en):say(w.unavailable)}}</strong><p>{{product?.price_cents!=null?money(product.price_cents):say(w.unpriced)}}</p><div class="shop-quantity" :aria-label="say(w.quantity)"><button :disabled="line.quantity<=1" :aria-label="say(w.quantity)+' −'" @click="quantityChange(line.key,-1)"><PhMinus/></button><span>{{line.quantity}}</span><button :disabled="line.quantity>=20" :aria-label="say(w.quantity)+' +'" @click="quantityChange(line.key,1)"><PhPlus/></button></div></div>
   <button class="shop-remove" :aria-label="say(w.remove)" @click="removeLine(line.key)"><PhTrash/></button>
  </div>
  <template #footer><div class="shop-cart-total"><span>{{say(w.subtotal)}}</span><strong>{{money(total)}}</strong></div><button class="desk-button primary" @click="setView('')">{{say(w.browse)}}<PhArrowRight/></button></template>
 </SlideOver>
 <SlideOver v-model="ordersOpen" :title="say(w.orders)"><p class="shop-notice">{{say(w.ordersHelp)}}</p><p v-if="!orders.length" class="shop-state">{{say(w.ordersEmpty)}}</p><RouterLink v-for="id in orders" :key="id" class="shop-order-row" :to="'/order/'+id"><span>{{id}}</span>{{say(w.orderOpen)}}<PhArrowRight/></RouterLink></SlideOver>
</template>
