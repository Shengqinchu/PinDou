<script setup lang="ts">
import { contentModule } from "../content-store";
const copyText = contentModule("components-BrandMark", copyTextDefault);

import copyTextDefault from "../content/components-BrandMark.json";
import { say } from "../state";

import { locale, tr } from "../state";
import { asset, publishedModules } from "../content-store";
withDefaults(defineProps<{ compact?: boolean }>(), { compact: false });
const base = import.meta.env.BASE_URL;
</script>
<template>
  <span
    class="puppy-brandmark"
    :class="{ compact, 'custom-brand': asset(`brand-${locale}`).src.startsWith('/studio-api/media/') }"
    role="img"
    :aria-label="say(copyText.pindo_puppy_08aa61)"
  >
    <img
      :src="asset(`brand-${locale}`).src"
      alt=""
      width="509"
      height="509"
    />
  </span>
</template>
<style scoped>
/* A viewport over the owner's unmodified PDF image. No relettering or redraw. */
:where(.puppy-brandmark) {
  position: relative;
  display: block;
  width: 290px;
  aspect-ratio: 2.65;
  overflow: hidden;
  flex-shrink: 0;
}
.puppy-brandmark img {
  position: absolute;
  width: 100%;
  max-width: none;
  height: auto;
  top: -93%;
  left: 0;
}
:where(.compact) {
  width: 184px;
  aspect-ratio: 2.65;
}
.compact img {
  width: 100%;
  top: -93%;
  left: 0;
}
.custom-brand img { position: static; width: 100%; height: 100%; object-fit: contain; }
</style>
