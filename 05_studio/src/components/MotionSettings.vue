<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue';
import { contentModule } from '../content-store';
import defaults from '../content/components-MotionSettings.json';
import { say } from '../state';
import { getMotionMode, setMotionMode, systemReducesMotion, onMotionSettingsChange, type MotionMode } from '../motion-preference';
const words=contentModule('components-MotionSettings',defaults);
const selected=ref(getMotionMode()),systemReduced=ref(systemReducesMotion());
const stop=onMotionSettingsChange(()=>{selected.value=getMotionMode();systemReduced.value=systemReducesMotion();});
onBeforeUnmount(stop);
const choices=['system','full','reduced'] as MotionMode[];
</script>
<template>
 <fieldset class="motion-settings"><legend>{{say(words.title)}}</legend>
  <div><button v-for="choice in choices" :key="choice" type="button" :aria-pressed="selected===choice" @click="setMotionMode(choice)">{{say(words[choice])}}</button></div>
  <p>{{say(systemReduced?words.systemReduced:words.systemFull)}}</p>
 </fieldset>
</template>
<style scoped>
.motion-settings {border:0;border-top:1px solid var(--line);padding:22px 0 0;margin:26px 0 0;min-width:0;}
.motion-settings legend {float:left;width:100%;font-size:14px;margin-bottom:12px;}
.motion-settings>div {display:flex;gap:8px;clear:both;}
.motion-settings button {min-height:44px;flex:1;padding:8px;border:1px solid var(--line);border-radius:8px;font-size:13px;}
.motion-settings button[aria-pressed=true] {background:var(--blue);border-color:var(--ink);}
.motion-settings p {font-size:12px;line-height:1.7;color:var(--muted);margin-top:10px;}
</style>
