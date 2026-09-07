<script setup lang="ts">
import { computed, ref } from "vue";
import { PhArrowLeft, PhArrowRight, PhX } from "@phosphor-icons/vue";
import { media, tr } from "../state";
import { useStudioModal } from "../modal";
const props = defineProps<{
  photos: { image: string; zh: string; en: string }[];
}>();
const dialog = ref<HTMLDialogElement>();
const selected = ref(0);
const direction = ref(1);
const photo = computed(() => props.photos[selected.value]);
const modal = useStudioModal(dialog, "photo");
function open(index: number) {
  selected.value = index;
  modal.open();
}
function move(delta: number) {
  direction.value = delta;
  selected.value =
    (selected.value + delta + props.photos.length) % props.photos.length;
}
defineExpose({ open });
</script>
<template>
  <Teleport to="body">
    <dialog
      ref="dialog"
      class="photo-dialog modal-shell"
      :aria-label="tr('工作室照片', 'Studio photograph')"
      @cancel.prevent="modal.close"
      @keydown.left="move(-1)"
      @keydown.right="move(1)"
    >
      <div class="modal-shade" aria-hidden="true" @click="modal.close" />
      <section class="photo-panel modal-panel">
        <div class="photo-toolbar">
          <span>{{ tr("小屋里的日常", "A little look around") }}</span
          ><button
            class="photo-close icon-button"
            @click="modal.close"
            :aria-label="tr('关闭照片', 'Close photograph')"
          >
            <PhX :size="24" />
          </button>
        </div>
        <div class="photo-stage" :style="{ '--photo-direction': direction }">
          <Transition name="photo-swap"
            ><figure :key="selected">
              <img :src="media(photo.image)" :alt="tr(photo.zh, photo.en)" />
              <figcaption>{{ tr(photo.zh, photo.en) }}</figcaption>
            </figure></Transition
          >
        </div>
        <div class="photo-controls">
          <button
            class="icon-button"
            @click="move(-1)"
            :aria-label="tr('上一张', 'Previous photo')"
          >
            <PhArrowLeft /></button
          ><span aria-live="polite"
            >{{ selected + 1 }} / {{ photos.length }}</span
          ><button
            class="icon-button"
            @click="move(1)"
            :aria-label="tr('下一张', 'Next photo')"
          >
            <PhArrowRight />
          </button>
        </div>
      </section>
    </dialog>
  </Teleport>
</template>
