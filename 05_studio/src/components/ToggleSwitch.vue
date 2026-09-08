<script setup lang="ts">
defineProps<{ modelValue: boolean; label: string; disabled?: boolean }>();
defineEmits<{ "update:modelValue": [value: boolean] }>();
</script>
<template>
  <button
    type="button"
    :class="['toggle-switch', { on: modelValue }]"
    role="switch"
    :aria-checked="modelValue"
    :aria-label="label"
    :disabled="disabled"
    @click="$emit('update:modelValue', !modelValue)"
  >
    <span class="switch-track" aria-hidden="true"
      ><span class="switch-thumb"
    /></span>
  </button>
</template>
<style scoped>
.toggle-switch {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  padding: 0;
  border: 0;
  background: transparent;
  border-radius: 12px;
}
.switch-track {
  position: relative;
  display: block;
  width: 44px;
  height: 26px;
  border: 1px solid #c8cec1;
  border-radius: 20px;
  background: #d7dbd0;
  transition:
    background-color var(--control-duration) var(--control-ease),
    border-color var(--control-duration) var(--control-ease),
    box-shadow var(--control-duration) var(--control-ease);
}
.switch-thumb {
  position: absolute;
  width: 18px;
  height: 18px;
  left: 3px;
  top: 3px;
  border-radius: 50%;
  background: #fffef9;
  box-shadow: 0 1px 3px #343f3136;
  transition: transform var(--control-duration) var(--control-ease);
}
.on .switch-track {
  background: #596e4b;
  border-color: #596e4b;
}
.on .switch-thumb {
  transform: translateX(18px);
}
.toggle-switch:active .switch-track {
  box-shadow: 0 0 0 3px #596e4b19;
}
.toggle-switch:focus-visible {
  outline: 2px solid #61754e;
  outline-offset: 2px;
}
.toggle-switch:disabled {
  opacity: 0.5;
}
</style>
