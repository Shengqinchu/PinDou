<script setup lang="ts">
import { computed } from "vue";
import { asset } from "../content-store";
const props = withDefaults(defineProps<{ name: string; alt: string; sizes?: string; loading?: "lazy" | "eager"; priority?: "high" | "low" | "auto" }>(), { sizes: "(max-width: 760px) 100vw, 60vw", loading: "lazy", priority: "auto" });
const photo = computed(() => asset(props.name));
</script>
<template>
  <img :src="photo.src" :srcset="photo.srcset" :width="photo.width" :height="photo.height" :sizes="sizes" :alt="alt" :loading="loading" :fetchpriority="priority" decoding="async" />
</template>
