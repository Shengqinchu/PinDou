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

<style scoped>
.segmented {
  --segments: 4;
  position: relative;
  display: grid;
  grid-template-columns: repeat(var(--segments), minmax(0, 1fr));
  gap: 0;
  padding: 4px;
  isolation: isolate;
  background: #edece5;
  border-radius: 12px;
}
.segment-indicator {
  position: absolute;
  z-index: -1;
  inset: 4px auto 4px 4px;
  width: calc((100% - 8px) / var(--segments));
  transform: translateX(calc(var(--selected) * 100%));
  background: #fffdf8;
  border-radius: 9px;
  box-shadow: 0 2px 5px #343f3112;
  transition: transform var(--surface-duration) var(--surface-ease);
}
.segmented > button {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 7px;
  min-height: 38px;
  padding: 7px 12px;
  font-size: 13px;
  line-height: 1.5;
  color: #62695d;
  transition:
    color var(--surface-duration) var(--surface-ease),
    transform var(--surface-duration) var(--surface-ease);
}
.segmented > button.selected {
  color: var(--ink);
  font-weight: 550;
}
.segmented > button:active {
  transform: scale(0.97);
}
.segmented small {
  font-size: 10px;
}

@media (pointer: coarse), (max-width: 600px) {
  .segmented > button {
    min-height: 44px;
    padding-inline: 5px;
  }
}
</style>
