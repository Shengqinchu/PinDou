<script setup lang="ts">
import { computed,onBeforeUnmount,onMounted,watch } from 'vue';
import { reducedMotion,onMotionPreferenceChange } from '../motion-preference';
const props=withDefaults(defineProps<{text:string|string[];as?:'h1'|'h2';emphasisLast?:boolean}>(),{as:'h1'});
const lines=computed(()=>Array.isArray(props.text)?props.text:props.text.split('\n'));
// Keep Latin words together; CJK and emoji remain complete graphemes.
const segmenter=typeof Intl.Segmenter==='function'?new Intl.Segmenter(undefined,{granularity:'grapheme'}):undefined;
const graphemes=(text:string)=>segmenter?[...segmenter.segment(text)].map(s=>s.segment):Array.from(text);
const words=computed(()=>lines.value.map(line=>(line.match(/[A-Za-z\u00c0-\u024f\d'’\-]+|\s+|[^A-Za-z\u00c0-\u024f\d'’\-\s]+/gu)||[]).flatMap(part=>/^[A-Za-z\u00c0-\u024f\d]/u.test(part)||/^\s/u.test(part)?[part]:graphemes(part))));
const effects=new Map<HTMLElement,Animation>();
const hover=matchMedia('(hover:hover) and (pointer:fine)');
function reset(){for(const effect of effects.values())effect.cancel();effects.clear();}
function lift(event:PointerEvent){
 if(event.pointerType==='touch'||event.buttons||!hover.matches||reducedMotion()||document.hidden)return;
 const hit=(event.target as Element).closest<HTMLElement>('.lift-hit');
 if(!hit||hit.contains(event.relatedTarget as Node))return;
 const glyph=hit.firstElementChild as HTMLElement;
 if(!glyph?.animate)return;
 const current=getComputedStyle(glyph).transform;effects.get(glyph)?.cancel();
 const height=Math.min(12,Math.max(4,parseFloat(getComputedStyle(glyph).fontSize)*.18));
 const effect=glyph.animate([{transform:current==='none'?'translateY(0)':current,offset:0,easing:'cubic-bezier(.2,.7,.3,1)'},{transform:`translateY(${-height}px)`,offset:.32,easing:'cubic-bezier(.35,0,.2,1)'},{transform:'translateY(0)',offset:1}],{duration:560,id:'studio-letter-lift'});
 effects.set(glyph,effect);effect.onfinish=()=>{if(effects.get(glyph)===effect)effects.delete(glyph);};
}
let stop:()=>void;
function hidden(){if(document.hidden)reset();}
onMounted(()=>{stop=onMotionPreferenceChange(reset);document.addEventListener('visibilitychange',hidden);});
watch(()=>props.text,reset);onBeforeUnmount(()=>{reset();stop?.();document.removeEventListener('visibilitychange',hidden);});
</script>
<template>
 <component :is="as" class="lift-title" :aria-label="lines.join(' ')" @pointerover="lift"><span v-for="(line,i) in words" :key="lines[i]" class="lift-line" :class="{'lift-emphasis':emphasisLast&&i===words.length-1}" aria-hidden="true"><template v-for="(word,j) in line" :key="j"><span v-if="/^\s/u.test(word)" class="lift-space">{{word}}</span><span v-else class="lift-word"><span v-for="(letter,k) in graphemes(word)" :key="k" class="lift-hit"><span class="lift-glyph">{{letter}}</span></span></span></template></span></component>
</template>
<style>
.lift-title{font-kerning:none;}.lift-title>.lift-line{display:block;}.lift-word{display:inline;white-space:nowrap;}.lift-space{white-space:pre-wrap;}.lift-hit,.lift-glyph{display:inline-block;}.lift-hit{vertical-align:baseline;}.lift-glyph{pointer-events:none;transform:translateY(0);}.lift-emphasis{font-style:italic;}
html[lang="zh-CN"] .lift-emphasis,html[lang="zh"] .lift-emphasis{font-style:normal;}
html[data-motion="reduced"] .lift-glyph{transform:none!important;}
</style>
