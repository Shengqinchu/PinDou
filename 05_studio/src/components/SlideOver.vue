<script setup lang="ts">
import { onBeforeUnmount, ref, useId } from "vue";
import { gsap } from "gsap";
import { PhX } from "@phosphor-icons/vue";
import { reducedMotion } from "../ui";
import { tr } from "../state";
defineProps<{
  modelValue: boolean;
  title: string;
  subtitle?: string;
  busy?: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();
const dialog = ref<HTMLDialogElement>();
const heading = useId();
let animation: gsap.core.Tween | undefined;
let priorOverflow = "";
function enter(el: Element, done: () => void) {
  const modal = el as HTMLDialogElement;
  priorOverflow = document.body.style.overflow;
  document.body.style.overflow = "hidden";
  if (!modal.open) modal.showModal();
  animation?.kill();
  animation = gsap.fromTo(
    modal,
    { x: reducedMotion() ? 0 : 48, opacity: 0 },
    {
      x: 0,
      opacity: 1,
      duration: reducedMotion() ? 0 : 0.3,
      ease: "power1.inOut",
      clearProps: "transform,opacity",
      onComplete: done,
    },
  );
}
function leave(el: Element, done: () => void) {
  animation?.kill();
  animation = gsap.to(el, {
    x: reducedMotion() ? 0 : 32,
    opacity: 0,
    duration: reducedMotion() ? 0 : 0.3,
    ease: "power1.inOut",
    onComplete() {
      (el as HTMLDialogElement).close();
      document.body.style.overflow = priorOverflow;
      done();
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
</script>
<template>
  <Teleport to="body"
    ><Transition :css="false" @enter="enter" @leave="leave"
      ><dialog
        v-if="modelValue"
        ref="dialog"
        class="studio-drawer"
        :aria-labelledby="heading"
        @cancel.prevent="!busy && emit('update:modelValue', false)"
        @click="
          $event.target === dialog && !busy && emit('update:modelValue', false)
        "
      >
        <div class="drawer-top">
          <div>
            <p v-if="subtitle" class="drawer-kicker">{{ subtitle }}</p>
            <h2 :id="heading">{{ title }}</h2>
          </div>
          <button
            class="icon-button"
            :disabled="busy"
            :aria-label="tr('关闭详情', 'Close details')"
            @click="emit('update:modelValue', false)"
          >
            <PhX :size="21" />
          </button>
        </div>
        <div class="drawer-body"><slot /></div>
        <div v-if="$slots.footer" class="drawer-bottom">
          <slot name="footer" />
        </div></dialog></Transition
  ></Teleport>
</template>
