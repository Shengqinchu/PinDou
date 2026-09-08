<script setup lang="ts">
defineProps<{ name: "wechat" | "xiaohongshu" | "canada" }>();
const base = import.meta.env.BASE_URL;
</script>

<template>
  <span class="brand-icon" :class="`brand-icon--${name}`" aria-hidden="true">
    <img :src="`${base}studio-brand/${name}.svg`" alt="" decoding="async" />
  </span>
</template>

<style scoped>
.brand-icon {
  display: inline-block;
  position: relative;
  flex: 0 0 auto;
  width: 1.6em;
  height: 1.6em;
  vertical-align: -0.2em;
}
.brand-icon img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.brand-icon--xiaohongshu {
  width: 2.8em;
  height: 1.1em;
  overflow: hidden;
}
.brand-icon--xiaohongshu img {
  position: absolute;
  width: 100%;
  height: auto;
  top: 50%;
  transform: translateY(-50%);
}
.brand-icon--canada {
  width: 1.6em;
  height: 0.8em;
  vertical-align: 0;
}
</style>
