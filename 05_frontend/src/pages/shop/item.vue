<script setup lang="ts">
import {computed,ref,shallowRef} from 'vue';
import {onLoad} from '@dcloudio/uni-app';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import {useStudioNative} from '../../utils/studio-native';
import {studioWords} from '../../utils/studio-content';
import {amount,cachedProduct,hasVariantPrices,imageUrl,loadCatalog,priceRange,type ShopProduct,type ShopVariant} from '../../utils/shop-catalog';
const {language,keyboardOpen,shellStyle,say,t,changeLanguage}=useStudioNative();
const words=(key:string)=>say(studioWords('miniapp',key));
const tr=(zh:string,en:string)=>language.value==='en'?en||zh:zh||en;
const product=shallowRef<ShopProduct|null>(null),variant=ref<ShopVariant|null>(null),failed=ref(false),current=ref(0);
const photos=computed(()=>(product.value?.images||[]).map(src=>imageUrl(src,800)));
const description=computed(()=>product.value?tr(product.value.detailZh||'',product.value.detailEn||''):'');
const price=computed(()=>{
 const p=product.value;if(!p||p.price_cents===null)return '';
 if(variant.value)return amount(variant.value.price_cents??p.price_cents);
 return hasVariantPrices(p)?priceRange(p):amount(p.price_cents);
});
onLoad(async options=>{
 const id=decodeURIComponent(String(options?.id||''));
 product.value=cachedProduct(id)||null;
 if(!product.value){try{product.value=(await loadCatalog()).products.find(p=>p.id===id)||null;}catch{}}
 failed.value=!product.value;
});
function preview(index:number){uni.previewImage({urls:photos.value,current:photos.value[index]});}
function pick(item:ShopVariant){variant.value=variant.value?.id===item.id?null:item;}
function wechat(){uni.setClipboardData({data:say(studioWords('contacts','wechat')),success:()=>uni.showToast({title:t('copied'),icon:'none'})});}
</script>
<template>
 <StudioShell id="studio-shop-item-shell" fitted :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" @language="changeLanguage">
  <view class="studio-native-main studio-shop-item">
   <text v-if="failed" class="studio-native-error">{{words('shop_empty')}}</text>
   <template v-else-if="product">
    <swiper v-if="photos.length" class="studio-shop-gallery" :indicator-dots="photos.length>1" indicator-active-color="#66889e" @change="current=$event.detail.current">
     <swiper-item v-for="(src,index) in photos" :key="src"><image :src="src" mode="aspectFit" class="studio-shop-gallery-image" @tap="preview(index)"/></swiper-item>
    </swiper>
    <view class="studio-native-section">
     <text class="studio-native-title studio-shop-item-title">{{tr(product.zh,product.en)}}</text>
     <text v-if="product.price_cents!==null" class="studio-shop-price studio-shop-item-price">{{price}}<text class="studio-shop-price-unit">CAD</text><text v-if="!variant&&hasVariantPrices(product)&&!price.includes('–')" class="studio-shop-price-unit">{{words('shop_from')}}</text></text>
     <text v-else class="studio-shop-unpriced">{{words('shop_unpriced')}}</text>
    </view>
    <view v-if="product.variants?.length" class="studio-shop-variants"><button v-for="item in product.variants" :key="item.id" class="studio-plan" :class="{'studio-plan--selected':variant?.id===item.id}" hover-class="studio-native-pressed" :aria-pressed="variant?.id===item.id" @tap="pick(item)">{{tr(item.zh,item.en)}}</button></view>
    <text v-if="description" class="studio-native-body studio-shop-description" selectable>{{description}}</text>
    <text class="studio-native-body studio-native-small">{{words('shop_note')}}</text>
   </template>
  </view>
  <template #actions><view class="studio-visit-actions"><button class="studio-native-primary" hover-class="studio-native-pressed" @tap="wechat"><StudioGlyph name="wechat"/><text class="studio-native-primary-label">{{words('shop_contact')}}</text><StudioGlyph name="copy" :size="18"/></button></view></template>
 </StudioShell>
</template>
