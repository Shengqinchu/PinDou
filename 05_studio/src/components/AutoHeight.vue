<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { gsap } from "gsap";
import { motion } from "../motion";
import { reducedMotion } from "../ui";
const frame = ref<HTMLElement>();
const content = ref<HTMLElement>();
let observer: ResizeObserver | undefined;
let animation: gsap.core.Tween | undefined;
let priorHeight = 0;
let priorWidth = 0;
onMounted(() => {
  if (!frame.value || !content.value) return;
  priorHeight = content.value.offsetHeight;
  priorWidth = content.value.offsetWidth;
  observer = new ResizeObserver(() => {
    if (!frame.value || !content.value) return;
    const height = content.value.offsetHeight;
    const width = content.value.offsetWidth;
    const changedWidth = Math.abs(width - priorWidth) > 1;
    priorWidth = width;
    if (height === priorHeight && !changedWidth) return;
    const from = animation?.isActive()
      ? frame.value.getBoundingClientRect().height
      : priorHeight;
    priorHeight = height;
    animation?.kill();
    if (changedWidth || reducedMotion()) {
      gsap.set(frame.value, { clearProps: "height,overflow" });
      return;
    }
    animation = gsap.fromTo(
      frame.value,
      { height: from, overflow: "clip" },
      {
        height,
        duration: motion.state,
        ease: "studio-control",
        clearProps: "height,overflow",
      },
    );
  });
  observer.observe(content.value);
});
onBeforeUnmount(() => {
  observer?.disconnect();
  animation?.kill();
});
</script>
<template>
  <div ref="frame" class="auto-height">
    <div ref="content" class="auto-height-content"><slot /></div>
  </div>
</template>
