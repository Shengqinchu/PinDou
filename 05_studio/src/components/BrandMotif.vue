<script setup lang="ts">
import { asset, contentModule } from "../content-store";
import { ref,onMounted,onBeforeUnmount } from 'vue';
import { installMotif } from '../motif';
import { say } from '../state';
import defaults from '../content/components-BrandMotif.json';
const copy=contentModule('components-BrandMotif',defaults);
const props=withDefaults(defineProps<{ kind?: "puppy" | "star" | "heart" | "bone"; interactive?:boolean }>(), {
  kind: "puppy",
});
const base = import.meta.env.BASE_URL;
const root=ref<HTMLElement>();let stop:(()=>void)|undefined;
onMounted(()=>{if(root.value&&props.interactive)stop=installMotif(root.value);});
onBeforeUnmount(()=>stop?.());
</script>
<template>
  <component :is="interactive?'button':'span'" ref="root" class="puppy-motif" :class="[kind,{'motif-interactive':interactive}]" :type="interactive?'button':undefined" :aria-label="interactive?say(copy[kind]):undefined" :aria-hidden="!interactive?true:undefined"
    ><span class="motif-float"><span class="motif-touch"><span class="motif-window"
    ><img
      :src="kind === 'puppy' ? asset('brand-puppy').src : `${base}studio-brand/logo-zh.jpg`"
      alt=""
      width="1267"
      height="1267"
  /></span></span></span></component>
</template>
<style scoped>
:where(.puppy-motif) {
  position: relative;
  display: inline-block;
  width: 80px;
  aspect-ratio: 360/205;
  padding:0;
  overflow: visible;
  mix-blend-mode: multiply;
  flex-shrink: 0;
}
.motif-float,.motif-touch,.motif-window { display:block; width:100%; height:100%; }
.motif-window { position:relative;overflow:hidden; }
.motif-float { position:absolute;inset:0; }
.motif-interactive { touch-action:manipulation; }
/* Enlarge the hit area without changing the atlas crop's aspect ratio. */
.motif-interactive::after { content:"";position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:max(100%,44px);height:max(100%,44px); }
.puppy-motif img {
  position: absolute;
  width: 351.94%;
  max-width: none;
  top: -225%;
  left: -67%;
  height: auto;
}
.puppy { aspect-ratio: 1.62; }
.puppy img { width: 148%; left: -22%; top: -72%; }
:where(.star) {
  width: 48px;
  aspect-ratio: 190/190;
}
.star img {
  width: 666.84%;
  top: -282%;
  left: -21%;
}
:where(.heart) {
  width: 42px;
  aspect-ratio: 126/108;
}
.heart img {
  width: 1005.55%;
  top: -603.7%;
  left: -896.8%;
}
:where(.bone) {
  width: 75px;
  aspect-ratio: 277/175;
}
.bone img {
  width: 457.4%;
  top: -309%;
  left: -224%;
}
</style>
