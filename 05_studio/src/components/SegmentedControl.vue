<script setup lang="ts">
import { computed } from "vue";
const props = defineProps<{
  modelValue: string;
  options: { value: string; label: string; count?: number }[];
  label: string;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
const position = computed(() =>
  Math.max(
    0,
    props.options.findIndex((o) => o.value === props.modelValue),
  ),
);
</script>
<template>
  <div
    class="segmented"
    role="group"
    :aria-label="label"
    :style="{ '--segments': options.length, '--selected': position }"
  >
    <span class="segment-indicator" aria-hidden="true" /><button
      v-for="option in options"
      :key="option.value"
      type="button"
      :aria-pressed="modelValue === option.value"
      :class="{ selected: modelValue === option.value }"
      @click="emit('update:modelValue', option.value)"
    >
      {{ option.label
      }}<small v-if="option.count !== undefined">{{ option.count }}</small>
    </button>
  </div>
</template>
