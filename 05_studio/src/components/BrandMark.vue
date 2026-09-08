<script setup lang="ts">
import copyText from "../content/components-BrandMark.json";
import { say } from "../state";

import { locale, tr } from "../state";
withDefaults(defineProps<{ compact?: boolean }>(), { compact: false });
const base = import.meta.env.BASE_URL;
</script>
<template>
  <span
    class="puppy-brandmark"
    :class="{ compact }"
    role="img"
    :aria-label="say(copyText.pindo_puppy_08aa61)"
  >
    <img
      :src="`${base}studio-brand/logo-${locale}.jpg`"
      alt=""
      width="1267"
      height="1267"
    />
  </span>
</template>
<style scoped>
/* A viewport over the owner's unmodified PDF image. No relettering or redraw. */
:where(.puppy-brandmark) {
  position: relative;
  display: block;
  width: 290px;
  aspect-ratio: 1267 / 510;
  overflow: hidden;
  flex-shrink: 0;
}
.puppy-brandmark img {
  position: absolute;
  width: 100%;
  max-width: none;
  height: auto;
  top: -88%;
  left: 0;
}
:where(.compact) {
  width: 174px;
  aspect-ratio: 710 / 160;
}
.compact img {
  width: 178.45%;
  top: -490%;
  left: -67.6%;
}
</style>
