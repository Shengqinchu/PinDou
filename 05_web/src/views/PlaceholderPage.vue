<template>
  <section class="placeholder-page">
    <p class="eyebrow">Protected Placeholder</p>
    <h1>{{ title }}</h1>
    <p>业务功能将在后续 Batch 实现。</p>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const title = computed(() => String(route.meta.title || '页面占位'));
</script>

