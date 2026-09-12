<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { PhTrash, PhArrowLeft, PhArrowRight } from '@phosphor-icons/vue';
import SlideOver from '../SlideOver.vue';
import MediaUpload from './MediaUpload.vue';
import { contentModule } from '../../content-store';
import defaults from '../../content/shop-batch.json';
import { shopWords as w, type ShopProduct } from '../../shop';
import { useDesk } from '../../admin';
import { uploadMedia } from '../../editor';
import { centsFromInput, matchProductImage } from '../../shop-batch';
import { CommerceError, money } from '../../commerce';
import { say, tr, formatCopy } from '../../state';
const b=contentModule('shop-batch',defaults);
const props=defineProps<{modelValue:boolean;products:ShopProduct[]}>();
const emit=defineEmits<{'update:modelValue':[value:boolean];saved:[count:number]}>();
const {request}=useDesk();
type Row={product:ShopProduct;price:string};
type Photo={key:string;file:File;url:string;target:string;src?:string};
const rows=ref<Row[]>([]),photos=ref<Photo[]>([]),uniform=ref(''),page=ref(0),photoPage=ref(0),busy=ref(false),error=ref(''),progress=ref('');
const assignment=ref('match'),treatment=ref<'append'|'replace'>('append'),onlyMissing=ref(true);
const pages=computed(()=>Math.max(1,Math.ceil(rows.value.length/20))),photoPages=computed(()=>Math.max(1,Math.ceil(photos.value.length/8)));
const displayed=computed(()=>rows.value.slice(page.value*20,(page.value+1)*20));
const shownPhotos=computed(()=>photos.value.slice(photoPage.value*8,(photoPage.value+1)*8));
function cleanup(){for(const p of photos.value)URL.revokeObjectURL(p.url);photos.value=[];}
watch(()=>props.modelValue,value=>{if(!value)return;cleanup();rows.value=props.products.map(p=>({product:JSON.parse(JSON.stringify(p)),price:p.price_cents===null?'':String(p.price_cents/100)}));uniform.value='';page.value=0;photoPage.value=0;error.value='';progress.value='';assignment.value='match';treatment.value='append';onlyMissing.value=true;});
onBeforeUnmount(cleanup);
function close(value:boolean){if(!busy.value)emit('update:modelValue',value)}
function applyPrice(){try{centsFromInput(uniform.value);for(const row of rows.value)row.price=uniform.value;error.value=''}catch{error.value=say(w.invalidPrice)}}
function addPhotos(files:File[]){
 if(photos.value.length+files.length>500){error.value=say(b.tooMany);return;}
 if(files.some(f=>f.size>12*1024*1024)){error.value=say(b.tooLarge);return;}
 for(const file of files)photos.value.push({key:crypto.randomUUID(),file,url:URL.createObjectURL(file),target:matchProductImage(file.name,props.products)});
 error.value='';
}
function removePhoto(key:string){const p=photos.value.find(p=>p.key===key);if(p)URL.revokeObjectURL(p.url);photos.value=photos.value.filter(p=>p.key!==key);photoPage.value=Math.min(photoPage.value,photoPages.value-1)}
function photosFor(row:Row){return onlyMissing.value&&row.product.images.length?[]:photos.value.filter(p=>assignment.value==='shared'||p.target===row.product.id)}
const priceChanges=computed(()=>rows.value.filter(r=>{try{return centsFromInput(r.price)!==r.product.price_cents}catch{return true}}).length);
const photoChanges=computed(()=>rows.value.filter(r=>photosFor(r).length).length);
const hasChanges=computed(()=>priceChanges.value+photoChanges.value>0);
async function save(){
 if(busy.value||!hasChanges.value)return;error.value='';
 try{for(const row of rows.value)centsFromInput(row.price)}catch{error.value=say(w.invalidPrice);return;}
 if(assignment.value==='match'&&photos.value.some(p=>!p.target)){error.value=say(b.unmatched);return;}
 for(const row of rows.value){const count=photosFor(row).length+(treatment.value==='append'?row.product.images.length:0);if(count>12){error.value=say(b.tooMany)+' · '+row.product.code;return;}}
 busy.value=true;
 try{
  const used=photos.value.filter(p=>rows.value.some(r=>photosFor(r).includes(p)));
  for(let i=0;i<used.length;i++){progress.value=formatCopy(b.uploading,{v0:i+1,v1:used.length});if(!used[i].src)used[i].src=(await uploadMedia(request,used[i].file,true)).src;}
  const items=rows.value.flatMap(row=>{
   const value=centsFromInput(row.price),images=photosFor(row).map(p=>p.src!);
   if(value===row.product.price_cents&&!images.length)return [];
   return [{id:row.product.id,version:row.product.version,...(value!==row.product.price_cents?{price_cents:value}:{}),...(images.length?{images,image_mode:treatment.value}:{})}];
  });
  if(!items.length)return;
  const result=await request<{updated:number}>('/manage/shop/products/batch',{method:'PATCH',body:JSON.stringify({items})});
  emit('saved',result.updated);emit('update:modelValue',false);cleanup();
 }catch(e){const x=e as CommerceError;error.value=x.code==='version_conflict'?say(b.conflict):x.code==='shop_too_many_images'?say(b.tooMany):x.message;}finally{busy.value=false;progress.value='';}
}
</script>
<template>
 <SlideOver :model-value="modelValue" :title="say(b.edit)" :subtitle="formatCopy(b.selected,{v0:rows.length})" :busy="busy" @update:model-value="close">
  <div class="shop-bulk-editor">
   <p class="shop-notice">{{say(b.priceAndPhoto)}}</p>
   <section><h3>{{say(w.price)}}</h3><p class="shop-notice">{{say(b.priceHelp)}}</p><div class="shop-bulk-uniform"><label>{{say(b.uniformPrice)}}<input v-model="uniform" inputmode="decimal" :disabled="busy" :placeholder="say(w.unpriced)"/></label><button class="desk-button secondary" :disabled="busy" @click="applyPrice">{{say(b.applyPrice)}}</button></div>
    <div class="shop-bulk-prices"><label v-for="row in displayed" :key="row.product.id"><span><strong>{{tr(row.product.zh,row.product.en)}}</strong><small>{{row.product.price_cents===null?say(w.unpriced):money(row.product.price_cents)}}</small></span><input v-model="row.price" inputmode="decimal" :disabled="busy" :placeholder="say(w.unpriced)" :aria-label="say(w.price)+' · '+tr(row.product.zh,row.product.en)"/></label></div>
    <div v-if="pages>1" class="shop-bulk-pager"><button :disabled="page===0" :aria-label="say(b.previous)" @click="page--"><PhArrowLeft/></button><span>{{formatCopy(b.page,{v0:page+1,v1:pages})}}</span><button :disabled="page>=pages-1" :aria-label="say(b.next)" @click="page++"><PhArrowRight/></button></div>
   </section>
   <section><h3>{{say(b.photos)}}</h3><label class="shop-bulk-label">{{say(b.assignment)}}<select v-model="assignment" :aria-label="say(b.assignment)" :disabled="busy"><option value="match">{{say(b.match)}}</option><option value="shared">{{say(b.shared)}}</option></select></label><p class="shop-notice">{{say(assignment==='match'?b.matchHelp:b.sharedHelp)}}</p>
    <div class="shop-bulk-options"><label><input v-model="onlyMissing" type="checkbox" :disabled="busy"/>{{say(b.onlyMissing)}}</label><label>{{say(b.treatment)}}<select v-model="treatment" :aria-label="say(b.treatment)" :disabled="busy"><option value="append">{{say(b.append)}}</option><option value="replace">{{say(b.replace)}}</option></select></label></div>
    <MediaUpload multiple original :label="say(b.upload)" :disabled="busy" @select="addPhotos"/>
    <div v-for="p in shownPhotos" :key="p.key" class="shop-bulk-photo"><img :src="p.url" :alt="p.file.name"/><div><strong>{{p.file.name}}</strong><select v-if="assignment==='match'" v-model="p.target" :aria-label="say(b.target)+' · '+p.file.name" :disabled="busy"><option value="">{{say(b.choose)}}</option><option v-for="row in rows" :key="row.product.id" :value="row.product.id">{{row.product.code}} · {{tr(row.product.zh,row.product.en)}}</option></select><small v-if="onlyMissing&&rows.find(r=>r.product.id===p.target)?.product.images.length">{{say(b.skipped)}}</small></div><button :disabled="busy" :aria-label="say(w.remove)+' · '+p.file.name" @click="removePhoto(p.key)"><PhTrash/></button></div>
    <div v-if="photoPages>1" class="shop-bulk-pager"><button :disabled="photoPage===0" :aria-label="say(b.previous)" @click="photoPage--"><PhArrowLeft/></button><span>{{formatCopy(b.page,{v0:photoPage+1,v1:photoPages})}}</span><button :disabled="photoPage>=photoPages-1" :aria-label="say(b.next)" @click="photoPage++"><PhArrowRight/></button></div>
   </section>
   <section class="shop-bulk-summary"><h3>{{say(b.preview)}}</h3><p>{{formatCopy(b.priceChanges,{v0:priceChanges})}}</p><p>{{formatCopy(b.photoChanges,{v0:photoChanges})}}</p><div v-for="row in displayed.filter(r=>photosFor(r).length)" :key="row.product.id" class="shop-bulk-preview"><strong>{{row.product.code||tr(row.product.zh,row.product.en)}}</strong><small>{{formatCopy(b.currentPhotos,{v0:row.product.images.length})}} · {{formatCopy(b.newPhotos,{v0:photosFor(row).length})}}</small><div><img v-for="p in photosFor(row)" :key="p.key" :src="p.url" :alt="p.file.name"/></div></div></section>
   <p v-if="progress" role="status" class="shop-notice">{{progress}}</p><p v-if="error" role="alert" class="shop-error">{{error}}</p>
  </div>
  <template #footer><button class="desk-button primary" :disabled="busy||!hasChanges" @click="save">{{say(hasChanges?b.save:b.nothing)}}</button></template>
 </SlideOver>
</template>
