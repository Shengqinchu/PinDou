<script setup lang="ts">
import LiftTitle from './LiftTitle.vue';
import { computed, ref } from 'vue';
import { PhArrowUpRight } from '@phosphor-icons/vue';
import defaults from '../content/components-BeadingProcess.json';
import { contentModule, asset } from '../content-store';
import { say } from '../state';
import StudioImage from './StudioImage.vue';
import PhotoViewer from './PhotoViewer.vue';
import BrandMotif from './BrandMotif.vue';
const copy=contentModule('components-BeadingProcess',defaults);
const viewer=ref<InstanceType<typeof PhotoViewer>>();
// Ironing and keepsakes are one step since 2026-10-21 (owner request); the mirror guide shows both.
const photoKeys=['pattern','tools','making','choices'] as const;
const photos=computed(()=>photoKeys.map(key=>({image:'process-'+key,src:asset('process-'+key).src,zh:copy[`${key}Alt`][0],en:copy[`${key}Alt`][1]})));
const steps=computed(()=>[
 {title:copy.patternTitle,body:copy.patternIntro,extra:copy.patternDetail,photos:['pattern']},
 {title:copy.toolsTitle,body:copy.toolsBody,photos:['tools']},
 {title:copy.makingTitle,body:copy.makingBody,photos:['making']},
 {title:copy.choicesTitle,body:copy.choicesBody,photos:['choices']},
]);
</script>
<template>
  <section id="process" class="beading-process vision-detail-section">
    <header class="process-heading"><LiftTitle as="h2" :text="say(copy.title)"/><BrandMotif kind="bone" interactive /></header>
    <ol class="process-steps"><li v-for="(step,i) in steps" :key="i" class="process-step">
      <div class="process-copy"><span class="process-number">{{String(i+1).padStart(2,'0')}}</span><h3>{{say(step.title)}}</h3><p>{{say(step.body)}}</p><p v-if="step.extra">{{say(step.extra)}}</p><a v-if="i===1" class="text-link" :href="say(copy.toolsUrl)" target="_blank" rel="noreferrer">{{say(copy.toolsLink)}}<PhArrowUpRight/></a></div>
      <div class="process-photos"><button v-for="key in step.photos" :key="key" class="process-photo" :aria-label="say(copy.photoLabel)+' · '+say((copy as Record<string,string[]>)[key+'Alt'])" @click="viewer?.open(photoKeys.indexOf(key as typeof photoKeys[number]))"><StudioImage :name="'process-'+key" :alt="say((copy as Record<string,string[]>)[key+'Alt'])" sizes="(max-width:760px) 90vw, 400px" /></button></div>
    </li></ol>
    <div class="process-invitation"><p>{{say(copy.booked)}}</p><p>{{say(copy.notBooked)}}</p><RouterLink to="/visit" class="button button-outline">{{say(copy.visit)}}<PhArrowUpRight/></RouterLink></div>
    <PhotoViewer ref="viewer" :photos="photos" />
  </section>
</template>
