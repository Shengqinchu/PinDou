<script setup lang="ts">
import { nextTick, ref } from "vue";
import { PhArrowLeft, PhArrowRight, PhX } from "@phosphor-icons/vue";
import { media, tr } from "../state";
const props = defineProps<{
  photos: { image: string; zh: string; en: string }[];
}>();
const dialog = ref<HTMLDialogElement>();
const selected = ref(0);
async function open(index: number) {
  selected.value = index;
  await nextTick();
  dialog.value?.showModal();
}
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
    @click="$event.target === dialog && dialog?.close()"
    @keydown.left="move(-1)"
    @keydown.right="move(1)"
  >
    <button
      class="photo-close icon-button"
      @click="dialog?.close()"
      :aria-label="tr('关闭照片', 'Close photograph')"
    >
      <PhX :size="26" />
    </button>
    <figure>
      <img
        :src="media(photos[selected].image)"
        :alt="tr(photos[selected].zh, photos[selected].en)"
      />
      <figcaption>
        {{ tr(photos[selected].zh, photos[selected].en) }}
      </figcaption>
    </figure>
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
