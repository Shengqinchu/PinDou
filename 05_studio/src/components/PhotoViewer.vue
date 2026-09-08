<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, useId } from "vue";
import { gsap } from "gsap";
import { PhArrowLeft, PhArrowRight, PhX } from "@phosphor-icons/vue";
import { media, tr } from "../state";
import { reducedMotion } from "../ui";
import { useStudioModal } from "../modal";
const props = defineProps<{
  photos: { image: string; zh: string; en: string }[];
}>();
const dialog = ref<HTMLDialogElement>();
const incomingElement = ref<HTMLElement>();
const selected = ref(0);
const current = ref(0);
const incoming = ref<number | null>(null);
const loading = ref(false);
const error = ref("");
const photo = computed(() => props.photos[current.value]);
const caption = useId();
const modal = useStudioModal(dialog, "photo");
let revision = 0;
let transition: gsap.core.Tween | undefined;
let preloader: HTMLImageElement | undefined;
function cancelSwap() {
  revision++;
  transition?.kill();
  preloader?.removeAttribute("src");
  preloader = undefined;
  // On interruption retain one dominant frame, rather than queueing old exits.
  if (
    incoming.value !== null &&
    incomingElement.value &&
    Number(getComputedStyle(incomingElement.value).opacity) >= 0.5
  )
    current.value = incoming.value;
  incoming.value = null;
  loading.value = false;
}
function open(index: number) {
  cancelSwap();
  selected.value = current.value = index;
  error.value = "";
  modal.open();
}
function close() {
  cancelSwap();
  modal.close();
}
async function showLatest() {
  cancelSwap();
  const version = revision;
  const target = selected.value;
  if (target === current.value && !error.value) return;
  loading.value = true;
  error.value = "";
  try {
    const img = new Image();
    preloader = img;
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error("photo unavailable"));
      img.src = media(props.photos[target].image);
    });
    if (typeof img.decode === "function") await img.decode();
    if (version !== revision) return;
    if (reducedMotion()) {
      current.value = target;
      loading.value = false;
      return;
    }
    incoming.value = target;
    await nextTick();
    if (version !== revision || !incomingElement.value) return;
    transition = gsap.fromTo(
      incomingElement.value,
      { opacity: 0 },
      {
        opacity: 1,
        duration: 0.38,
        ease: "studio-control",
        onComplete() {
          if (version !== revision) return;
          current.value = target;
          incoming.value = null;
          loading.value = false;
        },
      },
    );
  } catch {
    if (version === revision) {
      error.value = tr(
        "这张照片暂时没能加载，请重试。",
        "This photo could not load. Please try again.",
      );
      loading.value = false;
    }
  }
}
function move(delta: number) {
  selected.value =
    (selected.value + delta + props.photos.length) % props.photos.length;
  showLatest();
}
onBeforeUnmount(cancelSwap);
defineExpose({ open });
</script>
<template>
  <Teleport to="body">
    <dialog
      ref="dialog"
      class="photo-dialog modal-shell"
      :aria-label="tr('工作室照片', 'Studio photograph')"
      :aria-describedby="caption"
      @cancel.prevent="close"
      @keydown.left="move(-1)"
      @keydown.right="move(1)"
    >
      <div class="modal-shade" aria-hidden="true" @click="close" />
      <section class="photo-panel modal-panel">
        <div class="photo-toolbar">
          <span>{{ tr("小屋里的日常", "A little look around") }}</span
          ><button
            class="photo-close icon-button"
            @click="close"
            :aria-label="tr('关闭照片', 'Close photograph')"
          >
            <PhX :size="24" />
          </button>
        </div>
        <div class="photo-stage" :aria-busy="loading">
          <figure class="photo-current">
            <img :src="media(photo.image)" :alt="tr(photo.zh, photo.en)" />
          </figure>
          <figure
            v-if="incoming !== null"
            ref="incomingElement"
            class="photo-incoming"
            aria-hidden="true"
          >
            <img :src="media(photos[incoming].image)" alt="" />
          </figure>
        </div>
        <p :id="caption" class="viewer-caption">{{ tr(photo.zh, photo.en) }}</p>
        <p class="photo-load-status" role="status">
          <template v-if="error"
            >{{ error }}
            <button class="text-link" @click="showLatest">
              {{ tr("重试", "Try again") }}
            </button></template
          ><template v-else-if="loading">{{
            tr("正在载入照片…", "Loading photo…")
          }}</template>
        </p>
        <div class="photo-controls">
          <button
            class="icon-button"
            @click="move(-1)"
            :aria-label="tr('上一张', 'Previous photo')"
          >
            <PhArrowLeft /></button
          ><span aria-live="polite"
            >{{ current + 1 }} / {{ photos.length }}</span
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
<style scoped>
.photo-incoming {
  pointer-events: none;
}
.viewer-caption {
  flex-shrink: 0;
  text-align: center;
  font-size: 13px;
  line-height: 1.6;
  height: 3.2em;
  overflow: auto;
  margin: 12px 24px 0;
}
.photo-load-status {
  flex-shrink: 0;
  min-height: 22px;
  line-height: 1.5;
  font-size: 12px;
  text-align: center;
  margin: 2px 24px 0;
  color: #59694d;
}
.photo-load-status > .text-link {
  padding: 0;
}
</style>
