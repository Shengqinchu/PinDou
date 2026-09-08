<script setup lang="ts">
import { contentPhotos, contentModule } from "../content-store";
const copyText = contentModule("components-StudioCarousel", copyTextDefault);

import photoDefaults from "../content/data-components-StudioCarousel-photos.json";

import copyTextDefault from "../content/components-StudioCarousel.json";
import { say } from "../state";

import StudioImage from "./StudioImage.vue";
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import {
  PhArrowLeft,
  PhArrowRight,
  PhArrowsOutSimple,
} from "@phosphor-icons/vue";
import { media, tr } from "../state";
import { reducedMotion } from "../ui";
import PhotoViewer from "./PhotoViewer.vue";
const photos = contentPhotos("carousel-labels",photoDefaults);
const viewport = ref<HTMLElement>();
const viewer = ref<InstanceType<typeof PhotoViewer>>();
const current = ref(0);
const nearby = ref(false);
let visibility: IntersectionObserver | undefined;
let intended = 0,
  timer: ReturnType<typeof setTimeout>,
  observer: ResizeObserver | undefined;
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
    intended = current.value;
  }, 150);
}
function move(delta: number) {
  intended = Math.max(0, Math.min(photos.length - 1, intended + delta));
  viewport.value?.scrollTo({
    left: intended * viewport.value.clientWidth,
    behavior: reducedMotion() ? "instant" : "smooth",
  });
}
onMounted(async () => {
  await nextTick();
  observer = new ResizeObserver(() => {
    viewport.value?.scrollTo({
      left: current.value * viewport.value.clientWidth,
      behavior: "instant",
    });
    intended = current.value;
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
      @pointerdown="intended = current"
      @keydown.left.prevent="move(-1)"
      @keydown.right.prevent="move(1)"
    >
      <figure v-for="(photo, i) in photos" :key="photo.image">
        <StudioImage v-if="nearby && Math.abs(i-current) <= 1" :name="photo.image" :alt="tr(photo.zh, photo.en)" sizes="(max-width: 760px) 100vw, 560px" draggable="false" />
      </figure>
    </div>

    <div class="vision-carousel-bottom">
      <div class="vision-carousel-controls">
        <button
          class="icon-button"
          :disabled="current === 0"
          :aria-label="say(copyText.previous_studio_photo_d0e31b)"
          @click="move(-1)"
        >
          <PhArrowLeft /></button
        ><span aria-live="polite">{{ current + 1 }} / {{ photos.length }}</span
        ><button
          class="icon-button"
          :disabled="current === photos.length - 1"
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
