<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { PhArrowLeft, PhArrowRight, PhArrowsOutSimple } from "@phosphor-icons/vue";
import { media, tr } from "../state";
import { reducedMotion } from "../ui";
import PhotoViewer from "./PhotoViewer.vue";
const photos = [
  { image: "studio-04", zh: "窗边的一张桌子，留给慢慢做手工的你", en: "A table by the window, and time to make" },
  { image: "studio-02", zh: "白色工作台与越拼越满的作品墙", en: "White worktables and a wall full of things we love" },
  { image: "studio-08", zh: "藏在小屋角落里的可爱", en: "Lovely little things around the room" },
  { image: "studio-06", zh: "选一抹喜欢的颜色开始", en: "Start with a colour you love" },
  { image: "studio-07", zh: "准备好工具，慢慢拼", en: "Tools ready, take your time" },
  { image: "studio-11", zh: "把作品变成随身小物", en: "Turn your piece into something to carry with you" },
];
const viewport = ref<HTMLElement>();
const viewer = ref<InstanceType<typeof PhotoViewer>>();
const current = ref(0);
let intended = 0, timer: ReturnType<typeof setTimeout>, observer: ResizeObserver | undefined;
function scrolled() {
  if (!viewport.value) return;
  current.value = Math.max(0, Math.min(5, Math.round(viewport.value.scrollLeft / viewport.value.clientWidth)));
  clearTimeout(timer);
  timer = setTimeout(() => { intended = current.value; }, 150);
}
function move(delta: number) {
  intended = Math.max(0, Math.min(5, intended + delta));
  viewport.value?.scrollTo({ left: intended * viewport.value.clientWidth, behavior: reducedMotion() ? "instant" : "smooth" });
}
onMounted(async () => {
  await nextTick();
  observer = new ResizeObserver(() => {
    viewport.value?.scrollTo({ left: current.value * viewport.value.clientWidth, behavior: "instant" });
    intended = current.value;
  });
  if (viewport.value) observer.observe(viewport.value);
});
onBeforeUnmount(() => { observer?.disconnect(); clearTimeout(timer); });
</script>
<template>
  <div class="vision-carousel">
    <div ref="viewport" class="vision-carousel-window" tabindex="0" role="region" :aria-label="tr('工作室照片，可左右滑动', 'Studio photographs. Swipe or use the arrow keys.')" @scroll.passive="scrolled" @pointerdown="intended = current" @keydown.left.prevent="move(-1)" @keydown.right.prevent="move(1)">
      <figure v-for="photo in photos" :key="photo.image"><img :src="media(photo.image)" :alt="tr(photo.zh,photo.en)" width="1080" height="1440" loading="lazy" draggable="false" /></figure>
    </div>
    <button class="vision-carousel-expand icon-button" :aria-label="tr('放大这张照片', 'Enlarge this photograph')" @click="viewer?.open(current)"><PhArrowsOutSimple :size="22" /></button>
    <div class="vision-carousel-bottom"><p>{{ tr(photos[current].zh,photos[current].en) }}</p><div class="vision-carousel-controls"><button class="icon-button" :disabled="current === 0" :aria-label="tr('上一张空间照片', 'Previous studio photo')" @click="move(-1)"><PhArrowLeft /></button><span aria-live="polite">{{ current + 1 }} / 6</span><button class="icon-button" :disabled="current === 5" :aria-label="tr('下一张空间照片', 'Next studio photo')" @click="move(1)"><PhArrowRight /></button></div></div>
    <PhotoViewer ref="viewer" :photos="photos" />
  </div>
</template>
