<script setup lang="ts">
import { ref,nextTick,onBeforeUnmount } from 'vue';
import { PhCopy,PhCheck } from '@phosphor-icons/vue';
import { writeClipboard } from '../clipboard';
import { contentModule } from '../content-store';
import defaults from '../content/components-CopyContact.json';
import { say } from '../state';
import { notify } from '../ui';
const props=defineProps<{value:string;prefix?:string}>(),words=contentModule('components-CopyContact',defaults);
const done=ref(false),manual=ref(false),input=ref<HTMLInputElement>();let timer:ReturnType<typeof setTimeout>;
async function copy(){manual.value=false;done.value=await writeClipboard(props.value);if(done.value){notify(words.copied[0],words.copied[1]);clearTimeout(timer);timer=setTimeout(()=>done.value=false,3500);}else{manual.value=true;await nextTick();input.value?.focus({preventScroll:true});input.value?.select();}}
onBeforeUnmount(()=>clearTimeout(timer));
</script>
<template><span class="copy-contact"><button type="button" class="copy-contact-button" :aria-label="say(done?words.copied:words.copy)+' '+value" :title="say(words.copy)" @click="copy"><slot/><span>{{prefix}}{{value}}</span><PhCheck v-if="done" :size="15"/><PhCopy v-else :size="15"/></button><span v-if="manual" class="copy-contact-manual" role="status">{{say(words.manual)}}<input ref="input" :value="value" readonly :aria-label="say(words.copy)" @click="($event.target as HTMLInputElement).select()" /></span></span></template>
