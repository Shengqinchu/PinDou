<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref } from "vue";
import { gsap } from "gsap";
import { reducedMotion } from "../ui";
import { PhArrowLeft, PhArrowRight, PhX } from "@phosphor-icons/vue";
import { media, tr } from "../state";
const props = defineProps<{
  photos: { image: string; zh: string; en: string }[];
}>();
const dialog = ref<HTMLDialogElement>();
const selected = ref(0);
let animation: gsap.core.Tween | undefined;
let priorOverflow = "";
async function open(index: number) {
  selected.value = index;
  await nextTick();
  if (!dialog.value?.open) {
    priorOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.value?.showModal();
  }
  animation?.kill();
  if (dialog.value)
    animation = gsap.fromTo(
      dialog.value,
      {
        opacity: 0,
        y: reducedMotion() ? 0 : 16,
        scale: reducedMotion() ? 1 : 0.98,
      },
      {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: reducedMotion() ? 0 : 0.3,
        ease: "power1.inOut",
        clearProps: "transform,opacity",
      },
    );
}
function close() {
  animation?.kill();
  if (!dialog.value) return;
  animation = gsap.to(dialog.value, {
    opacity: 0,
    y: reducedMotion() ? 0 : 12,
    duration: reducedMotion() ? 0 : 0.3,
    ease: "power1.inOut",
    onComplete() {
      dialog.value?.close();
      document.body.style.overflow = priorOverflow;
    },
  });
}
onBeforeUnmount(() => {
  animation?.kill();
  if (dialog.value?.open) {
    dialog.value.close();
    document.body.style.overflow = priorOverflow;
  }
});
function move(delta: number) {
  selected.value =
    (selected.value + delta + props.photos.length) % props.photos.length;
}
defineExpose({ open });
</script>
<template>
  <dialog
    ref="dialog"
    class="photo-dialog"
    :aria-label="tr('工作室照片', 'Studio photograph')"
    @click="$event.target === dialog && close()"
    @cancel.prevent="close"
    @keydown.left="move(-1)"
    @keydown.right="move(1)"
  >
    <button
      class="photo-close icon-button"
      @click="close"
      :aria-label="tr('关闭照片', 'Close photograph')"
    >
      <PhX :size="26" />
    </button>
    <Transition name="photo-swap" mode="out-in"
      ><figure :key="selected">
        <img
          :src="media(photos[selected].image)"
          :alt="tr(photos[selected].zh, photos[selected].en)"
        />
        <figcaption>
          {{ tr(photos[selected].zh, photos[selected].en) }}
        </figcaption>
      </figure></Transition
    >
    <div class="photo-controls">
      <button
        class="icon-button"
        @click="move(-1)"
        :aria-label="tr('上一张', 'Previous photo')"
      >
        <PhArrowLeft /></button
      ><span>{{ selected + 1 }} / {{ photos.length }}</span
      ><button
        class="icon-button"
        @click="move(1)"
        :aria-label="tr('下一张', 'Next photo')"
      >
        <PhArrowRight />
      </button>
    </div>
  </dialog>
</template>
