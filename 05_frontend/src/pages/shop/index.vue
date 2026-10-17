<script setup lang="ts">
import {computed,ref,shallowRef} from 'vue';
import {onShow} from '@dcloudio/uni-app';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import {useStudioNative} from '../../utils/studio-native';
import {studioWords} from '../../utils/studio-content';
import {amount,hasVariantPrices,imageUrl,intro,loadCatalog,minimumPrice,type ShopCatalog,type ShopProduct} from '../../utils/shop-catalog';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const words=(key:string)=>say(studioWords('miniapp',key));
const tr=(zh:string,en:string)=>language.value==='en'?en||zh:zh||en;
type Section='home'|'finished'|'services';
const sections:{id:Section;key:string}[]=[{id:'home',key:'shop_home'},{id:'finished',key:'shop_finished'},{id:'services',key:'shop_services'}];
const catalog=shallowRef<ShopCatalog|null>(null),loading=ref(true),failed=ref(false),section=ref<Section>('home'),root=ref('kits'),leaf=ref('kits'),resetKey=ref(0);
const roots=computed(()=>catalog.value?.categories.filter(c=>!c.parent_id)||[]);
const children=computed(()=>catalog.value?.categories.filter(c=>c.parent_id===root.value)||[]);
const visible=computed(()=>(catalog.value?.products||[]).filter(p=>p.shop_collection===section.value&&(section.value!=='home'||p.shop_category_id===leaf.value)));
async function load(force=false){
 failed.value=false;if(!catalog.value)loading.value=true;
 try{
  catalog.value=await loadCatalog(force);
  // Keep the website's default (kits) and fall back to the first category.
  if(!catalog.value.categories.some(c=>c.id===leaf.value)){const first=roots.value[0];root.value=first?.id||'';leaf.value=children.value[0]?.id||first?.id||'';}
 }catch{failed.value=!catalog.value;}
 finally{loading.value=false;}
}
onShow(()=>void load());
function pickSection(id:Section){if(section.value!==id){section.value=id;resetKey.value++;}}
function pickRoot(id:string){root.value=id;const first=catalog.value?.categories.find(c=>c.parent_id===id);leaf.value=first?.id||id;resetKey.value++;}
function pickLeaf(id:string){leaf.value=id;resetKey.value++;}
function open(p:ShopProduct){uni.navigateTo({url:'/pages/shop/item?id='+encodeURIComponent(p.id)});}
const price=(p:ShopProduct)=>p.price_cents===null?'':amount(minimumPrice(p));
</script>
<template>
 <StudioShell id="studio-shop-shell" fitted :reset-key="resetKey" :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" @language="changeLanguage">
  <view class="studio-native-main studio-shop">
   <text class="studio-native-title">{{words('shop_title')}}</text>
   <view class="studio-shop-tabs"><button v-for="item in sections" :key="item.id" :class="{'studio-shop-tab--active':section===item.id}" hover-class="studio-native-pressed" :aria-pressed="section===item.id" @tap="pickSection(item.id)">{{words(item.key)}}</button></view>
   <text v-if="loading" class="studio-native-body studio-native-small">{{words('shop_loading')}}</text>
   <view v-else-if="failed" class="studio-native-section"><text class="studio-native-error">{{words('generic_error')}}</text><button class="studio-native-secondary" hover-class="studio-native-pressed" @tap="load(true)"><StudioGlyph name="refresh" :size="18"/><text>{{words('shop_retry')}}</text></button></view>
   <view v-else class="studio-shop-layout" :class="{'studio-shop-layout--flat':section!=='home'}">
    <view v-if="section==='home'" class="studio-shop-categories">
     <view v-for="c in roots" :key="c.id" class="studio-shop-category">
      <button class="studio-shop-root" :class="{'studio-shop-root--active':root===c.id}" hover-class="studio-native-pressed" @tap="pickRoot(c.id)">{{tr(c.zh,c.en)}}</button>
      <view v-if="root===c.id&&children.length" class="studio-shop-children"><button v-for="child in children" :key="child.id" :class="{'studio-shop-child--active':leaf===child.id}" hover-class="studio-native-pressed" @tap="pickLeaf(child.id)">{{tr(child.zh,child.en)}}</button></view>
     </view>
    </view>
    <view class="studio-shop-grid" :class="{'studio-shop-grid--services':section==='services'}">
     <text v-if="!visible.length" class="studio-native-body studio-native-small">{{words('shop_empty')}}</text>
     <view v-for="p in visible" :key="p.id" class="studio-shop-card" hover-class="studio-native-pressed" @tap="open(p)">
      <view class="studio-shop-card-photo"><image v-if="p.images[0]" :src="imageUrl(p.images[0],section==='services'?480:320)" mode="aspectFit" lazy-load/><view v-else class="studio-shop-placeholder"><text class="studio-shop-placeholder-code">{{p.code||tr(p.zh,p.en)}}</text><text>{{words('shop_no_photo')}}</text></view></view>
      <view class="studio-shop-card-body">
       <text class="studio-shop-name">{{tr(p.zh,p.en)}}</text>
       <text v-if="section!=='home'" class="studio-shop-intro">{{intro(tr(p.detailZh||'',p.detailEn||''))}}</text>
       <text v-if="p.price_cents!==null" class="studio-shop-price">{{price(p)}}<text class="studio-shop-price-unit">CAD</text><text v-if="hasVariantPrices(p)" class="studio-shop-price-unit">{{words('shop_from')}}</text></text>
       <text v-else class="studio-shop-unpriced">{{words('shop_unpriced')}}</text>
      </view>
     </view>
    </view>
   </view>
   <text class="studio-native-body studio-native-small">{{words('shop_note')}}</text>
  </view>
 </StudioShell>
</template>
