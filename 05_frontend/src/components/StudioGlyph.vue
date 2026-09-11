<script setup lang="ts">
import { computed } from 'vue';
const props = withDefaults(defineProps<{ name: string; size?: number }>(), { size: 22 });
const paths: Record<string, string> = {
  home: '<path d="m3 10 9-7 9 7v10H3Z M9 20v-7h6v7"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 11h18m-13 4h2m4 0h2"/>',
  back: '<path d="M19 12H5m6-6-6 6 6 6"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 1v2m0 18v2M1 12h2m18 0h2M4 4l1.5 1.5m13 13L20 20M4 20l1.5-1.5m13-13L20 4"/>',
  pin: '<path d="M19 10c0 5-7 12-7 12S5 15 5 10a7 7 0 0 1 14 0Z"/><circle cx="12" cy="10" r="2.5"/>',
  phone: '<path d="m6 3 4 4-2 3c2 3 3 4 6 6l3-2 4 4-3 3C10 21 3 14 3 6Z"/>',
  arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
  hidden: '<path d="m3 3 18 18M9.5 5.3A11 11 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3 3.9M6.2 6.2A20 20 0 0 0 2 12s3.5 7 10 7a11 11 0 0 0 5.8-1.7M10 10a3 3 0 0 0 4 4"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
  refresh: '<path d="M20 10a8 8 0 1 0-1 7M20 4v6h-6"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V4H4v12h4"/>',
  wechat: '<path d="M14 6a7 7 0 0 0-5-2C5 4 2 6.5 2 10c0 2 1 3.5 3 4.5L4 17l3-1.5M22 14c0-3-3-5.5-6.5-5.5S9 11 9 14s3 5.5 6.5 5.5c1 0 2-.2 3-.5l2.5 1-1-2c1.3-1 2-2.5 2-4Z"/><path d="M6 8h.1M10 8h.1M13 13h.1M18 13h.1"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
};
const source = computed(() => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#344957" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round">${paths[props.name] || paths.info}</svg>`;
  const bytes = Uint8Array.from(svg, character => character.charCodeAt(0));
  return 'data:image/svg+xml;base64,' + uni.arrayBufferToBase64(bytes.buffer);
});
</script>
<template><image :src="source" :style="{width:size+'px',height:size+'px',flexShrink:0}" mode="aspectFit" aria-hidden="true" /></template>
