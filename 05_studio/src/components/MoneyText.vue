<script setup lang="ts">
import { computed } from 'vue';
const props=defineProps<{text:string}>();
// Presentation only: keep the original amounts, wording and owner overrides.
const parts=computed(()=>{
 const result:{text?:string;amount?:string;currency?:string}[]=[];
 const pattern=/\b(CAD|CNY)\s*(\d[\d,]*(?:\.\d+)?)|(\d[\d,]*(?:\.\d+)?)\s*(CAD|CNY)\b/g;
 let at=0;
 for(const match of props.text.matchAll(pattern)){
  if(match.index!>at)result.push({text:props.text.slice(at,match.index)});
  result.push({amount:match[2]||match[3],currency:match[1]||match[4]});at=match.index!+match[0].length;
 }
 if(at<props.text.length)result.push({text:props.text.slice(at)});
 return result;
});
</script>
<template><span class="money-text"><template v-for="(part,i) in parts" :key="i"><span v-if="part.currency" class="price-amount"><span class="price-number">{{part.amount}}</span>{{' '}}<span class="price-currency">{{part.currency}}</span></span><template v-else>{{part.text}}</template></template></span></template>
<style>
.price-amount{display:inline-flex;align-items:baseline;gap:.2em;white-space:nowrap;font:inherit;vertical-align:baseline;font-variant-numeric:tabular-nums;}.price-currency{font-size:.46em;font-weight:500;line-height:1;letter-spacing:.025em;position:relative;top:.08em;color:inherit;}.price-number{font:inherit;}
</style>
