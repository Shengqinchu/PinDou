<script setup lang="ts">
import { computed } from "vue";
import BrandIcon from "./BrandIcon.vue";

const props = defineProps<{ text: string }>();
const canada = "\u{1F1E8}\u{1F1E6}";
const parts = computed(() => props.text.split(canada));
</script>

<template>
  <span class="flag-text"
    ><template v-for="(part, index) in parts" :key="index"
      ><span v-if="index" class="flag-text-canada"
        ><span class="flag-text-source">{{ canada }}</span
        ><BrandIcon name="canada" /></span
      >{{ part }}</template
    ></span
  >
</template>

<style scoped>
.flag-text-canada {
  display: inline-block;
  margin-inline-end: 0.16em;
}
.flag-text-source {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}
</style>
