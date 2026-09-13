<script setup lang="ts">
import { computed } from 'vue';
import { type ShopProduct, shopWords as w } from '../../shop';
import { orderWords as o } from '../../shop-ordering';
import { say } from '../../state';
const props=defineProps<{product:ShopProduct;busy:boolean}>();
function add(kind:'variants'|'choices'){(props.product[kind]??=[]).push({id:'v-'+crypto.randomUUID().slice(0,8),zh:'',en:''})}
function toggleOffer(event:Event){props.product.quantity_offer=(event.target as HTMLInputElement).checked?{quantity:2,price_cents:0}:null}
const offerPrice=computed({get:()=>props.product.quantity_offer?.price_cents?props.product.quantity_offer.price_cents/100:'',set:v=>{if(props.product.quantity_offer)props.product.quantity_offer.price_cents=Math.round(Number(v)*100)}});
</script>
<template>
 <fieldset class="shop-editor-options" :disabled="busy"><legend>{{say(o.variants)}}</legend><p class="shop-notice">{{say(o.optionsHelp)}}</p>
  <div v-for="(v,i) in product.variants||[]" :key="v.id" class="shop-option-editor-row"><label>{{say(o.variantZh)}}<input v-model="v.zh" maxlength="80" required/></label><label>{{say(o.variantEn)}}<input v-model="v.en" maxlength="120" required/></label><button type="button" class="desk-button secondary" @click="product.variants!.splice(i,1)">{{say(w.remove)}}</button></div>
  <button type="button" class="desk-button secondary" :disabled="(product.variants?.length||0)>=100" @click="add('variants')">{{say(o.addVariant)}}</button>
 </fieldset>
 <fieldset class="shop-editor-options" :disabled="busy"><legend>{{say(o.choices)}}</legend>
  <div v-if="product.choices?.length" class="shop-edit-pair"><label>{{say(o.choiceLabelZh)}}<input v-model="product.choiceZh" maxlength="80" required/></label><label>{{say(o.choiceLabelEn)}}<input v-model="product.choiceEn" maxlength="120" required/></label></div>
  <div v-for="(v,i) in product.choices||[]" :key="v.id" class="shop-option-editor-row"><label>{{say(o.variantZh)}}<input v-model="v.zh" maxlength="80" required/></label><label>{{say(o.variantEn)}}<input v-model="v.en" maxlength="120" required/></label><button type="button" class="desk-button secondary" @click="product.choices!.splice(i,1)">{{say(w.remove)}}</button></div>
  <button type="button" class="desk-button secondary" :disabled="(product.choices?.length||0)>=20" @click="add('choices')">{{say(o.addChoice)}}</button>
 </fieldset>
 <fieldset class="shop-editor-options" :disabled="busy"><label class="shop-check"><input type="checkbox" :checked="!!product.quantity_offer" @change="toggleOffer"/>{{say(o.offerEnabled)}}</label>
  <template v-if="product.quantity_offer"><div class="shop-edit-pair"><label>{{say(o.offerQuantity)}}<input v-model.number="product.quantity_offer.quantity" type="number" min="2" max="20" step="1" required/></label><label>{{say(o.offerPrice)}}<input v-model="offerPrice" type="number" min="0.01" max="10000" step="0.01" required/></label></div><p class="shop-notice">{{say(o.offerHelp)}}</p></template>
 </fieldset>
</template>
