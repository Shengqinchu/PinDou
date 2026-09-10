<script setup lang="ts">
import { ref,onMounted,onBeforeUnmount } from 'vue';
import { gsap } from 'gsap';
import { reducedMotion,onMotionPreferenceChange } from '../motion-preference';
defineProps<{view:string;label:string}>();
const frame=ref<HTMLElement>();let animation:gsap.core.Tween|undefined,observer:ResizeObserver|undefined,stop:()=>void,width=0;
function reset(){animation?.kill();frame.value?.style.removeProperty('height');frame.value?.classList.remove('is-swapping');}
function beforeLeave(element:Element){
 (element as HTMLElement).inert=true;element.setAttribute('aria-hidden','true');
 if(!frame.value||reducedMotion())return;
 const height=frame.value.getBoundingClientRect().height;animation?.kill();frame.value.style.height=height+'px';frame.value.classList.add('is-swapping');
}
function enter(element:Element){
 if(!frame.value||reducedMotion()){reset();return;}
 animation=gsap.to(frame.value,{height:(element as HTMLElement).offsetHeight,duration:.56,ease:'studio-travel',onComplete:reset});
}
onMounted(()=>{stop=onMotionPreferenceChange(reset);observer=new ResizeObserver(([entry])=>{if(Math.abs(entry.contentRect.width-width)>1)reset();width=entry.contentRect.width;});if(frame.value){width=frame.value.offsetWidth;observer.observe(frame.value);}});
onBeforeUnmount(()=>{reset();observer?.disconnect();stop?.();});
</script>
<template><div ref="frame" class="flow-picker-window"><Transition name="picker-swap" mode="out-in" @before-leave="beforeLeave" @enter="enter" @after-enter="(el:Element)=>(el as HTMLElement).focus({preventScroll:true})"><section :key="view" class="flow-picker-pane" :data-picker-view="view" :aria-label="label" tabindex="-1" role="group"><slot/></section></Transition></div></template>
<style>
.flow-picker-window{overflow:visible;}.flow-picker-window.is-swapping{overflow:clip;overflow-clip-margin:10px;}.flow-picker-pane{outline:none;padding:8px 3px 8px;}.picker-swap-leave-active{transition:opacity .42s var(--control-ease),transform .42s var(--control-ease);pointer-events:none;}.picker-swap-enter-active{transition:opacity .56s var(--control-ease),transform .56s var(--control-ease);}.picker-swap-leave-to{opacity:0;transform:translateY(-10px)}.picker-swap-enter-from{opacity:0;transform:translateY(18px)}
html[data-motion="reduced"] :is(.picker-swap-leave-active,.picker-swap-enter-active){transition:none;transform:none;opacity:1}
</style>
