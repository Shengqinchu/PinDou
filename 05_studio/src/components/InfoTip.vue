<script setup lang="ts">
import { nextTick,onBeforeUnmount,ref,useId,watch } from 'vue';
import { PhInfo } from '@phosphor-icons/vue';
defineProps<{label:string}>();
const id=useId(),trigger=ref<HTMLButtonElement>(),panel=ref<HTMLElement>();
const open=ref(false),pinned=ref(false),portal=ref<HTMLElement|string>('body');
const position=ref({left:'0px',top:'0px',maxHeight:'none'});
let closeTimer:ReturnType<typeof setTimeout>|undefined;
function place(){
  if(!trigger.value||!panel.value)return;
  const anchor=trigger.value.getBoundingClientRect(),box=panel.value.getBoundingClientRect();
  const view=window.visualViewport,left=view?.offsetLeft||0,top=view?.offsetTop||0;
  const width=view?.width||innerWidth,height=view?.height||innerHeight;
  const x=Math.max(left+12,Math.min(anchor.right-box.width,left+width-box.width-12));
  const below=anchor.bottom+8,above=anchor.top-box.height-8;
  const y=below+box.height<=top+height-12?below:Math.max(top+12,above);
  position.value={left:`${x}px`,top:`${y}px`,maxHeight:`${Math.max(80,height-24)}px`};
}
async function show(){
  clearTimeout(closeTimer);
  portal.value=trigger.value?.closest('dialog')||'body';
  open.value=true;await nextTick();place();
}
function close(){clearTimeout(closeTimer);open.value=false;pinned.value=false;}
function leave(){if(!pinned.value)closeTimer=setTimeout(close,150);}
function stay(){clearTimeout(closeTimer);}
function toggle(){if(pinned.value)close();else{pinned.value=true;void show();}}
function outside(event:Event){
  if(!trigger.value?.contains(event.target as Node)&&!panel.value?.contains(event.target as Node))close();
}
function key(event:Event){if(event instanceof KeyboardEvent&&event.key==='Escape'&&open.value){event.stopPropagation();event.preventDefault();close();}}
watch(open,value=>{
  const action=value?'addEventListener':'removeEventListener';
  document[action]('pointerdown',outside,true);document[action]('keydown',key,true);
  window[action]('resize',place);window[action]('scroll',place,true);
  window.visualViewport?.[action]('resize',place);window.visualViewport?.[action]('scroll',place);
});
onBeforeUnmount(()=>{
  clearTimeout(closeTimer);document.removeEventListener('pointerdown',outside,true);document.removeEventListener('keydown',key,true);
  window.removeEventListener('resize',place);window.removeEventListener('scroll',place,true);
  window.visualViewport?.removeEventListener('resize',place);window.visualViewport?.removeEventListener('scroll',place);
});
</script>
<template>
  <span class="info-tip" @pointerenter="event=>{if(event.pointerType==='mouse')show()}" @pointerleave="leave">
    <button ref="trigger" type="button" class="info-tip-trigger" :aria-label="label" :aria-describedby="open?id:undefined" :aria-expanded="open" @focus="show" @blur="leave" @click="toggle"><PhInfo :size="18"/></button>
    <Teleport :to="portal"><div v-if="open" :id="id" ref="panel" role="tooltip" class="info-tip-panel" :style="position" @pointerenter="stay" @pointerleave="leave"><slot/></div></Teleport>
  </span>
</template>
