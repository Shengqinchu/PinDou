<script setup lang="ts">
import { ref,computed,nextTick,onBeforeUnmount,useId,watch } from 'vue';
import { PhUsers,PhCaretDown,PhCheck } from '@phosphor-icons/vue';
import { say } from '../state';
import { copy,guestCount } from './copy';
const props=defineProps<{modelValue:number;maximum:number;disabled?:boolean}>();
const emit=defineEmits<{'update:modelValue':[value:number]}>();
const id=useId(),open=ref(false),active=ref(1),trigger=ref<HTMLButtonElement>(),panel=ref<HTMLElement>(),portal=ref<HTMLElement|string>('body');
const maximum=computed(()=>Math.max(1,Math.min(99,props.maximum)));
const position=ref({left:'0px',top:'0px',width:'200px',maxHeight:'240px'});
function place(){if(!trigger.value)return;const box=trigger.value.getBoundingClientRect(),view=visualViewport,x=view?.offsetLeft||0,y=view?.offsetTop||0,w=view?.width||innerWidth,h=view?.height||innerHeight;const height=Math.min(264,h-24,maximum.value*44+12),below=y+h-box.bottom-8,above=box.top-y-8;const top=below>=Math.min(height,above)?box.bottom+6:Math.max(y+12,box.top-height-6);position.value={left:Math.max(x+12,Math.min(box.left,x+w-Math.min(box.width,w-24)-12))+'px',top:top+'px',width:Math.min(box.width,w-24)+'px',maxHeight:Math.min(height,y+h-top-12)+'px'};}
async function focus(){await nextTick();const option=panel.value?.querySelector<HTMLButtonElement>(`[data-count="${active.value}"]`);option?.focus({preventScroll:true});option?.scrollIntoView({block:'nearest'});}
async function show(){if(props.disabled)return;active.value=Math.min(maximum.value,Math.max(1,props.modelValue));portal.value=trigger.value?.closest('dialog')||'body';open.value=true;await nextTick();place();void focus();}
function close(restore=false){open.value=false;if(restore)trigger.value?.focus({preventScroll:true});}
function select(value:number){emit('update:modelValue',value);close(true);}
function key(event:KeyboardEvent){if(event.key==='Escape'){event.preventDefault();event.stopPropagation();close(true);return;}if(event.key==='Tab'){close(true);return;}const value=event.key==='ArrowDown'?Math.min(maximum.value,active.value+1):event.key==='ArrowUp'?Math.max(1,active.value-1):event.key==='Home'?1:event.key==='End'?maximum.value:0;if(value){event.preventDefault();active.value=value;void focus();}}
function outside(event:Event){if(!trigger.value?.contains(event.target as Node)&&!panel.value?.contains(event.target as Node))close();}
watch(open,value=>{const action=value?'addEventListener':'removeEventListener';document[action]('pointerdown',outside,true);window[action]('resize',place);window[action]('scroll',place,true);visualViewport?.[action]('resize',place);});
watch(()=>props.disabled,value=>{if(value)close();});
onBeforeUnmount(()=>{document.removeEventListener('pointerdown',outside,true);window.removeEventListener('resize',place);window.removeEventListener('scroll',place,true);visualViewport?.removeEventListener('resize',place);});
</script>
<template>
 <div class="visit-guest-select"><span :id="id+'-label'">{{say(copy.guests)}}</span><button ref="trigger" class="visit-guest-trigger" type="button" :aria-labelledby="id+'-label '+id+'-value'" aria-haspopup="listbox" :aria-expanded="open" :aria-controls="open?id:undefined" :disabled="disabled" @click="open?close():show()" @keydown.down.prevent="show" @keydown.up.prevent="show"><PhUsers/><span :id="id+'-value'">{{guestCount(modelValue)}}</span><PhCaretDown/></button></div>
 <Teleport :to="portal"><div v-if="open" :id="id" ref="panel" class="visit-guest-options" role="listbox" :aria-label="say(copy.guests)" :style="position" @keydown="key"><button v-for="n in maximum" :key="n" :data-count="n" type="button" role="option" :aria-selected="modelValue===n" :tabindex="active===n?0:-1" @focus="active=n" @click="select(n)">{{guestCount(n)}}<PhCheck v-if="modelValue===n"/></button></div></Teleport>
</template>
