<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { foregroundImage, imageWidth, previewURL, imagePrepared, rememberImage } from '../shop-images';
const props = defineProps<{ src: string; alt: string; priority?: boolean }>();
const element = ref<HTMLImageElement>();
const near = ref(false), loaded = ref(false), fallback = ref(false), width = ref(320);
const cached = ref(false);
const source = computed(() => near.value ? (fallback.value ? props.src : previewURL(props.src, width.value)) : undefined);
let intersection: IntersectionObserver | undefined, resize: ResizeObserver | undefined;
let finish: (() => void) | undefined;
function measure() {
  if (element.value) width.value = Math.max(width.value, imageWidth(element.value.getBoundingClientRect().width));
}
function ready() { loaded.value = true; if (source.value) rememberImage(source.value); finish?.(); }
function failed() {
  const image = element.value;
  // WebKit emits error for an <img> with no src, and can deliver that event as
  // IntersectionObserver starts its first request. Only a completed request for
  // the current source can trigger fallback; ignore empty/stale/cancelled loads.
  if (!source.value || !image?.getAttribute('src') || !image.complete) return;
  if (image.currentSrc && image.currentSrc !== new URL(source.value, location.href).href) return;
  finish?.();
  if (!fallback.value && source.value !== props.src) fallback.value = true;
}
watch(source, async value => {
  finish?.(); loaded.value = false;
  if (!value) return;
  cached.value = imagePrepared(value);
  finish = foregroundImage();
  await nextTick();
  if (element.value?.complete && element.value.naturalWidth) ready();
}, { flush: 'pre' });
watch(() => props.src, () => { fallback.value = false; width.value = 320; measure(); });
onMounted(() => {
  measure();
  if ('ResizeObserver' in window) { resize = new ResizeObserver(measure); resize.observe(element.value!); }
  if ('IntersectionObserver' in window) {
    intersection = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { measure(); near.value = true; intersection?.disconnect(); }
    }, { rootMargin: '180px 0px' });
    intersection.observe(element.value!);
  } else near.value = true;
});
onBeforeUnmount(() => { intersection?.disconnect(); resize?.disconnect(); finish?.(); });
</script>
<template>
  <img ref="element" class="shop-product-image" :src="source" :alt="alt" width="600" height="600" :data-loaded="loaded" :data-cached="cached" :fetchpriority="priority ? 'high' : 'auto'" decoding="async" @load="ready" @error="failed"/>
</template>
<style>
.shop-card-preview{background:#f7f9fa;}
.shop-product-image{opacity:0;transition:opacity 160ms ease-out;}
.shop-product-image[data-loaded="true"]{opacity:1;}
.shop-product-image[data-cached="true"]{transition:none;}
html[data-motion="reduced"] .shop-product-image{transition:none;}
</style>
