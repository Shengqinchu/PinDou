<script setup lang="ts">
import contentPhotos from "../content/data-components-StudioCarousel-photos.json";

import copyText from "../content/components-StudioCarousel.json";
import { say } from "../state";

import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import {
  PhArrowLeft,
  PhArrowRight,
  PhArrowsOutSimple,
} from "@phosphor-icons/vue";
import { media, tr } from "../state";
import { reducedMotion } from "../ui";
import PhotoViewer from "./PhotoViewer.vue";
const photos = contentPhotos;
const viewport = ref<HTMLElement>();
const viewer = ref<InstanceType<typeof PhotoViewer>>();
const current = ref(0);
let intended = 0,
  timer: ReturnType<typeof setTimeout>,
  observer: ResizeObserver | undefined;
function scrolled() {
  if (!viewport.value) return;
  current.value = Math.max(
    0,
    Math.min(
      5,
      Math.round(viewport.value.scrollLeft / viewport.value.clientWidth),
    ),
  );
  clearTimeout(timer);
  timer = setTimeout(() => {
    intended = current.value;
  }, 150);
}
function move(delta: number) {
  intended = Math.max(0, Math.min(5, intended + delta));
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
});
onBeforeUnmount(() => {
  observer?.disconnect();
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
      <figure v-for="photo in photos" :key="photo.image">
        <img
          :src="media(photo.image)"
          :alt="tr(photo.zh, photo.en)"
          width="1080"
          height="1440"
          loading="lazy"
          draggable="false"
        />
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
        ><span aria-live="polite">{{ current + 1 }} / 6</span
        ><button
          class="icon-button"
          :disabled="current === 5"
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
