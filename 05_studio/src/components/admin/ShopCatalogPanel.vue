<script setup lang="ts">
import { computed, onMounted, onDeactivated, ref } from 'vue';
import { PhPlus, PhArrowClockwise, PhPencilSimple } from '@phosphor-icons/vue';
import { useDesk } from '../../admin';
import { say, tr, formatCopy } from '../../state';
import { money, CommerceError } from '../../commerce';
import { shopWords as w, shopImage, loadShop, type ShopCatalog, type ShopProduct, type ShopCategory } from '../../shop';
import { uploadMedia } from '../../editor';
import MediaUpload from './MediaUpload.vue';
import SlideOver from '../SlideOver.vue';
import '../../styles/shop.css';
defineProps<{active?:boolean}>();
const {request}=useDesk();
const data=ref<ShopCatalog>(),busy=ref(false),error=ref(''),success=ref(''),search=ref(''),collection=ref('all'),category=ref('all');
const categoryMode=ref(false),edit=ref<ShopProduct>(),categoryEdit=ref<ShopCategory>(),open=ref(false),categoryOpen=ref(false),price=ref('');
const drafts=new Map<string,{product:ShopProduct;price:string}>();
const clone=<T,>(v:T):T=>JSON.parse(JSON.stringify(v));
const leaves=computed(()=>data.value?.categories.filter(c=>c.parent_id)||[]);
const visible=computed(()=>data.value?.products.filter(p=>(collection.value==='all'||p.shop_collection===collection.value)&&(category.value==='all'||p.shop_category_id===category.value)&&`${p.zh} ${p.en} ${p.code}`.toLowerCase().includes(search.value.trim().toLowerCase()))||[]);
const roots=computed(()=>data.value?.categories.filter(c=>!c.parent_id&&c.id!==categoryEdit.value?.id)||[]);
function fail(e:unknown){const x=e as CommerceError;error.value=say(x.code==='version_conflict'?w.conflict:x.code==='shop_category_invalid'?w.invalidCategory:x.code==='shop_category_in_use'?w.categoryUsed:[])||x.message;}
async function refresh(){error.value='';try{data.value=await request<ShopCatalog>('/manage/shop')}catch(e){fail(e)}}
function keepDraft(){if(edit.value)drafts.set(edit.value.id,{product:clone(edit.value),price:price.value})}
function editProduct(p:ShopProduct){if(busy.value)return;keepDraft();const draft=drafts.get(p.id);edit.value=clone(draft?.product||p);price.value=draft?.price??(p.price_cents===null?'':String(p.price_cents/100));error.value='';success.value='';open.value=true;}
function create(){editProduct({id:'item-'+crypto.randomUUID().slice(0,12),kind:'physical',category:'beads',zh:'',en:'',detailZh:'',detailEn:'',image:'',images:[],price_cents:null,stock:0,active:false,version:1,shop_collection:collection.value==='finished'?'finished':collection.value==='services'?'services':'home',shop_category_id:collection.value==='finished'||collection.value==='services'?null:leaves.value[0]?.id||null,shop_visible:false,code:'',sort:500});}
function changeCollection(){if(edit.value)edit.value.shop_category_id=edit.value.shop_collection==='home'?(leaves.value[0]?.id||null):null;}
async function save(){
 if(!edit.value||busy.value)return;
 if(price.value&&!/^\d{1,5}(\.\d{1,2})?$/.test(price.value)){error.value=say(w.invalidPrice);return;}
 const amount=price.value===''?null:Math.round(Number(price.value)*100);
 if(amount!==null&&(amount<1||amount>1000000)){error.value=say(w.invalidPrice);return;}
 const current=clone(edit.value);current.price_cents=amount;current.image=current.images[0]||'';current.active=false;
 current.category=current.shop_collection==='home'?(data.value?.categories.find(c=>c.id===current.shop_category_id)?.parent_id==='tools'?'tools':'beads'):'finished';
 busy.value=true;error.value='';success.value='';
 try{const next=await request<ShopProduct>('/manage/products/'+current.id,{method:'PUT',body:JSON.stringify(current)});drafts.delete(current.id);edit.value=clone(next);await refresh();void loadShop(true).catch(()=>{});open.value=false;success.value=say(w.saved)}catch(e){fail(e)}finally{busy.value=false;}
}
async function reloadProduct(){if(!edit.value||busy.value)return;const id=edit.value.id;await refresh();const p=data.value?.products.find(p=>p.id===id);if(p){drafts.delete(id);edit.value=undefined;editProduct(p)}}
async function upload(files:File[]){
 if(!edit.value||busy.value)return;const target=edit.value;busy.value=true;error.value='';
 try{for(const file of files.slice(0,12-target.images.length)){const asset=await uploadMedia(request,file,true);if(!target.images.includes(asset.src))target.images.push(asset.src)}}catch(e){fail(e)}finally{busy.value=false;}
}
function cover(index:number){if(!edit.value||busy.value)return;edit.value.images.unshift(...edit.value.images.splice(index,1));}
function editCat(c?:ShopCategory){if(busy.value)return;categoryEdit.value=clone(c||{id:'category-'+crypto.randomUUID().slice(0,12),parent_id:null,zh:'',en:'',visible:true,version:1,sort:50});error.value='';success.value='';categoryOpen.value=true;}
async function saveCat(){if(!categoryEdit.value||busy.value)return;busy.value=true;error.value='';try{await request('/manage/shop/categories/'+categoryEdit.value.id,{method:'PUT',body:JSON.stringify(categoryEdit.value)});await refresh();void loadShop(true).catch(()=>{});categoryOpen.value=false;success.value=say(w.saved)}catch(e){fail(e)}finally{busy.value=false}}
async function reloadCat(){const id=categoryEdit.value?.id;await refresh();const c=data.value?.categories.find(c=>c.id===id);if(c)editCat(c)}
onMounted(refresh);onDeactivated(()=>{keepDraft();open.value=false;categoryOpen.value=false;});defineExpose({refresh});
</script>
<template>
 <section class="shop-admin">
  <header class="desk-page-heading"><div><h1>{{say(w.adminTitle)}}</h1><p>{{say(w.adminHelp)}}</p></div><div class="shop-actions"><button class="desk-button secondary" @click="refresh"><PhArrowClockwise/>{{say(w.refresh)}}</button><button class="desk-button primary" @click="categoryMode?editCat():create()"><PhPlus/>{{say(categoryMode?w.addCategory:w.addProduct)}}</button></div></header>
  <nav class="shop-tabs"><button :class="{active:!categoryMode}" @click="categoryMode=false">{{say(w.adminTitle)}}</button><button :class="{active:categoryMode}" @click="categoryMode=true">{{say(w.categories)}}</button></nav>
  <p v-if="error&&!open&&!categoryOpen" role="alert" class="shop-error">{{error}}</p><p v-if="success" role="status">{{success}}</p>
  <template v-if="!categoryMode">
   <div class="shop-admin-tools"><select v-model="collection" :aria-label="say(w.collection)"><option value="all">{{say(w.all)}}</option><option v-for="s in (['home','finished','services'] as const)" :key="s" :value="s">{{say(w[s])}}</option></select><select v-model="category" :aria-label="say(w.category)"><option value="all">{{say(w.all)}}</option><option v-for="c in leaves" :key="c.id" :value="c.id">{{tr(c.zh,c.en)}}</option></select><input v-model="search" type="search" :placeholder="say(w.search)" :aria-label="say(w.search)"/></div>
   <p class="shop-notice">{{formatCopy(w.count,{v0:visible.length})}}</p>
   <div class="shop-admin-list"><button v-for="p in visible" :key="p.id" class="shop-admin-row" @click="editProduct(p)"><img v-if="p.images.length" :src="shopImage(p.images[0])" alt="" loading="lazy"/><span v-else class="shop-bag-thumb">{{p.code||'—'}}</span><span><strong>{{tr(p.zh,p.en)}}</strong><small>{{p.code}}</small></span><span>{{p.price_cents===null?say(w.unpriced):money(p.price_cents)}}</span><span>{{say(p.shop_visible?w.visible:w.hidden)}}<PhPencilSimple/></span></button></div>
   <p v-if="!visible.length" class="shop-state">{{say(w.noMatch)}}</p>
  </template>
  <div v-else class="shop-admin-categories"><button v-for="c in data?.categories" :key="c.id" :class="{child:c.parent_id}" @click="editCat(c)">{{tr(c.zh,c.en)}}<small v-if="!c.visible"> · {{say(w.hidden)}}</small></button></div>
 </section>
 <SlideOver v-model="open" :title="say(w.editProduct)" :busy="busy">
  <form v-if="edit" id="shop-product-editor" class="shop-edit-form" @submit.prevent="save">
   <div class="shop-edit-pair"><label>{{say(w.nameZh)}}<input v-model="edit.zh" maxlength="90" required/></label><label>{{say(w.nameEn)}}<input v-model="edit.en" maxlength="140" required/></label></div>
   <div class="shop-edit-pair"><label>{{say(w.collection)}}<select :aria-label="say(w.collection)" v-model="edit.shop_collection" @change="changeCollection"><option v-for="s in (['home','finished','services'] as const)" :key="s" :value="s">{{say(w[s])}}</option></select></label><label v-if="edit.shop_collection==='home'">{{say(w.category)}}<select :aria-label="say(w.category)" v-model="edit.shop_category_id" required><option v-for="c in leaves" :key="c.id" :value="c.id">{{tr(c.zh,c.en)}}</option></select></label></div>
   <div class="shop-edit-pair"><label>{{say(w.price)}}<input v-model="price" inputmode="decimal" :placeholder="say(w.unpriced)"/></label><label>{{say(w.stock)}}<input v-model.number="edit.stock" type="number" min="0" max="100000" step="1" required/></label></div>
   <p class="shop-notice">{{say(w.pendingInfo)}}</p>
   <div class="shop-edit-pair"><label>{{say(w.code)}}<input v-model="edit.code" maxlength="50"/></label><label>{{say(w.sort)}}<input v-model.number="edit.sort" type="number" min="0" max="100000" step="1" required/></label></div>
   <label>{{say(w.detailZh)}}<textarea v-model="edit.detailZh" maxlength="500"/></label><label>{{say(w.detailEn)}}<textarea v-model="edit.detailEn" maxlength="700"/></label>
   <label class="shop-check"><input v-model="edit.shop_visible" type="checkbox"/>{{say(w.show)}}</label>
   <div><h3>{{say(w.photos)}}</h3><p class="shop-notice">{{say(w.photoHelp)}}</p><div class="shop-edit-photos"><div v-for="(src,i) in edit.images" :key="src"><img :src="shopImage(src)" :alt="formatCopy(w.imageNumber,{v0:i+1})"/><button v-if="i>0" type="button" :disabled="busy" @click="cover(i)">{{say(w.cover)}}</button><button type="button" :disabled="busy" @click="edit.images.splice(i,1)">{{say(w.remove)}}</button></div></div><MediaUpload multiple original :busy="busy" :disabled="busy||edit.images.length>=12" :label="say(w.upload)" @select="upload"/></div>
   <details v-if="data?.sources?.[edit.id]"><summary>{{say(w.source)}}</summary><p>{{data.sources[edit.id].platform}} · {{data.sources[edit.id].title}}</p><p>{{say(w.sourcePrice)}} {{(data.sources[edit.id].source_min_fen/100).toFixed(2)}}</p></details>
   <p v-if="error" class="shop-error" role="alert">{{error}} <button type="button" :disabled="busy" @click="reloadProduct">{{say(w.retry)}}</button></p>
  </form>
  <template #footer><button class="desk-button primary" form="shop-product-editor" type="submit" :disabled="busy">{{say(w.save)}}</button></template>
 </SlideOver>
 <SlideOver v-model="categoryOpen" :title="say(w.editCategory)" :busy="busy"><form v-if="categoryEdit" id="shop-category-editor" class="shop-edit-form" @submit.prevent="saveCat">
  <label>{{say(w.nameZh)}}<input v-model="categoryEdit.zh" maxlength="60" required/></label><label>{{say(w.nameEn)}}<input v-model="categoryEdit.en" maxlength="100" required/></label><label>{{say(w.parent)}}<select v-model="categoryEdit.parent_id" :aria-label="say(w.parent)"><option :value="null">{{say(w.topCategory)}}</option><option v-for="c in roots" :key="c.id" :value="c.id">{{tr(c.zh,c.en)}}</option></select></label><label>{{say(w.sort)}}<input v-model.number="categoryEdit.sort" type="number" min="0" max="100000" required/></label><label class="shop-check"><input v-model="categoryEdit.visible" type="checkbox"/>{{say(w.show)}}</label><p v-if="error" class="shop-error" role="alert">{{error}} <button type="button" :disabled="busy" @click="reloadCat">{{say(w.retry)}}</button></p>
 </form><template #footer><button class="desk-button primary" form="shop-category-editor" type="submit" :disabled="busy">{{say(w.save)}}</button></template></SlideOver>
</template>
