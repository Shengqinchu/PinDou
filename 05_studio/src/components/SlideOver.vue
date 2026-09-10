<script setup lang="ts">
import LiftTitle from './LiftTitle.vue';
import { contentModule } from "../content-store";
const copyText = contentModule("components-SlideOver", copyTextDefault);

import copyTextDefault from "../content/components-SlideOver.json";
import { say } from "../state";

import { ref, useId, watch } from "vue";
import { PhX } from "@phosphor-icons/vue";
import { tr } from "../state";
import { useStudioModal } from "../modal";
const props = defineProps<{
  modelValue: boolean;
  title: string;
  subtitle?: string;
  busy?: boolean;
  closeLabel?: string;
}>();
const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();
const dialog = ref<HTMLDialogElement>();
const heading = useId();
const modal = useStudioModal(dialog, "drawer");
watch(
  () => props.modelValue,
  (value) => (value ? modal.open() : modal.close()),
  { immediate: true },
);
function dismiss() {
  if (!props.busy) emit("update:modelValue", false);
}
</script>
<template>
  <Teleport to="body">
    <dialog
      ref="dialog"
      class="studio-drawer modal-shell"
      :aria-labelledby="heading"
      @cancel.prevent="dismiss"
    >
      <div class="modal-shade" aria-hidden="true" @click="dismiss" />
      <section class="drawer-panel modal-panel">
        <div class="drawer-top">
          <div>
            <p v-if="subtitle" class="drawer-kicker">{{ subtitle }}</p>
            <LiftTitle :id="heading" as="h2" :text="title"/>
          </div>
          <button
            class="icon-button"
            :disabled="busy"
            :aria-label="closeLabel || say(copyText.close_details_643b07)"
            @click="dismiss"
          >
            <PhX :size="21" />
          </button>
        </div>
        <div class="drawer-body"><slot /></div>
        <div v-if="$slots.footer" class="drawer-bottom">
          <slot name="footer" />
        </div>
      </section>
    </dialog>
  </Teleport>
</template>
