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
import { invalidFieldMessage } from "../form-feedback";
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
// First field that blocked a submit; stays beside the actions until edited.
const issue = ref("");
watch(
  () => props.modelValue,
  (value) => {
    issue.value = "";
    if (value) modal.open();
    else modal.close();
  },
  { immediate: true },
);
function noteInvalid(event: Event) {
  if (!issue.value) issue.value = invalidFieldMessage(event);
}
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
      @invalid.capture="noteInvalid"
      @input="issue = ''"
      @change="issue = ''"
      @submit.capture="issue = ''"
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
        <div v-if="$slots.footer || issue" class="drawer-bottom">
          <p v-if="issue" class="drawer-issue" role="alert">{{ issue }}</p>
          <slot name="footer" />
        </div>
      </section>
    </dialog>
  </Teleport>
</template>
