<template>
  <section class="placeholder-page">
    <p class="eyebrow">正在准备</p>
    <h1>{{ title }}</h1>
    <p>{{ description }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const title = computed(() => String(route.meta.title || '即将开放'));
const description = computed(() => {
  if (route.name === 'result') {
    return '照片已收到，图纸生成体验正在为你准备。';
  }
  if (route.name === 'works') {
    return '这里会集中保存你的拼豆作品，方便随时回来查看。';
  }
  return '这个页面正在整理中，很快就能使用。';
});
</script>
