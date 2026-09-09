<script setup lang="ts">
import { contentPhotos, contentModule } from "../content-store";
const copyText = contentModule("components-StudioCarousel", copyTextDefault);

import photoDefaults from "../content/data-components-StudioCarousel-photos.json";

import copyTextDefault from "../content/components-StudioCarousel.json";
import { say } from "../state";

import StudioImage from "./StudioImage.vue";
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  PhArrowLeft,
  PhArrowRight,
  PhArrowsOutSimple,
} from "@phosphor-icons/vue";
import { media, tr } from "../state";
import { reducedMotion } from "../ui";
import { gsap } from "gsap";
import { onMotionPreferenceChange } from "../motion-preference";
import PhotoViewer from "./PhotoViewer.vue";
const photos = contentPhotos("carousel-labels",photoDefaults);
const viewport = ref<HTMLElement>();
const viewer = ref<InstanceType<typeof PhotoViewer>>();
const current = ref(0);
const targetIndex = ref(0);
const loaded = ref(new Set([0,1]));
function warm(index:number) { for (const i of [index-1,index,index+1]) if(i>=0&&i<photos.length) loaded.value.add(i); }
watch(current,warm);
const nearby = ref(false);
let visibility: IntersectionObserver | undefined;
let intended = 0,
  timer: ReturnType<typeof setTimeout>,
  observer: ResizeObserver | undefined;
let travel: gsap.core.Tween | undefined;
let width = 0;
let stopPreference: (() => void) | undefined;
function stopTravel(releaseSnap=true) {
  travel?.kill(); travel = undefined;
  if (releaseSnap && viewport.value) viewport.value.style.scrollSnapType = '';
}
function userScroll() { stopTravel(); targetIndex.value = intended = current.value; }
function scrolled() {
  if (!viewport.value) return;
  current.value = Math.max(
    0,
    Math.min(
      photos.length - 1,
      Math.round(viewport.value.scrollLeft / viewport.value.clientWidth),
    ),
  );
  clearTimeout(timer);
  timer = setTimeout(() => {
    if (!travel) targetIndex.value = intended = current.value;
  }, 150);
}
function move(delta: number) {
  intended = Math.max(0, Math.min(photos.length - 1, intended + delta));
  targetIndex.value = intended; warm(intended);
  const element = viewport.value;
  if (!element) return;
  stopTravel(false);
  const left = intended * element.clientWidth;
  if (reducedMotion()) { element.style.scrollSnapType = ''; element.scrollLeft = left; scrolled(); return; }
  // Chrome's native smooth-scroll flag cannot disable these explicit frames.
  // Snap remains available for direct touch/trackpad input, outside the tween.
  element.style.scrollSnapType = 'none';
  travel = gsap.to(element, {scrollLeft:left,duration:.82,ease:'studio-travel',overwrite:true,
    onComplete:()=>{travel=undefined;element.style.scrollSnapType='';current.value=intended;},
  });
}
onMounted(async () => {
  await nextTick();
  observer = new ResizeObserver(() => {
    if (!viewport.value || width === viewport.value.clientWidth) return;
    width = viewport.value.clientWidth;
    const target = travel ? intended : current.value;
    stopTravel();
    viewport.value?.scrollTo({
      left: target * viewport.value.clientWidth,
      behavior: "instant",
    });
    targetIndex.value = current.value = intended = target;
  });
  stopPreference = onMotionPreferenceChange(() => {
    if (travel && reducedMotion() && viewport.value) {
      stopTravel(); viewport.value.scrollLeft = intended * viewport.value.clientWidth;
      current.value = intended;
    }
  });
  if (viewport.value) observer.observe(viewport.value);
  if (typeof IntersectionObserver === "undefined") nearby.value = true;
  else {
    visibility = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { nearby.value = true; visibility?.disconnect(); }
    }, {rootMargin:"400px"});
    if(viewport.value)visibility.observe(viewport.value);
  }
});
onBeforeUnmount(() => {
  observer?.disconnect();
  visibility?.disconnect();
  clearTimeout(timer);
  stopTravel(); stopPreference?.();
});
</script>
<template>
  <div class="vision-carousel">
    <div
      ref="viewport"
      class="vision-carousel-window"
      tabindex="0"
      role="region"
      :aria-label="
        say(copyText.studio_photographs_swipe_or_use_the_arrow_9442fa)
      "
      @scroll.passive="scrolled"
      @pointerdown="userScroll"
      @wheel.passive="userScroll"
      @keydown.left.prevent="move(-1)"
      @keydown.right.prevent="move(1)"
    >
      <figure v-for="(photo, i) in photos" :key="photo.image">
        <StudioImage v-if="nearby && loaded.has(i)" :name="photo.image" :alt="tr(photo.zh, photo.en)" sizes="(max-width: 760px) 100vw, 560px" loading="eager" draggable="false" />
      </figure>
    </div>

    <div class="vision-carousel-bottom">
      <div class="vision-carousel-controls">
        <button
          class="icon-button"
          :disabled="targetIndex === 0"
          :aria-label="say(copyText.previous_studio_photo_d0e31b)"
          @click="move(-1)"
        >
          <PhArrowLeft /></button
        ><span aria-live="polite">{{ current + 1 }} / {{ photos.length }}</span
        ><button
          class="icon-button"
          :disabled="targetIndex === photos.length - 1"
          :aria-label="say(copyText.next_studio_photo_c276c9)"
          @click="move(1)"
        >
          <PhArrowRight />
        </button>
      </div>
    </div>
    <PhotoViewer ref="viewer" :photos="photos" />
  </div>
</template>
