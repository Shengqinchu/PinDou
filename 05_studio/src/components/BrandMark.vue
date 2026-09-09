<script setup lang="ts">
import { computed } from "vue";
import { asset, contentModule } from "../content-store";
import copyTextDefault from "../content/components-BrandMark.json";
import { locale, say } from "../state";
const copyText = contentModule("components-BrandMark", copyTextDefault);
const props = withDefaults(defineProps<{ compact?: boolean; contact?: boolean }>(), { compact: false, contact: false });
const source = computed(() => asset(props.contact && locale.value === 'en' ? 'brand-en-contact' : `brand-${locale.value}`));
const ownerEnglish = computed(() => source.value.src === '/studio-brand/english-mark-20260908.jpg');
const ownerContact = computed(() => source.value.src === '/studio-brand/english-contact-20260908.jpg');
</script>
<template>
  <span
    class="puppy-brandmark"
    :class="{ compact, 'owner-english': ownerEnglish, 'owner-contact': ownerContact, 'custom-brand': source.src.startsWith('/studio-api/media/') }"
    role="img"
    :aria-label="say(copyText.pindo_puppy_08aa61)"
  >
    <img
      :src="source.src"
      alt=""
      :width="source.width"
      :height="source.height"
      decoding="async"
    />
  </span>
</template>
<style scoped>
/* Viewports over the owner's unmodified images. The JPGs retain their source bytes. */
:where(.puppy-brandmark) {
  position: relative;
  display: block;
  width: 290px;
  max-width: 100%;
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
.owner-english { aspect-ratio: 1280 / 505; }
.owner-english img { top: calc(-455 / 505 * 100%); }
.owner-contact { width: 100%; aspect-ratio: 1280 / 795; }
.owner-contact img { top: calc(-455 / 795 * 100%); }
.custom-brand img { position: static; width: 100%; height: 100%; object-fit: contain; }
</style>
